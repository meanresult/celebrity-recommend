# save_state.py
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os

load_dotenv()
USERNAME = "pywh_"
PW = os.getenv("PW")

LOGIN_URL = "https://www.instagram.com/accounts/login/"
STATE_PATH = "storage_state.json"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 로컬은 눈으로 확인하기 쉬움
        context = browser.new_context()
        page = context.new_page()

        page.goto(LOGIN_URL)
        print("브라우저에서 로그인 완료(사람이 직접 or 자동)한 다음, 인스타 메인 화면이 보이면 엔터를 누르세요.")

        page.wait_for_selector("input[name='username'], input[name='email']")
        page.wait_for_selector("input[name='password'], input[name='pass']")

        if page.locator("input[name='email']").first.is_visible():
            page.fill("input[name='email']", USERNAME)
            page.fill("input[name='pass']", PW)
            page.click("div[role='button']")  # 이메일 로그인 버튼
        else:
            page.fill("input[name='username']", USERNAME)
            page.fill("input[name='password']", PW)
            page.click("button[type='submit']")

        # 로그인 세션 저장
        context.storage_state(path=STATE_PATH)
        print(f"✅ 저장 완료: {STATE_PATH}")

        browser.close()

if __name__ == "__main__":
    main()
