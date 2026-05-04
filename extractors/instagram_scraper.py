"""
grid 페이지는 유지하고, 게시물 상세는 별도 detail page에서 읽는 방식의 extractor
"""

from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path


load_dotenv()

MENTION_RE = re.compile(r"@[\w\.]+")
POST_URL_RE = re.compile(r"/p/([^/?#]+)/?")
OWNER_DESC_RE = re.compile(
    r"^\s*([A-Za-z0-9._]+)\s+on\s+[A-Z][a-z]+\s+\d{1,2},\s+\d{4}",
    re.IGNORECASE,
)
DISPLAY_NAME_RE = re.compile(r"^(.*?)\s+on Instagram:", re.IGNORECASE)
DETAIL_READY_SCRIPT = """
() => Boolean(
    document.querySelector("time") ||
    document.querySelector('meta[property="og:description"]') ||
    document.querySelector('meta[property="og:image"]')
)
"""


def assert_logged_in(page):
    cookies = page.context.cookies()
    cookie_names = {cookie["name"] for cookie in cookies}

    if "sessionid" not in cookie_names:
        raise RuntimeError(
            f"로그인 세션(sessionid) 없음. 현재 URL={page.url}, cookies={sorted(cookie_names)}"
        )


def wait_for_sessionid(page, timeout=20):
    deadline = time.time() + timeout

    while time.time() < deadline:
        cookies = page.context.cookies()
        if any(cookie["name"] == "sessionid" for cookie in cookies):
            return True
        page.wait_for_timeout(500)

    return False


def dismiss_common_dialogs(page):
    for label in ("나중에 하기", "Not Now"):
        for _ in range(3):
            try:
                page.get_by_role("button", name=label).click(timeout=1500)
                page.wait_for_timeout(500)
            except Exception:
                break


def ensure_logged_in(page, login_url, username, password):
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    page.wait_for_timeout(1000)

    if "/accounts/login" in page.url:
        print("🔁 홈 접근이 로그인으로 리다이렉트 → login() 수행")
        login(page, login_url, username, password)
        return

    dismiss_common_dialogs(page)
    assert_logged_in(page)


def login(page, login_url, username, password):
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
        cookies = page.context.cookies()
        cookie_names = sorted({cookie["name"] for cookie in cookies})
        raise RuntimeError(f"sessionid 발급 실패. url={page.url}, cookies={cookie_names}")


def goto_tagged(page, brand_id):
    tagged_url = f"https://www.instagram.com/{brand_id}/tagged/"
    page.goto(tagged_url, wait_until="domcontentloaded")
    page.wait_for_load_state("domcontentloaded")
    print("tagged 이동 후 URL:", page.url)

    if "/accounts/login" in page.url:
        raise RuntimeError(f"tagged 접근 실패(로그인으로 리다이렉트): {page.url}")

    dismiss_common_dialogs(page)
    page.wait_for_selector("a[href*='/p/']", timeout=10000)


def parse_post_date_kst(page, kst):
    try:
        page.wait_for_selector("time", state="visible", timeout=8000)
        time_el = page.locator("time").first
        dt_str = time_el.get_attribute("datetime")

        if dt_str:
            post_dt_utc = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            post_dt_kst = post_dt_utc.astimezone(kst)
            post_date_str = post_dt_kst.strftime("%Y-%m-%d")
            print(f"포스팅 날짜 문자열: {post_date_str}")
            return post_date_str
    except Exception:
        pass

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

    post_dt = datetime.strptime(match.group(1), "%B %d, %Y").replace(tzinfo=kst)
    post_date_str = post_dt.strftime("%Y-%m-%d")
    print(f"포스팅 날짜 문자열: {post_date_str}")
    return post_date_str


def extract_post_data(page, href):
    meta_title = page.evaluate(
        """
        () => document.querySelector('meta[property="og:title"]')?.getAttribute("content") || ""
        """
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
        """
        () => document.querySelector('meta[property="og:image"]')?.getAttribute("content") || ""
        """
    )

    image_candidates = page.evaluate(
        """
        () => Array.from(document.querySelectorAll("main img"))
            .map((img) => ({
                alt: img.getAttribute("alt") || "",
                src: img.getAttribute("src") || ""
            }))
            .filter((item) =>
                item.alt.startsWith("Photo by ") || item.alt.startsWith("Photo shared by ")
            )
        """
    )

    tags = []
    for item in image_candidates:
        alt = item["alt"]
        found = MENTION_RE.findall(alt)
        cleaned = [tag.rstrip(".,!?:;") for tag in found]
        tags.extend(cleaned)

        if not src and item["src"]:
            src = item["src"]

    seen = set()
    tags = [tag for tag in tags if not (tag in seen or seen.add(tag))]
    tags_cnt = len(tags)
    insta_tag = ",".join(tags) if tags else ""

    full_link = f"https://www.instagram.com{href}" if href else ""
    post_match = POST_URL_RE.search(full_link)

    post_id = post_match.group(1) if post_match else "unknown"
    insta_id = extract_insta_id(href, meta_desc)
    insta_name = extract_insta_name(meta_title, insta_id)

    return post_id, insta_id, insta_name, full_link, src, insta_tag, tags_cnt


def extract_insta_id(href, meta_desc):
    path_parts = [part for part in href.split("/") if part] if href else []
    if len(path_parts) >= 3 and path_parts[1] == "p":
        return path_parts[0].lower()

    owner_match = OWNER_DESC_RE.search(meta_desc or "")
    if owner_match:
        return owner_match.group(1).lower()

    return "unknown"


def extract_insta_name(meta_title, insta_id):
    title = (meta_title or "").strip()
    if not title:
        return "unknown"

    display_name_match = DISPLAY_NAME_RE.search(title)
    if not display_name_match:
        return "unknown"

    display_name = display_name_match.group(1).strip().strip('"').strip()
    if not display_name:
        return "unknown"

    if insta_id != "unknown" and display_name.lower() == insta_id.lower():
        return "unknown"

    return display_name


def snapshot_post_urls(page):
    hrefs = page.eval_on_selector_all(
        "a[href*='/p/']",
        "elements => elements.map(el => el.getAttribute('href'))",
    )

    seen = set()
    full_hrefs = []

    for href in hrefs:
        href = href.split("?")[0]
        if "/c/" in href:
            continue

        if href not in seen:
            seen.add(href)
            full_hrefs.append(href)

    return full_hrefs


def save_debug_artifact(page, url, reason, debug_dir="/tmp/insta_debug"):
    Path(debug_dir).mkdir(parents=True, exist_ok=True)
    post_code = url.strip("/").split("/")[-1] if url else "unknown"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(debug_dir, f"{reason}_{post_code}_{timestamp}.png")

    try:
        page.screenshot(path=screenshot_path, full_page=True)
        return screenshot_path
    except Exception as exc:
        print(f"⚠️ 스크린샷 저장 실패: {exc}")
        return None


def open_post_detail_page(detail_page, url):
    detail_url = f"https://www.instagram.com{url}"
    detail_page.goto(detail_url, wait_until="domcontentloaded")
    detail_page.wait_for_load_state("domcontentloaded")

    if "/accounts/login" in detail_page.url:
        raise RuntimeError(f"상세 페이지 접근 실패(로그인으로 리다이렉트): {detail_page.url}")

    detail_page.wait_for_function(DETAIL_READY_SCRIPT, timeout=10000)
    detail_page.wait_for_timeout(1500)
    return detail_page.url


def collect_posts_with_scroll(
    grid_page,
    detail_page,
    brand_id,
    brand_name,
    scroll_y,
    max_scrolls,
    wait_ms,
    kst,
    target_day,
):
    posts = []
    all_seen = set()
    past_date_streak = 0
    no_change_count = 0
    scroll_count = 0
    detail_fail_cnt = 0
    parsed_fail_cnt = 0
    stop_early = False
    stop_reason = None

    while scroll_count < max_scrolls and not stop_early:
        urls = snapshot_post_urls(grid_page)
        print(f"[스크롤 {scroll_count}] 스냅샷된 게시물: {len(urls)}개")

        before_count = len(all_seen)
        new_urls = [url for url in urls if url not in all_seen]
        print(f"새로운 게시물: {len(new_urls)}개")

        for url in new_urls:
            all_seen.add(url)

            try:
                print(f"처리 중: {url}")
                opened_url = open_post_detail_page(detail_page, url)
                print(f"상세 페이지 열림: {opened_url}")

                post_date = parse_post_date_kst(detail_page, kst)
                if post_date is None:
                    parsed_fail_cnt += 1
                    screenshot_path = save_debug_artifact(detail_page, url, "date_parse_fail")
                    print(f"⚠️ 날짜 추출 실패 → 스킵 {url}")
                    print(f"현재 detail URL: {detail_page.url}")
                    if screenshot_path:
                        print(f"디버그 스크린샷: {screenshot_path}")
                    continue

                print(f"목표: {target_day} | 실제: {post_date}")

                if target_day is not None and post_date < target_day:
                    past_date_streak += 1
                    print(f"📌 {past_date_streak}번째 연속 과거 게시물")

                    if past_date_streak >= 5:
                        print("✅ 5번 연속 과거 게시물 → 수집 종료(조기 종료 플래그)")
                        stop_early = True
                        stop_reason = "past_date_streak>=5"
                        break

                    continue

                past_date_streak = 0

                if target_day is None or post_date == target_day:
                    post_id, insta_id, insta_name, full_link, src, insta_tag, tags_cnt = extract_post_data(
                        detail_page, url
                    )
                    posts.append(
                        (
                            post_id,
                            insta_id,
                            insta_name,
                            brand_name,
                            brand_id,
                            full_link,
                            src,
                            post_date,
                            insta_tag,
                            tags_cnt,
                        )
                    )
                    print(f"✅ 수집 완료 ({len(posts)}개): {full_link}")

            except Exception as exc:
                detail_fail_cnt += 1
                screenshot_path = save_debug_artifact(detail_page, url, "detail_open_fail")
                print(f"❌ 상세 페이지 처리 실패: {url} - {exc}")
                print(f"현재 detail URL: {detail_page.url}")
                if screenshot_path:
                    print(f"디버그 스크린샷: {screenshot_path}")
                continue

        if stop_early:
            break

        after_count = len(all_seen)
        new_count = after_count - before_count

        if new_count == 0:
            no_change_count += 1
            print(f"⚠️ 새 게시물 없음 ({no_change_count}/3)")
        else:
            no_change_count = 0

        if no_change_count >= 3:
            print("✅ 3번 연속 새 게시물 없음 → 종료")
            break

        print(f"스크롤 진행 중... (누적: {after_count}개, 수집: {len(posts)}개)")
        grid_page.mouse.wheel(0, scroll_y)
        grid_page.wait_for_timeout(wait_ms)
        scroll_count += 1

    print(f"📊 최종 수집: {len(posts)}개 게시물")
    print(f"상세 페이지 처리 실패 건 수: {detail_fail_cnt}개")
    print(f"날짜 수집 실패 횟수: {parsed_fail_cnt}개")
    print(f"종료 사유: {stop_reason}")
    return posts


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
):
    kst = timezone(timedelta(hours=9))
    username = username or os.getenv("ID")
    password = password or os.getenv("PW")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=state_path)
        grid_page = context.new_page()

        ensure_logged_in(grid_page, login_url, username, password)
        goto_tagged(grid_page, brand_id)

        detail_page = context.new_page()
        posts = collect_posts_with_scroll(
            grid_page=grid_page,
            detail_page=detail_page,
            brand_id=brand_id,
            brand_name=brand_name,
            scroll_y=scroll_y,
            max_scrolls=max_scrolls,
            wait_ms=wait_ms,
            kst=kst,
            target_day=target_day,
        )

        detail_page.close()
        grid_page.close()
        browser.close()

    print("✅수집된 데이터 type 확인")
    print(posts[0:1])
    return posts


def main():
    run(
        state_path="/opt/airflow/secrets/storage_state.json",
        brand_name="amomento",
        brand_id="amomento.co",
        headless=False,
    )


if __name__ == "__main__":
    main()
