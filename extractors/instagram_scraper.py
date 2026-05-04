"""
instagram_scraper.py

Playwright로 Instagram 브랜드 태그 페이지를 스크롤하며
게시물 데이터를 수집합니다.

동작 흐름:
  1. 저장된 세션(storage_state.json)으로 로그인 상태 복원
  2. /{brand_id}/tagged/ 페이지로 이동
  3. 스크롤하며 게시물 URL 수집 → 상세 페이지에서 날짜·태그·이미지 파싱
  4. 필터 적용 (자기 태그 / 비즈니스 계정 제외)
  5. target_day와 일치하는 게시물만 반환

수집 필터:
  - 자기 태그 제외: 브랜드 본인이 올린 게시물은 제외
  - 비즈니스 계정 제외: 무신사·29cm 등 플랫폼, 편집샵 계정은 제외
"""

import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


load_dotenv()

# ── 정규식 패턴 ──────────────────────────────────────────────────

MENTION_RE      = re.compile(r"@[\w\.]+")
POST_URL_RE     = re.compile(r"/p/([^/?#]+)/?")
OWNER_DESC_RE   = re.compile(
    r"^\s*([A-Za-z0-9._]+)\s+on\s+[A-Z][a-z]+\s+\d{1,2},\s+\d{4}",
    re.IGNORECASE,
)
DISPLAY_NAME_RE = re.compile(r"^(.*?)\s+on Instagram:", re.IGNORECASE)

# 상세 페이지가 로드됐다고 볼 수 있는 조건 (시간 요소, og 메타 중 하나라도 있으면 OK)
DETAIL_READY_SCRIPT = """
() => Boolean(
    document.querySelector("time") ||
    document.querySelector('meta[property="og:description"]') ||
    document.querySelector('meta[property="og:image"]')
)
"""


# ── 비즈니스 계정 필터 설정 ──────────────────────────────────────

# 알려진 국내 패션 플랫폼·편집샵 계정 (프로필 방문 없이 즉시 제외)
KNOWN_PLATFORM_ACCOUNTS = frozenset({
    # 종합 패션 플랫폼
    "musinsa", "musinsa.official",
    "29cm_official_kr",
    "wconcept_korea",
    "ably_official",
    "zigzag_official",
    "brandi_hq",
    "kream.official",
    # 백화점·대형 리테일
    "lotteon_fashion", "lottefashion_official",
    "galleria_dept",
    "hyundaidept_official",
    "shinsegaedfs", "ssg_com",
    # 편집샵·멀티 브랜드
    "handsome_official",
    "kasina",
    "boontheshop",
    "10cursedmen",
    "thecornerkorea",
})

# Instagram 프로필 페이지 본문에서 비즈니스 계정임을 나타내는 키워드
# (Instagram 카테고리 라벨 및 쇼핑 기능 버튼 텍스트)
BUSINESS_INDICATOR_KEYWORDS = (
    # Instagram 카테고리 라벨 (한/영)
    "의류(브랜드)", "clothing (brand)", "clothing brand",
    "쇼핑 및 소매", "shopping & retail",
    "부티크", "boutique store",
    "소매 회사", "retail company",
    "패션 디자이너", "fashion designer",
    "인터넷 회사", "internet company",
    # Instagram 쇼핑 기능 버튼 (비즈니스 계정에만 표시)
    "쇼핑하기", "view shop",
)


# ── 필터 함수 ────────────────────────────────────────────────────

def _is_self_tagged(insta_id: str, brand_id: str) -> bool:
    """브랜드가 자기 자신을 태그한 게시물인지 확인합니다."""
    return insta_id.lower() == brand_id.lower()


def check_is_business_account(
    profile_page,
    insta_id: str,
    cache: dict,
) -> bool:
    """
    계정이 비즈니스/편집샵 계정인지 확인합니다.

    확인 순서:
      1. cache에 이미 결과가 있으면 재사용 (같은 계정 반복 방문 없음)
      2. KNOWN_PLATFORM_ACCOUNTS에 포함되면 즉시 True
      3. 프로필 페이지 방문 → 카테고리 라벨·쇼핑 버튼 키워드 탐지

    Args:
        profile_page : 프로필 확인 전용 브라우저 탭
        insta_id     : 확인할 계정 ID
        cache        : {insta_id: bool} 세션 내 캐시 딕셔너리
    """
    if insta_id == "unknown":
        return False

    if insta_id in cache:
        return cache[insta_id]

    # 알려진 플랫폼은 프로필 방문 없이 즉시 처리
    if insta_id in KNOWN_PLATFORM_ACCOUNTS:
        cache[insta_id] = True
        return True

    # 프로필 페이지 방문해서 키워드 탐지
    try:
        profile_page.goto(
            f"https://www.instagram.com/{insta_id}/",
            wait_until="domcontentloaded",
        )
        profile_page.wait_for_timeout(1500)

        body_text = profile_page.evaluate("() => document.body.innerText").lower()
        is_biz    = any(kw.lower() in body_text for kw in BUSINESS_INDICATOR_KEYWORDS)

        cache[insta_id] = is_biz
        if is_biz:
            print(f"🏢 비즈니스 계정 감지 → 제외: @{insta_id}")
        return is_biz

    except Exception as exc:
        print(f"⚠️ 프로필 확인 실패 ({insta_id}): {exc}")
        cache[insta_id] = False  # 확인 못 하면 일단 포함
        return False


# ── 로그인 관련 ──────────────────────────────────────────────────

def assert_logged_in(page):
    """sessionid 쿠키가 없으면 에러를 발생시킵니다."""
    cookies      = page.context.cookies()
    cookie_names = {cookie["name"] for cookie in cookies}

    if "sessionid" not in cookie_names:
        raise RuntimeError(
            f"로그인 세션(sessionid) 없음. URL={page.url}, cookies={sorted(cookie_names)}"
        )


def wait_for_sessionid(page, timeout=20):
    """sessionid 쿠키가 생길 때까지 최대 timeout초 기다립니다."""
    deadline = time.time() + timeout

    while time.time() < deadline:
        cookies = page.context.cookies()
        if any(cookie["name"] == "sessionid" for cookie in cookies):
            return True
        page.wait_for_timeout(500)

    return False


def dismiss_common_dialogs(page):
    """'나중에 하기' 등 팝업이 뜨면 닫아줍니다."""
    for label in ("나중에 하기", "Not Now"):
        for _ in range(3):
            try:
                page.get_by_role("button", name=label).click(timeout=1500)
                page.wait_for_timeout(500)
            except Exception:
                break


def ensure_logged_in(page, login_url, username, password):
    """홈에 접근했을 때 로그인 페이지로 튕기면 다시 로그인합니다."""
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    page.wait_for_timeout(1000)

    if "/accounts/login" in page.url:
        print("홈 접근이 로그인으로 리다이렉트 → 로그인 수행")
        login(page, login_url, username, password)
        return

    dismiss_common_dialogs(page)
    assert_logged_in(page)


def login(page, login_url, username, password):
    """Instagram 로그인 폼에 계정 정보를 입력하고 로그인합니다."""
    page.goto(login_url, wait_until="domcontentloaded")

    page.wait_for_selector("input[name='username'], input[name='email']")
    page.wait_for_selector("input[name='password'], input[name='pass']")

    if page.locator("input[name='email']").first.is_visible():
        page.fill("input[name='email']", username)
        page.fill("input[name='pass']", password)
        page.get_by_role("button", name="정보 저장").click()
    else:
        page.fill("input[name='username']", username)
        page.fill("input[name='password']", password)
        page.click("button[type='submit']")

    page.wait_for_timeout(3000)
    dismiss_common_dialogs(page)
    page.wait_for_timeout(3000)

    assert_logged_in(page)
    print("✅ 로그인 성공:", page.url)

    if not wait_for_sessionid(page, timeout=20):
        cookie_names = sorted({c["name"] for c in page.context.cookies()})
        raise RuntimeError(f"sessionid 발급 실패. url={page.url}, cookies={cookie_names}")


# ── 페이지 이동 ──────────────────────────────────────────────────

def goto_tagged(page, brand_id):
    """브랜드의 tagged 페이지로 이동하고 게시물 링크가 보일 때까지 기다립니다."""
    tagged_url = f"https://www.instagram.com/{brand_id}/tagged/"
    page.goto(tagged_url, wait_until="domcontentloaded")
    page.wait_for_load_state("domcontentloaded")
    print("tagged 이동 후 URL:", page.url)

    if "/accounts/login" in page.url:
        raise RuntimeError(f"tagged 접근 실패(로그인으로 리다이렉트): {page.url}")

    dismiss_common_dialogs(page)
    page.wait_for_selector("a[href*='/p/']", timeout=10000)


def open_post_detail_page(detail_page, url):
    """상세 페이지로 이동하고 og 메타 또는 time 태그가 로드될 때까지 기다립니다."""
    detail_url = f"https://www.instagram.com{url}"
    detail_page.goto(detail_url, wait_until="domcontentloaded")
    detail_page.wait_for_load_state("domcontentloaded")

    if "/accounts/login" in detail_page.url:
        raise RuntimeError(f"상세 페이지 접근 실패(로그인으로 리다이렉트): {detail_page.url}")

    detail_page.wait_for_function(DETAIL_READY_SCRIPT, timeout=10000)
    detail_page.wait_for_timeout(1500)
    return detail_page.url


# ── 데이터 파싱 ──────────────────────────────────────────────────

def parse_post_date_kst(page, kst):
    """
    상세 페이지에서 게시물 날짜를 KST 기준 'YYYY-MM-DD' 문자열로 추출합니다.
    1순위: <time datetime="..."> 태그
    2순위: og:description 메타의 날짜 텍스트
    """
    # 1순위: time 태그
    try:
        page.wait_for_selector("time", state="visible", timeout=8000)
        dt_str = page.locator("time").first.get_attribute("datetime")

        if dt_str:
            post_dt_utc   = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            post_date_str = post_dt_utc.astimezone(kst).strftime("%Y-%m-%d")
            print(f"게시물 날짜: {post_date_str}")
            return post_date_str
    except Exception:
        pass

    # 2순위: og:description 메타 텍스트에서 날짜 추출
    meta_desc = page.evaluate(
        """
        () => (
            document.querySelector('meta[property="og:description"]')?.getAttribute("content") ||
            document.querySelector('meta[name="description"]')?.getAttribute("content") ||
            ""
        )
        """
    )
    match = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4})", meta_desc)
    if not match:
        return None

    post_date_str = (
        datetime.strptime(match.group(1), "%B %d, %Y")
        .replace(tzinfo=kst)
        .strftime("%Y-%m-%d")
    )
    print(f"게시물 날짜(메타 폴백): {post_date_str}")
    return post_date_str


def extract_insta_id(href, meta_desc):
    """URL 경로 또는 og:description에서 계정 ID를 추출합니다."""
    path_parts = [part for part in href.split("/") if part] if href else []
    if len(path_parts) >= 3 and path_parts[1] == "p":
        return path_parts[0].lower()

    owner_match = OWNER_DESC_RE.search(meta_desc or "")
    if owner_match:
        return owner_match.group(1).lower()

    return "unknown"


def extract_insta_name(meta_title, insta_id):
    """og:title에서 계정 표시 이름을 추출합니다. 추출 실패 시 'unknown'을 반환합니다."""
    title = (meta_title or "").strip()
    if not title:
        return "unknown"

    match = DISPLAY_NAME_RE.search(title)
    if not match:
        return "unknown"

    display_name = match.group(1).strip().strip('"').strip()
    if not display_name:
        return "unknown"

    # 표시 이름이 계정 ID와 동일하면 의미없는 값이므로 unknown 처리
    if insta_id != "unknown" and display_name.lower() == insta_id.lower():
        return "unknown"

    return display_name


def extract_post_data(page, href):
    """
    상세 페이지의 메타 태그와 이미지 alt에서 게시물 데이터를 추출합니다.
    반환: (post_id, insta_id, insta_name, full_link, img_src, tagged_ids, tags_cnt)
    """
    meta_title = page.evaluate(
        "() => document.querySelector('meta[property=\"og:title\"]')?.getAttribute('content') || ''"
    )
    meta_desc = page.evaluate(
        """
        () => (
            document.querySelector('meta[property="og:description"]')?.getAttribute("content") ||
            document.querySelector('meta[name="description"]')?.getAttribute("content") ||
            ""
        )
        """
    )
    src = page.evaluate(
        "() => document.querySelector('meta[property=\"og:image\"]')?.getAttribute('content') || ''"
    )

    # 이미지 alt 텍스트에서 @멘션 태그 추출
    image_candidates = page.evaluate(
        """
        () => Array.from(document.querySelectorAll("main img"))
            .map((img) => ({ alt: img.getAttribute("alt") || "", src: img.getAttribute("src") || "" }))
            .filter((item) => item.alt.startsWith("Photo by ") || item.alt.startsWith("Photo shared by "))
        """
    )

    tags = []
    for item in image_candidates:
        found   = MENTION_RE.findall(item["alt"])
        cleaned = [tag.rstrip(".,!?:;") for tag in found]
        tags.extend(cleaned)

        if not src and item["src"]:
            src = item["src"]

    # 중복 태그 제거 (순서 유지)
    seen = set()
    tags = [tag for tag in tags if not (tag in seen or seen.add(tag))]

    full_link  = f"https://www.instagram.com{href}" if href else ""
    post_match = POST_URL_RE.search(full_link)
    post_id    = post_match.group(1) if post_match else "unknown"
    insta_id   = extract_insta_id(href, meta_desc)
    insta_name = extract_insta_name(meta_title, insta_id)

    return post_id, insta_id, insta_name, full_link, src, ",".join(tags), len(tags)


def snapshot_post_urls(page):
    """현재 화면에 보이는 게시물 URL을 중복 없이 반환합니다."""
    hrefs = page.eval_on_selector_all(
        "a[href*='/p/']",
        "elements => elements.map(el => el.getAttribute('href'))",
    )

    seen       = set()
    full_hrefs = []

    for href in hrefs:
        href = href.split("?")[0]
        if "/c/" in href:  # 댓글 링크 제외
            continue
        if href not in seen:
            seen.add(href)
            full_hrefs.append(href)

    return full_hrefs


# ── 디버그 ───────────────────────────────────────────────────────

def save_debug_artifact(page, url, reason, debug_dir="/tmp/insta_debug"):
    """실패한 게시물의 스크린샷을 저장합니다."""
    Path(debug_dir).mkdir(parents=True, exist_ok=True)
    post_code       = url.strip("/").split("/")[-1] if url else "unknown"
    timestamp       = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(debug_dir, f"{reason}_{post_code}_{timestamp}.png")

    try:
        page.screenshot(path=screenshot_path, full_page=True)
        return screenshot_path
    except Exception as exc:
        print(f"⚠️ 스크린샷 저장 실패: {exc}")
        return None


# ── 핵심 수집 루프 ───────────────────────────────────────────────

def collect_posts_with_scroll(
    grid_page,
    detail_page,
    profile_page,
    brand_id,
    brand_name,
    scroll_y,
    max_scrolls,
    wait_ms,
    kst,
    target_day,
    filter_self_tag=True,
    filter_business=True,
):
    """
    스크롤하며 게시물을 수집합니다.

    Args:
        profile_page     : 비즈니스 계정 확인 전용 탭 (filter_business=True일 때 사용)
        filter_self_tag  : True면 브랜드 본인이 올린 게시물 제외
        filter_business  : True면 비즈니스/편집샵 계정 게시물 제외

    종료 조건:
      - max_scrolls 횟수 초과
      - 새 게시물이 3번 연속 없을 때 (그리드 끝 도달)
      - target_day보다 오래된 게시물이 5번 연속 나올 때 (날짜 범위 벗어남)
    """
    posts            = []
    all_seen         = set()
    business_cache   = {}    # {insta_id: bool} — 세션 내 비즈니스 계정 캐시
    past_date_streak = 0
    no_change_count  = 0
    scroll_count     = 0
    detail_fail_cnt  = 0
    parsed_fail_cnt  = 0
    filtered_cnt     = 0
    stop_early       = False
    stop_reason      = None

    while scroll_count < max_scrolls and not stop_early:

        # ── 현재 화면의 게시물 URL 스냅샷 ──────────────────────────
        urls         = snapshot_post_urls(grid_page)
        new_urls     = [url for url in urls if url not in all_seen]
        before_count = len(all_seen)

        print(f"[스크롤 {scroll_count}] 전체: {len(urls)}개 / 신규: {len(new_urls)}개")

        # ── 신규 게시물 처리 ────────────────────────────────────────
        for url in new_urls:
            all_seen.add(url)

            try:
                print(f"처리 중: {url}")
                open_post_detail_page(detail_page, url)

                # 날짜 확인 (가장 먼저 체크 — 페이지 로드 후 빠르게 필터링)
                post_date = parse_post_date_kst(detail_page, kst)
                if post_date is None:
                    parsed_fail_cnt += 1
                    screenshot_path  = save_debug_artifact(detail_page, url, "date_parse_fail")
                    print(f"⚠️ 날짜 추출 실패 → 스킵: {url}")
                    if screenshot_path:
                        print(f"   디버그 스크린샷: {screenshot_path}")
                    continue

                print(f"목표: {target_day} | 실제: {post_date}")

                # target_day보다 오래된 게시물 연속 감지
                if target_day is not None and post_date < target_day:
                    past_date_streak += 1
                    print(f"📌 {past_date_streak}번째 연속 과거 게시물")

                    if past_date_streak >= 5:
                        print("5번 연속 과거 게시물 → 수집 종료")
                        stop_early  = True
                        stop_reason = "past_date_streak>=5"
                        break

                    continue

                past_date_streak = 0

                if target_day is not None and post_date != target_day:
                    continue

                # 날짜 통과 → 상세 데이터 추출
                post_id, insta_id, insta_name, full_link, src, insta_tag, tags_cnt = (
                    extract_post_data(detail_page, url)
                )

                # ── 필터 1: 자기 태그 제외 ───────────────────────────
                # 브랜드 계정이 자기 자신을 태그한 게시물은 수집 제외
                if filter_self_tag and _is_self_tagged(insta_id, brand_id):
                    filtered_cnt += 1
                    print(f"🔕 자기 태그 제외: @{insta_id}")
                    continue

                # ── 필터 2: 비즈니스/편집샵 계정 제외 ──────────────
                # 무신사·29cm 등 플랫폼, 편집샵 계정은 일반 소비자가 아니므로 제외
                # (처음 만나는 계정만 프로필 방문, 이후 캐시 활용)
                if filter_business and check_is_business_account(
                    profile_page, insta_id, business_cache
                ):
                    filtered_cnt += 1
                    continue

                posts.append((
                    post_id, insta_id, insta_name,
                    brand_name, brand_id,
                    full_link, src, post_date,
                    insta_tag, tags_cnt,
                ))
                print(f"✅ 수집 완료 ({len(posts)}개): {full_link}")

            except Exception as exc:
                detail_fail_cnt += 1
                screenshot_path  = save_debug_artifact(detail_page, url, "detail_open_fail")
                print(f"❌ 상세 페이지 처리 실패: {url} — {exc}")
                if screenshot_path:
                    print(f"   디버그 스크린샷: {screenshot_path}")

        if stop_early:
            break

        # ── 스크롤 종료 조건 체크 ────────────────────────────────────
        new_count = len(all_seen) - before_count
        if new_count == 0:
            no_change_count += 1
            print(f"⚠️ 새 게시물 없음 ({no_change_count}/3)")
        else:
            no_change_count = 0

        if no_change_count >= 3:
            print("3번 연속 새 게시물 없음 → 그리드 끝 도달, 종료")
            break

        # ── 다음 스크롤 ─────────────────────────────────────────────
        print(f"스크롤 진행 중... (누적: {len(all_seen)}개 | 수집: {len(posts)}개)")
        grid_page.mouse.wheel(0, scroll_y)
        grid_page.wait_for_timeout(wait_ms)
        scroll_count += 1

    print(
        f"\n[수집 완료]"
        f"\n  수집    : {len(posts)}개"
        f"\n  필터 제외: {filtered_cnt}건 (자기태그/비즈니스)"
        f"\n  상세 실패: {detail_fail_cnt}건"
        f"\n  날짜 실패: {parsed_fail_cnt}건"
        f"\n  종료 사유: {stop_reason}"
    )
    return posts


# ── 진입점 ───────────────────────────────────────────────────────

def run(
    state_path="/opt/airflow/secrets/storage_state.json",
    login_url="https://www.instagram.com/accounts/login/",
    username=os.getenv("ID"),
    password=os.getenv("PW"),
    brand_name=None,
    brand_id=None,
    scroll_y=700,
    max_scrolls=50,
    wait_ms=5000,
    headless=True,
    target_day=None,
    filter_self_tag=True,
    filter_business=True,
):
    """
    브랜드 태그 페이지에서 게시물을 수집해 리스트로 반환합니다.

    Args:
        state_path       : Playwright 세션 파일 경로
        brand_id         : Instagram 계정 ID (예: "amomento.co")
        brand_name       : 브랜드 키 (예: "amomento") — DB 저장용
        target_day       : 수집 대상 날짜 'YYYY-MM-DD'. None이면 전체 수집
        headless         : True면 브라우저 창 없이 실행
        filter_self_tag  : True면 브랜드 본인 게시물 제외 (기본값: True)
        filter_business  : True면 비즈니스/편집샵 계정 제외 (기본값: True)
    """
    kst = timezone(timedelta(hours=9))

    with sync_playwright() as playwright:
        browser      = playwright.chromium.launch(headless=headless)
        context      = browser.new_context(storage_state=state_path)
        grid_page    = context.new_page()
        detail_page  = context.new_page()
        profile_page = context.new_page()  # 비즈니스 계정 확인 전용

        ensure_logged_in(grid_page, login_url, username, password)
        goto_tagged(grid_page, brand_id)

        posts = collect_posts_with_scroll(
            grid_page=grid_page,
            detail_page=detail_page,
            profile_page=profile_page,
            brand_id=brand_id,
            brand_name=brand_name,
            scroll_y=scroll_y,
            max_scrolls=max_scrolls,
            wait_ms=wait_ms,
            kst=kst,
            target_day=target_day,
            filter_self_tag=filter_self_tag,
            filter_business=filter_business,
        )

        profile_page.close()
        detail_page.close()
        grid_page.close()
        browser.close()

    print("수집된 샘플:", posts[0:1])
    return posts


def main():
    """로컬 테스트용 진입점입니다."""
    run(
        state_path="/opt/airflow/secrets/storage_state.json",
        brand_name="amomento",
        brand_id="amomento.co",
        headless=False,
    )


if __name__ == "__main__":
    main()
