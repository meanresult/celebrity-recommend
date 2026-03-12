# filename: mini_playwright.py
from playwright.sync_api import sync_playwright
import requests
from dotenv import load_dotenv
import os 
from openpyxl import Workbook
from datetime import datetime, timezone, timedelta

load_dotenv()
LOGIN_URL= "https://www.instagram.com/?flo=true"
URL = "https://www.instagram.com/amomento.co/tagged/"  # 나중에 원하는 주소로 변경
SELECTOR = "h3"                         # 가져올 요소(원하는 CSS로 변경)
USERNAME = 'pywh_'
PW = os.getenv('PW')


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 서버면 True
        page = browser.new_page()
        # 로그인 페이지 열기
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        
        # 입력창이 뜰때까지 기다리기
        page.wait_for_selector("input[name='username']")
        page.wait_for_selector("input[name='password']")

        print('*'*30)
        print("PW =", PW, type(PW))
        print('*'*30)
        
        # 정보 넣기 전 다시 확인 
        user_lo = page.locator("input[name='username']")
        user_lo.wait_for(state="visible", timeout=5000)
        # 2초 기다리기 
        page.wait_for_timeout(2000)
        # 3) 로그인 정보 넣기 
        page.fill("input[name='username']", USERNAME)
        page.fill("input[name='password']", PW)
        
        # 4) 로그인 버튼 클릭
        page.click("button[type='submit']")
        print("로그인 클릭 후 URL:", page.url)

        try:
            page.get_by_role("button", name="나중에 하기").click(timeout=5000)
        except:
            pass  # 버튼이 없으면 그냥 넘어감
        
        # 5) 로그인 성공 대기 (피드 페이지로 이동할 때까지)
        page.wait_for_load_state("domcontentloaded")
        
        
        
        # # # 검색 클릭
        # page.get_by_role("button", name="검색").click()
        # page.fill("input[aria-label='입력 검색']", "amomento.co")
        # page.wait_for_timeout(2000)
        # page.locator("div[role='none'] a").first.click()


        # 2초 기다리기 
        page.wait_for_timeout(5000)

        # # 이후 원하는 URL로 이동
        page.goto(URL, wait_until="domcontentloaded")
        print("tagged 이동 후 URL:", page.url)
        page.wait_for_load_state("domcontentloaded")

        print("아모멘토 페이지 도착, 브라우저 유지 중...")
        page.wait_for_timeout(15000)


        # =============================
        # 게시물 데이터 수집
        # =============================
        #결과를 저장할 리스트 
        posts = []
        
        # 중복 링크를 막기 위한 저장소
        seen = set()


        # 게시물 카드가 로드될 때까지 대기
        page.wait_for_selector("a[href*='/p/']",state="attached", timeout=10000)

        # 게시물 링크(anchor 태그) 선택 ######################################################
        post_links = page.locator("a[href*='/p/']")

        post_links60 = min(post_links.count(), 60) #
        print(f"수집할 게시물 수: {post_links60}")


        for idx in range(post_links60):  # 앞 10개만 테스트
            link = post_links.nth(idx)
            href = link.get_attribute("href")  # 게시물 링크
            #예시 출력
            print(f"href[{idx}]:", href)

            link.click()  # 게시물 클릭하여 상세 페이지로 이동
            page.wait_for_selector("time", state="visible", timeout=5000)

            # 게시물의 시간 정보 추출 
            time_el = page.locator("time").first
            dt_str = time_el.get_attribute("datetime")  # 예: '2024-06-15T12:34:56.000Z'
            dt_str_fixed = datetime.fromisoformat(dt_str.replace("Z", "+00:00")) # ISO 포맷으로 변환

            # 한국 시간대로 변경
            transformed_korean_time = timezone(timedelta(hours=9)) # 한국 시간으로 변경 

            # 현재시간 게시물 포스팅 시간 한국 시간대로 변경
            korean_posttime = dt_str_fixed.astimezone(transformed_korean_time)
            now_korean_time = datetime.now(transformed_korean_time)

            # 날짜로 바꿔주기
            post_date = korean_posttime.date()
            now_date = now_korean_time.date()

            days_diff = (now_date - post_date).days # 게시물 작성일과 현재일의 차이 계산
            print(f"게시물 작성일[{idx}]:", korean_posttime, f"(현재와의 일수 차이: {days_diff}일)")

            if days_diff == 1: # 오늘(0) 또는 어제(1) 게시물 수집 대상
                insta_id = href.strip("/").split("/p/")[0] if href else "unknown"
                print(f"insta_id[{idx}]:", insta_id)

                if href and href not in seen:
                    seen.add(href)
                    full_link = "https://www.instagram.com" + href
    
                    # 게시물 안의 이미지 태그 찾기
                    img = link.locator("img").first
                    src = img.get_attribute("src") if img else None

                    print(f"[{idx}] 링크: {full_link}")
                    print(f"     사진: {src}")

                    posts.append((insta_id, full_link, src, post_date))
                    print("posts 개수:", len(posts))
            else :
                pass  # 그 외는 수집하지 않음

            page.go_back()  # 이전 페이지(게시물 목록)로 돌아가기   
            # ##########



        # =============================
        # 4) 엑셀 저장
        # =============================
        wb = Workbook()
        ws = wb.active
        ws.title = "Instagram Posts"

        # 첫 행 제목
        ws.append(["insta ID","Post Link", "Image URL", "Post Time"])

        # 데이터 행 추가
        for id, link, img, post_date in posts:
            ws.append([id,link, img, post_date])

        # 엑셀 파일 저장
        wb.save("instagram_posts.xlsx")
        print("📂 'instagram_posts.xlsx' 파일 저장 완료!")

        # =============================
        # 예시: 페이지 HTML 일부 출력
        # =============================
        
        print(page.content()[:500])

        texts = [t.strip() for t in page.locator(SELECTOR).all_text_contents()]
        for t in texts:
            if t:
                print(t)

        browser.close()

if __name__ == "__main__":
    main()
