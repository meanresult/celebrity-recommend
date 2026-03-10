"""
목표 : 컬럼 추가 마지막 크롤링 날짜, 활성화 여부 
"""

from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
from openpyxl import Workbook
from datetime import datetime, timezone, timedelta
import time
import re 
from pathlib import Path


load_dotenv()
#########################################
# 로그인 상태 확인 함수
#########################################
def assert_logged_in(page):
    cookies = page.context.cookies()
    cookie_names = {c["name"] for c in cookies}

    # 인스타 로그인 핵심 쿠키(대표)
    if "sessionid" not in cookie_names:
        # 디버깅용으로 어떤 쿠키가 있는지 찍어두면 원인 파악이 빨라짐
        raise RuntimeError(f"로그인 세션(sessionid) 없음. 현재 URL={page.url}, cookies={sorted(cookie_names)}")


#########################################
# 세션 ID를 기다리는 함수
#########################################
def wait_for_sessionid(page, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        cookies = page.context.cookies()
        if any(c["name"] == "sessionid" for c in cookies):
            return True
        page.wait_for_timeout(500)
    return False
#########################################
# 세션 페이지 먼저 접속 
#########################################
def ensure_logged_in(page, LOGIN_URL, USERNAME, PW):
    # 1) 먼저 홈으로 가서 세션이 먹는지 확인
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded") 
    page.wait_for_timeout(1000)

    # 2) login으로 튕겼으면 그때만 로그인
    if "/accounts/login" in page.url:
        print("🔁 홈 접근이 로그인으로 리다이렉트 → login() 수행")
        login(page, LOGIN_URL, USERNAME, PW)
        return
    
#########################################
# 로그인 함수
#########################################
def login(page,LOGIN_URL, USERNAME, PW):
    """인스타 로그인 수행"""
    page.goto(LOGIN_URL, wait_until="domcontentloaded")

    page.wait_for_selector("input[name='username'], input[name='email']")
    page.wait_for_selector("input[name='password'], input[name='pass']")

    if page.locator("input[name='email']").first.is_visible():
        page.fill("input[name='email']", USERNAME)
        page.fill("input[name='pass']", PW)
        page.get_by_role("button", name="정보 저장").click() # 이메일 로그인 버튼
    else:
        page.fill("input[name='username']", USERNAME)
        page.fill("input[name='password']", PW)
        page.click("button[type='submit']")
    

    page.wait_for_timeout(3000)

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

#########################################
# 브랜드 계정 링크 함수 
#########################################
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


#########################################
# 한국 시간대로 확인하기 좋기 변경
#########################################
def parse_post_date_kst(page , KST):
    try:
        page.wait_for_selector("time", state="visible", timeout=5000)

        time_el = page.locator("time").first
        dt_str = time_el.get_attribute("datetime")
        if dt_str:
            post_dt_utc = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            post_dt_kst = post_dt_utc.astimezone(KST)
            post_date_str = post_dt_kst.strftime('%Y-%m-%d')
            print(f"포스팅 날짜 문자열: {post_date_str}")
            return post_date_str
    except Exception:
        pass

    meta_desc = page.evaluate("""
        () => (
            document.querySelector('meta[property="og:description"]')?.getAttribute('content') ||
            document.querySelector('meta[name="description"]')?.getAttribute('content') ||
            ''
        )
    """)

    match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', meta_desc)
    if not match:
        return None

    post_dt = datetime.strptime(match.group(1), "%B %d, %Y").replace(tzinfo=KST)
    post_date_str = post_dt.strftime('%Y-%m-%d')
    print(f"포스팅 날짜 문자열: {post_date_str}")
    return post_date_str


#########################################
# 브랜드 계정을 태그한 insta_id 정보 추출 크롤링
#########################################
MENTION_RE = re.compile(r'@[\w\.]+')  # 인스타 아이디는 보통 영문/숫자/._ 조합

def extract_post_data(page, href):
    """
    상세 화면에서 대표 이미지(src) + 이미지 alt에서 계정태그(@...) 추출
    - 실무적으로: '수집(list) -> 저장 직전 string 변환(join)' 흐름 유지
    """

    src = page.evaluate("""
        () => document.querySelector('meta[property="og:image"]')?.getAttribute('content') || ''
    """)

    image_candidates = page.evaluate("""
        () => Array.from(document.querySelectorAll('main img'))
            .map((img) => ({
                alt: img.getAttribute('alt') || '',
                src: img.getAttribute('src') || ''
            }))
            .filter((item) => item.alt.startsWith('Photo by ') || item.alt.startsWith('Photo shared by '))
    """)

    tags = []
    for item in image_candidates:
        alt = item["alt"]
        found = MENTION_RE.findall(alt)
        cleaned = [t.rstrip(".,!?:;") for t in found]
        tags.extend(cleaned)

        if not src and item["src"]:
            src = item["src"]

    # 중복 제거 + 순서 유지
    seen = set()
    tags = [t for t in tags if not (t in seen or seen.add(t))]
    tags_cnt = len(tags)

    # 저장용 문자열 (엑셀/DB에 바로 넣을 값)
    insta_tag = ",".join(tags) if tags else ""

    # 인스타 아이디 및 링크 추출

    insta_id = href.strip("/").split("/p/")[0] if href else "unknown"
    post_id = href.strip("/").split("/p/")[1] if href else "unknown"
    full_link = "https://www.instagram.com" + href if href else ""

    return post_id, insta_id, full_link, src, insta_tag,tags_cnt

#########################################
# 게시물 링크 한번에 가져오기 
#########################################
def snapshot_post_urls(page):
    hrefs = page.eval_on_selector_all(
    "a[href*='/p/']",
    "elements => elements.map(el => el.getAttribute('href'))"
    ) # 게시물 링크들 한번에 스냅샷

    seen = set() # 중복 제거용 세트
    full_hrefs = [] # 최종 링크 리스트

    for href in hrefs:
        
        href = href.split("?")[0]  # 쿼리스트링 제거
        if "/c/" in href:
            continue  # 광고 게시물 스킵

        if href not in seen:
            seen.add(href)
            full_hrefs.append(href)
        else:
            continue

    return full_hrefs


#########################################
# 디버그 스크린샷 저장
#########################################
def save_popup_debug_artifact(page, url, debug_dir="/tmp/insta_debug"):
    Path(debug_dir).mkdir(parents=True, exist_ok=True)
    post_code = url.strip("/").split("/")[-1] if url else "unknown"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(debug_dir, f"popup_fail_{post_code}_{timestamp}.png")
    try:
        page.screenshot(path=screenshot_path, full_page=True)
        return screenshot_path
    except Exception as exc:
        print(f"⚠️ 스크린샷 저장 실패: {exc}")
        return None


#########################################
# 게시물 상세 진입 상태 판별
#########################################
def wait_for_post_open(page, timeout_ms=10000):
    deadline = time.time() + (timeout_ms / 1000)

    while time.time() < deadline:
        current_url = page.url

        # 전체 페이지 상세 진입
        if "/p/" in current_url:
            return "detail_page"

        # 모달 기반 상세 진입
        if page.locator("[role='dialog']").count() > 0 or page.locator("button[aria-label='닫기']").count() > 0:
            return "popup"

        page.wait_for_timeout(300)

    return None



#########################################
# 크롤링 함수 메인
#########################################
def collect_posts_with_scroll(page, brand_id, brand_name, scroll_y, MAX_SCROLLS, wait_ms, KST, target_day):
    """스크롤하면서 게시물 열어보고 target_day만 수집"""
    posts = []
    all_seen = set()
    past_date_streak = 0 # 스냅샷 안 목표게시물 보다 이전 데이터 수
    no_change_count = 0 # 현재 스냅샷 까지 더한 총 스냅샷 갯수와 이전 스냅샷 총갯수 비교
    scroll_count = 0 # 스크롤 카운트 
    popup_fail_cnt = 0 # 파업 실패 카운트
    parsed_fail = 0 # 날짜 수집 실패 횟수 

    # 종료 트리거 
    stop_early = False
    stop_reason = None

    while scroll_count < MAX_SCROLLS and not stop_early:
        # 현재 화면의 게시물 URL 스냅샷
        urls = snapshot_post_urls(page)
        print(f"[스크롤 {scroll_count}] 스냅샷된 게시물: {len(urls)}개")

        before_count = len(all_seen)
        new_urls = [url for url in urls if url not in all_seen]
        
        print(f"새로운 게시물: {len(new_urls)}개")

        # 새로운 게시물 처리
        for url in new_urls:
            all_seen.add(url)
            
            try:
                print(f"처리 중: {url}")
                
                # ✅ 개선: JavaScript로 직접 클릭 (오버레이 회피)
                page.evaluate(f"""
                    () => {{
                        const link = document.querySelector('a[href="{url}"]');
                        if (link) link.click();
                    }}
                """)

                open_state = wait_for_post_open(page, timeout_ms=10000)

                if open_state == "popup":
                    print(f"팝업 상세 진입 성공: {url}")
                elif open_state == "detail_page":
                    print(f"상세 페이지 이동 감지: {page.url}")
                    page.goto(f"https://www.instagram.com{url}", wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
                else:
                    screenshot_path = save_popup_debug_artifact(page, url)
                    print(f"⚠️ 팝업 로드 실패: {url}")
                    print(f"현재 URL: {page.url}")
                    print("팝업 또는 상세 페이지 진입을 확인하지 못했습니다.")
                    if screenshot_path:
                        print(f"디버그 스크린샷: {screenshot_path}")
                    popup_fail_cnt += 1
                    page.keyboard.press("Escape")
                    continue

                # 날짜 파싱
                post_date = parse_post_date_kst(page, KST)
                if post_date is None:
                    print(f"⚠️ 날짜 추출 실패 → 스킵{url}")
                    parsed_fail += 1
                    if open_state == "detail_page":
                        page.go_back()
                        page.wait_for_timeout(1000)
                    else:
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(500)
                    continue

                print(f"목표: {target_day} | 실제: {post_date}")

                # 종료 조건: 연속으로 오래된 게시물 발견
                if post_date < target_day:
                    past_date_streak += 1
                    print(f"📌 {past_date_streak}번째 연속 과거 게시물")
                    
                    if past_date_streak >= 5:
                        print("✅ 5번 연속 과거 게시물 → 수집 종료(조기 종료 플래그)")
                        stop_early = True
                        stop_reason = "past_date_streak>=5"
                        if open_state == "detail_page":
                            page.go_back()
                            page.wait_for_timeout(1000)
                        else:
                            page.keyboard.press("Escape")
                        break  
                    
                    if open_state == "detail_page":
                        page.go_back()
                        page.wait_for_timeout(1000)
                    else:
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(500)
                    continue
                else:
                    past_date_streak = 0

                # target_day 게시물만 수집
                if post_date == target_day:
                    post_id, insta_id, full_link, src, insta_tag, tags_cnt = extract_post_data(page, url)
                    posts.append((
                        post_id, insta_id, brand_name, brand_id, 
                        full_link, src, target_day, insta_tag, tags_cnt
                    ))
                    print(f"✅ 수집 완료 ({len(posts)}개): {full_link}")

                # 팝업 닫기
                if open_state == "popup":
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
                elif open_state == "detail_page":
                    page.go_back()
                    page.wait_for_timeout(1000)

            except Exception as e:
                print(f"❌ 오류 발생: {url} - {str(e)}")
                try:
                    if "/p/" in page.url:
                        page.go_back()
                        page.wait_for_timeout(1000)
                    else:
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(500)
                except:
                    pass
                continue
        
        if stop_early:
            break

        # 스크롤 후 새 게시물 체크
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

        # 스크롤
        print(f"스크롤 진행 중... (누적: {after_count}개, 수집: {len(posts)}개)")
        page.mouse.wheel(0, scroll_y)
        page.wait_for_timeout(wait_ms)
        scroll_count += 1

    print(f"📊 최종 수집: {len(posts)}개 게시물")
    print(f"팝업창 로딩 실패 건 수 : {popup_fail_cnt}개")
    print(f"날짜 수집 실패 횟수: {parsed_fail}개")
    print(f"종료 사유: {stop_reason}")
    return posts



def run(
    # 로그인 관련
    STATE_PATH = "/opt/airflow/secrets/storage_state.json",
    LOGIN_URL = "https://www.instagram.com/accounts/login/",
    USERNAME = os.getenv("ID"),
    PW = os.getenv("PW"),
    brand_name: str = None,
    brand_id: str = None,
    scroll_y: int = 700,
    MAX_SCROLLS: int = 50,
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

        ensure_logged_in(page, LOGIN_URL, USERNAME, PW)
        goto_tagged(page, brand_id)

        posts = collect_posts_with_scroll(
            page,
            brand_id=brand_id,
            brand_name=brand_name,
            scroll_y=scroll_y,
            MAX_SCROLLS =MAX_SCROLLS,
            wait_ms=wait_ms,
            KST=KST,
            target_day=target_day
        )
        

        browser.close()
    print(f'✅수집된 데이터 type 확인')
    print(posts[0:1])  # 수집된 데이터 일부 출력
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
