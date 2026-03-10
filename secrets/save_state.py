import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
USERNAME = os.getenv("ID")
PW = os.getenv("PW")

LOGIN_URL = "https://www.instagram.com/accounts/login/"
BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "storage_state.json"
FAILSHOT_PATH = BASE_DIR / "login_failed.png"

def main():
    if not USERNAME or not PW:
        raise RuntimeError(
            ".env에서 ID/PW를 읽지 못했습니다. 프로젝트 루트에 .env가 있는지 확인하세요."
        )

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

        # ✅ 로그인 완료 대기: URL이 login이 아니게 되거나, 홈/피드 요소가 뜰 때까지
        page.wait_for_timeout(15000)

        try:
            btn = page.get_by_role("button", name="정보 저장")
            if btn.first.is_visible(timeout=1000):
                btn.first.click(timeout=2000)
                page.wait_for_timeout(500)
        except:
            pass

        # ✅ 쿠키에 sessionid가 생겼는지 체크
        cookies = context.cookies()
        cookie_names = sorted([c["name"] for c in cookies])
        print("cookie_names:", cookie_names)
        print("current_url:", page.url)

        if "sessionid" not in cookie_names:
            # 진단용 스크린샷
            page.screenshot(path=str(FAILSHOT_PATH), full_page=True)
            raise RuntimeError(
                f"sessionid가 없어서 저장 중단. 실패 화면: {FAILSHOT_PATH}"
            )


        # 로그인 세션 저장
        context.storage_state(path=str(STATE_PATH))
        print(f"✅ 저장 완료: {STATE_PATH}")

        browser.close()

if __name__ == "__main__":
    main()
