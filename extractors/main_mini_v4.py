from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
from openpyxl import Workbook
from datetime import datetime, timezone, timedelta

load_dotenv()

LOGIN_URL = "https://www.instagram.com/?flo=true"
TAGGED_URL = "https://www.instagram.com/amomento.co/tagged/"
USERNAME = "pywh_"
PW = os.getenv("PW")

KST = timezone(timedelta(hours=9))


def login(page):
    """인스타 로그인 수행"""
    page.goto(LOGIN_URL, wait_until="domcontentloaded")

    page.wait_for_selector("input[name='username']")
    page.wait_for_selector("input[name='password']")

    page.fill("input[name='username']", USERNAME)
    page.fill("input[name='password']", PW)

    page.click("button[type='submit']")

    # 팝업이 뜰 수도 있으니 시도만 해보고 없으면 패스
    try:
        page.get_by_role("button", name="나중에 하기").click(timeout=5000)
    except:
        pass

    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(3000)  # 추가 대기
    print("로그인 이후 URL:", page.url)


def goto_tagged(page):
    """tagged 페이지로 이동 + 기본 로드 대기"""
    page.goto(TAGGED_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("domcontentloaded")
    print("tagged 이동 후 URL:", page.url)

    # 게시물 링크가 화면에 붙을 때까지 대기
    page.wait_for_selector("a[href*='/p/']", timeout=10000)


def calculate_days_diff(dt_str: str, now_kst: datetime = None) -> tuple:
    """순수 함수 — ISO datetime 문자열 → (post_dt_kst, post_date, days_diff)

    브라우저 없이 단독 테스트 가능하도록 page 의존성 분리.
    now_kst를 주입받으면 테스트 시 고정된 기준 시각 사용 가능.
    """
    post_dt_utc = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    post_dt_kst = post_dt_utc.astimezone(KST)

    if now_kst is None:
        now_kst = datetime.now(KST)

    days_diff = (now_kst.date() - post_dt_kst.date()).days
    return post_dt_kst, post_dt_kst.date(), days_diff


def parse_href(href: str) -> tuple:
    """순수 함수 — href → (insta_id, full_link)"""
    if not href:
        return "unknown", ""
    insta_id = href.strip("/").split("/p/")[0]
    full_link = "https://www.instagram.com" + href
    return insta_id, full_link


def parse_post_date_kst(page):
    """상세 화면(게시물)에서 datetime 읽어서 KST datetime + date + days_diff 반환"""
    page.wait_for_selector("time", state="visible", timeout=5000)

    time_el = page.locator("time").first
    dt_str = time_el.get_attribute("datetime")
    if not dt_str:
        return None, None, None

    return calculate_days_diff(dt_str)


def extract_post_data(page, href):
    """상세 화면에서 이미지(src) 등 필요한 정보 추출 (필요시 확장)"""
    img = page.locator("article img").first
    src = img.get_attribute("src") if img else None

    insta_id, full_link = parse_href(href)
    return insta_id, full_link, src


def collect_posts_with_scroll(page, target=60, max_scroll=7, scroll_y=3000, wait_ms=5000):
    """스크롤하면서 게시물 열어보고(클릭) 오늘/어제만 수집"""
    posts = []
    seen = set()

    for s in range(max_scroll):
        links = page.locator("a[href*='/p/']")
        count = links.count()
        print(f"[스크롤 {s}] 현재 카드 수: {count}, 수집된 posts: {len(posts)}")

        # 현재 화면에 잡힌 카드들을 순회
        for idx in range(count):
            link = links.nth(idx)
            href = link.get_attribute("href")

            if not href or href in seen:
                continue

            # 일단 seen에 넣어서 중복 방지(스크롤/리렌더 대응)
            seen.add(href)

            # 상세 열기
            link.click()

            # 날짜 판단
            post_dt_kst, post_date, days_diff = parse_post_date_kst(page)
            if post_date is None:
                page.go_back()
                continue

            print(f"게시물[{idx}] 작성일: {post_dt_kst} (days_diff={days_diff})")

            # ✅ 오늘/어제만
            if days_diff == 1:
                insta_id, full_link, src = extract_post_data(page, href)
                posts.append((insta_id, full_link, src, post_date))
                print("✅ 수집됨:", full_link, " / posts:", len(posts))

            # 목록으로 복귀
            page.go_back()

            # 목표 수집 개수 채우면 종료
            if len(posts) >= target:
                print("✅ posts 목표 개수 도달 → 종료")
                return posts

        # 목표(카드 로딩 개수 기준)로 멈추는 게 아니라, 실제 수집(posts) 기준이 더 정확함
        page.mouse.wheel(0, scroll_y)
        page.wait_for_timeout(wait_ms)

        new_count = page.locator("a[href*='/p/']").count()
        if new_count == count:
            print("📌 스크롤해도 카드가 늘지 않음 → 종료")
            break

    return posts


def save_to_excel(posts, filename="instagram_posts.xlsx"):
    """수집 결과를 엑셀로 저장"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Instagram Posts"

    ws.append(["insta ID", "Post Link", "Image URL", "Post Date"])

    for insta_id, link, img, post_date in posts:
        ws.append([insta_id, link, img, post_date])

    wb.save(filename)
    print(f"📂 '{filename}' 저장 완료! (총 {len(posts)}개)")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        login(page)
        goto_tagged(page)

        posts = collect_posts_with_scroll(
            page,
            target=60,
            max_scroll=4,
            scroll_y=900,
            wait_ms=5000
        )

        save_to_excel(posts)

        browser.close()


if __name__ == "__main__":
    main()

#######################
###### 코드 리뷰 ########
#######################

""" 
개선된 것 : 코드 함수로 정리하여 가독성 향상, 중복 코드 제거, 스크롤 및 게시물 수집 로직 개선, 엑셀 저장 로직 분리
발견된 문제점 : 
    - 스크롤했을 때 다음 게시물을 제대로 잡지 못함 
    - posts 게시일이 오래된 것들이 연속으로 나오면 종료해도 되는데 계속 스크롤 시도 (비효율적)

수정 제안 :
    - 스크롤 후 게시물 수가 증가하지 않으면 종료하도록 로직 추가
    - 스크롤 파라미터 조정 (완료)

data 파이프라인을 먼저 생성한 후에 추후에 수정할 예정 
"""