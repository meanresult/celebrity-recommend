from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
from openpyxl import Workbook
from datetime import datetime, timezone, timedelta
import time


load_dotenv()
# 로그인 상태 확인 함수
def assert_logged_in(page):
    cookies = page.context.cookies()
    cookie_names = {c["name"] for c in cookies}

    # 인스타 로그인 핵심 쿠키(대표)
    if "sessionid" not in cookie_names:
        # 디버깅용으로 어떤 쿠키가 있는지 찍어두면 원인 파악이 빨라짐
        raise RuntimeError(f"로그인 세션(sessionid) 없음. 현재 URL={page.url}, cookies={sorted(cookie_names)}")

# 세션 ID를 기다리는 함수
def wait_for_sessionid(page, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        cookies = page.context.cookies()
        if any(c["name"] == "sessionid" for c in cookies):
            return True
        page.wait_for_timeout(500)
    return False

# 로그인 함수

def login(page,LOGIN_URL, USERNAME, PW):
    """인스타 로그인 수행"""
    page.goto(LOGIN_URL, wait_until="domcontentloaded")

    page.wait_for_selector("input[name='username'], input[name='email']")
    page.wait_for_selector("input[name='password'], input[name='pass']")

    if page.locator("input[name='email']").first.is_visible():
        page.fill("input[name='email']", USERNAME)
        page.fill("input[name='pass']", PW)
        page.get_by_role("button", name="로그인").click() # 이메일 로그인 버튼
    else:
        page.fill("input[name='username']", USERNAME)
        page.fill("input[name='password']", PW)
        page.click("button[type='submit']")


    #page.wait_for_selector("a[href*='/pywh_/']", timeout=10000)

    # 간혹 로그인 페이지로 다시 뜨는 경우
    # try:
    #     page.wait_for_selector(
    #         "input[name='email'], input[name='username']",
    #         timeout=10000,
    #         state="visible"
    #     )
    #     if page.locator("input[name='email']").first.is_visible():
    #         page.fill("input[name='email']", USERNAME)
    #         page.fill("input[name='pass']", PW)
    #     else:
    #         page.fill("input[name='username']", USERNAME)
    #         page.fill("input[name='password']", PW)
    #     page.click("button[type='submit']")

    # except: 
    #     pass

    # 팝업이 뜰 수도 있으니 시도만 해보
    for _ in range(3):  # 최대 3번까지 시도
        try:
            page.get_by_role("button", name="나중에 하기").click(timeout=3000)
            page.wait_for_timeout(1000)  # 다음 팝업 뜰 시간
        except:
            break

    try:
        page.click("div[role='button'][has-text()='나중에 하기']", timeout=5000)
    except:
        pass

    # 로그인 페이지를 "벗어날 때"까지 기다림
    page.wait_for_timeout(3000)  # 추가 대기

    assert_logged_in(page)
    print("✅ 로그인 성공:", page.url)

    ok = wait_for_sessionid(page, timeout=20)
    if not ok:
        cookies = page.context.cookies()
        cookie_names = sorted({c["name"] for c in cookies})
        raise RuntimeError(f"sessionid 발급 실패. url={page.url}, cookies={cookie_names}")

def goto_tagged(page, brand_id):
    """tagged 페이지로 이동 + 기본 로드 대기"""
    
    tagged_url =str(f"https://www.instagram.com/{brand_id}/tagged/")
    page.goto(tagged_url, wait_until="domcontentloaded")
    page.wait_for_load_state("domcontentloaded")
    print("tagged 이동 후 URL:", page.url)

    # tagged 가려다 로그인으로 튕겼는지 즉시 확인
    if "/accounts/login" in page.url:
        raise RuntimeError(f"tagged 접근 실패(로그인으로 리다이렉트): {page.url}")

    try:
        page.click("div[rlole='button'][text()='나중에 하기']", timeout=5000)
    except:
        pass

    # 게시물 링크가 화면에 붙을 때까지 대기
    page.wait_for_selector("a[href*='/p/']", timeout=10000)


def parse_post_date_kst(page , KST):
    page.wait_for_selector("time", state="visible", timeout=5000)

    time_el = page.locator("time").first
    dt_str = time_el.get_attribute("datetime")
    if not dt_str:
        return None, None, None

    post_dt_utc = datetime.fromisoformat(dt_str.replace("Z", "+00:00")) # 'YYYY-MM-DD' 형식으로 변환
    
    post_dt_kst = post_dt_utc.astimezone(KST)


    post_date_str = post_dt_kst.strftime('%Y-%m-%d') # 'YYYY-MM-DD' 형식 문자열
    print(f"포스팅 날짜 문자열: {post_date_str}")

    return post_date_str


def extract_post_data(page, href):
    """상세 화면에서 이미지(src) 등 필요한 정보 추출 (필요시 확장)"""
    # 상세 화면에서 대표 이미지 찾기(상황에 따라 selector가 달라질 수 있음)
    img = page.locator("article img").first
    src = img.get_attribute("src") if img else None

    insta_id = href.strip("/").split("/p/")[0] if href else "unknown"
    post_id = href.strip("/").split("/p/")[1] if href else "unknown"   
    full_link = "https://www.instagram.com" + href

    return post_id,insta_id, full_link, src


def collect_posts_with_scroll(page, brand_id, brand_name,scroll_y, wait_ms,KST, target_day):
    """스크롤하면서 게시물 열어보고(클릭) 오늘/어제만 수집"""
    posts = []
    seen = set()
    past_date_streak = 0

    while True:
        links = page.locator("a[href*='/p/']")
        total_links = links.count()

        for s in range(total_links):
            print(f"[스크롤 {s}] 현재 카드 수: {total_links}, 수집된 posts: {len(posts)}")

            link = links.nth(s) # 현재 카드 선택
            href = link.get_attribute("href") # href 추출

            if not href or href in seen:
                continue

            # 일단 seen에 넣어서 중복 방지(스크롤/리렌더 대응)
            seen.add(href)

            # 상세 열기
            link.click()

            # 날짜 판단 없으면 돌아가기
            post_date = parse_post_date_kst(page, KST)
            if target_day is None:
                page.go_back()
                continue

            print(f"게시물[{s}] 수집날짜: {target_day}, 포스팅날짜: {post_date}")


            # 종료조건
            if post_date < target_day:
                past_date_streak += 1
                page.go_back()
                print(f"📌 {past_date_streak}번째 연속으로 목표일 이전 게시물 발견")

                if past_date_streak >= 3:
                    print("📌 3번 연속 목표일 이전 게시물 → 수집 종료")
                    return posts
                continue

            # ✅ 오늘/어제만
            if post_date == target_day:
                past_date_streak = 0 # 타겟 게시물이 조회되면 초기화 
                post_id,insta_id,  full_link, src = extract_post_data(page, href)
                posts.append((post_id,insta_id, brand_name, brand_id, full_link, src, target_day))
                print("✅ 수집됨:", full_link, " / posts:", len(posts))

            # 목록으로 복귀
            page.go_back()

        # 목표(카드 로딩 개수 기준)로 멈추는 게 아니라, 실제 수집(posts) 기준이 더 정확함
        page.mouse.wheel(0, scroll_y)
        page.wait_for_timeout(wait_ms)

        new_count = page.locator("a[href*='/p/']").count()
        if new_count == total_links:
            print("📌 스크롤해도 카드가 늘지 않음 → 종료")
            break

    return posts


def save_to_excel(posts, filename="instagram_posts.xlsx"):
    """수집 결과를 엑셀로 저장"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Instagram Posts"

    ws.append(["post_id","insta ID", "Post Link", "Image URL", "Post Date"])

    for post_id, insta_id, brand_name, brand_id, full_link, src, post_date in posts:
        ws.append([post_id,insta_id, brand_name, brand_id, full_link, src, post_date])

    wb.save(filename)
    print(f"📂 '{filename}' 저장 완료! (총 {len(posts)}개)")


def run(
    # 로그인 관련
    STATE_PATH = "/opt/airflow/secrets/storage_state.json",
    LOGIN_URL = "https://www.instagram.com/accounts/login/",
    USERNAME = os.getenv("ID"),
    PW = os.getenv("PW"),
    brand_name: str = None,
    brand_id: str = None,
    scroll_y: int = 900,
    wait_ms: int = 5000,
    headless: bool = True,
    target_day: datetime = None,
):
    KST = timezone(timedelta(hours=9))
    USERNAME = USERNAME or os.getenv("ID")
    PW = PW or os.getenv("PW")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=STATE_PATH)
        page = context.new_page()

        login(page, LOGIN_URL, USERNAME, PW)
        goto_tagged(page, brand_id)

        posts = collect_posts_with_scroll(
            page,
            brand_id=brand_id,
            brand_name=brand_name,
            scroll_y=scroll_y,
            wait_ms=wait_ms,
            KST=KST,
            target_day=target_day
        )

        save_to_excel(posts)
        

        browser.close()
    print(posts[0:2])  # 수집된 데이터 일부 출력
    return posts  # or filename

def main():
    run(
        STATE_PATH = "/opt/airflow/secrets/storage_state.json",
        tagged_url= "https://www.instagram.com/amomento.co/tagged/",
        headless=False,  # 로컬에서는 브라우저 보이게
    )

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