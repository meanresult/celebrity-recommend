# filename: mini_playwright.py
from playwright.sync_api import sync_playwright
import requests
from dotenv import load_dotenv
import os 
from openpyxl import Workbook

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

        try:
            page.get_by_role("button", name="나중에 하기").click(timeout=5000)
        except:
            pass  # 버튼이 없으면 그냥 넘어감
        
        # 5) 로그인 성공 대기 (피드 페이지로 이동할 때까지)
        page.wait_for_load_state("domcontentloaded")
        
        print("로그인 성공!")
        
        # # # 검색 클릭
        # page.get_by_role("button", name="검색").click()
        # page.fill("input[aria-label='입력 검색']", "amomento.co")
        # page.wait_for_timeout(2000)
        # page.locator("div[role='none'] a").first.click()

        # # 이후 원하는 URL로 이동
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_load_state("domcontentloaded")

        print("아모멘토 페이지 도착, 브라우저 유지 중...")
        page.wait_for_timeout(15000)

        # =============================
        # 게시물 데이터 수집
        # =============================
        posts = []
        
        # 게시물 카드가 로드될 때까지 대기
        page.wait_for_selector("a[href*='/p/']",state="attached", timeout=10000)

        # 게시물 링크(anchor 태그) 선택
        post_links = page.locator("a[href*='/p/']")
        print(f"발견된 게시물 수: {post_links.count()}")
        print(f"post_linkks 타입: {type(post_links)}")

        ct = min(post_links.count(), 10)
        print(f"수집할 게시물 수: {ct}")

        # 중복 제거를 위해 set 사용
        seen = set()

        for idx in range(ct):  # 앞 10개만 테스트
            link = post_links.nth(idx - 1)
            href = link.get_attribute("href")  # 게시물 링크
            #예시 출력
            print(f"href[{idx}]:", href)

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

                posts.append((insta_id, full_link, src))

        # =============================
        # 4) 엑셀 저장
        # =============================
        wb = Workbook()
        ws = wb.active
        ws.title = "Instagram Posts"

        # 첫 행 제목
        ws.append(["insta ID","Post Link", "Image URL"])

        # 데이터 행 추가
        for id, link, img in posts:
            ws.append([id,link, img])

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
