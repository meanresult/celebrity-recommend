"""
Playwright 기본 구조 템플릿 (Python, sync)
- 목적: 동적 웹 크롤링/테스트 자동화의 80%를 커버하는 실전 뼈대 코드
- 사용법:
    1) pip install playwright
    2) playwright install
    3) python main.py  # 아래 파일명을 main.py로 저장했다고 가정
- 주의: 각 사이트의 robots.txt, 서비스 약관(ToS), 관련 법령을 준수하십시오.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
    Page,
    Browser,
    BrowserContext,
)

# =============================
# 0) 환경 기본 설정
# =============================
@dataclass
class Settings:
    base_url: str = "https://www.instagram.com/amomento.co/tagged/"
    headless: bool = False          # 서버에선 True 권장
    slow_mo_ms: int = 50            # 디버깅용(동작을 천천히)
    viewport: Dict[str, int] = None # 기본 viewport
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    )
    locale: str = "ko-KR"
    timezone_id: str = "Asia/Seoul"
    storage_path: str = "state/storage_state.json"  # 로그인 세션 저장 위치

    def __post_init__(self):
        if self.viewport is None:
            self.viewport = {"width": 1366, "height": 900}

SET = Settings()

# 유틸: 파일 저장 디렉토리 보장
def ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)

# =============================
# 1) 브라우저/컨텍스트/페이지 생성
# =============================

def launch_browser(p) -> Browser:
    return p.chromium.launch(headless=SET.headless, slow_mo=SET.slow_mo_ms)


def new_context(browser: Browser, use_saved_state: bool = True) -> BrowserContext:
    args: Dict[str, Any] = dict(
        viewport=SET.viewport,
        user_agent=SET.user_agent,
        locale=SET.locale,
        timezone_id=SET.timezone_id,
    )
    if use_saved_state and Path(SET.storage_path).exists():
        args["storage_state"] = SET.storage_path
    ctx = browser.new_context(**args)
    return ctx


def new_page(ctx: BrowserContext) -> Page:
    page = ctx.new_page()
    # 네트워크 유휴 상태까지 기다리도록 기본 설정 패턴
    page.set_default_timeout(10_000)         # 10초
    page.set_default_navigation_timeout(20_000)
    return page

# =============================
# 2) 공통 동작 유틸
# =============================

def goto(page: Page, url: str) -> None:
    page.goto(url, wait_until="domcontentloaded")
    # 초기 렌더링 후, 추가 리소스 로딩까지 대기
    page.wait_for_load_state("networkidle")


def text_all(page: Page, locator_str: str) -> List[str]:
    """Locator의 모든 텍스트를 깔끔히 추출"""
    loc = page.locator(locator_str)
    return [t.strip() for t in loc.all_text_contents() if t and t.strip()]


def attrs(page: Page, locator_str: str, attr: str) -> List[str]:
    loc = page.locator(locator_str)
    values: List[str] = []
    for el in loc.element_handles():
        v = el.get_attribute(attr)
        if v:
            values.append(v)
    return values


def scroll_to_bottom(page: Page, max_steps: int = 30, wait_ms: int = 600) -> None:
    """무한 스크롤 페이지에서 바닥까지 스크롤"""
    prev_height = 0
    for _ in range(max_steps):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(wait_ms)
        height = page.evaluate("document.body.scrollHeight")
        if height == prev_height:
            break
        prev_height = height


def wait_json_by_pred(page: Page, pred: Callable[[str], bool], timeout: int = 15_000) -> Optional[dict]:
    """특정 패턴의 JSON 응답 대기 및 반환"""
    try:
        resp = page.wait_for_response(lambda r: pred(r.url) and r.ok, timeout=timeout)
        return resp.json()
    except Exception:
        return None


def save_jsonl(path: str | Path, rows: Iterable[dict]) -> None:
    ensure_parent(path)
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# =============================
# 3) 로그인 세션 저장/재사용 (선택)
# =============================

def persist_login_state(ctx: BrowserContext) -> None:
    """현재 컨텍스트의 스토리지를 저장하여 다음 실행 때 재사용"""
    ensure_parent(SET.storage_path)
    ctx.storage_state(path=SET.storage_path)


# =============================
# 4) 크롤링 파이프라인(샘플)
# =============================

def extract_sample(page: Page) -> List[dict]:
    """예시: h3 타이틀 텍스트와 링크 수집"""
    items: List[dict] = []
    # 권장: CSS/Role/Text selector보다 우선 'locator' API 사용
    cards = page.locator("h3")
    count = cards.count()
    for i in range(count):
        node = cards.nth(i)
        title = node.inner_text().strip()
        # 링크 부모 탐색 예시 (사이트 구조에 맞게 수정)
        href = node.evaluate("el => el.closest('a')?.href || ''")
        if title:
            items.append({"title": title, "url": href})
    return items


def run() -> None:
    with sync_playwright() as p:
        browser = launch_browser(p)
        ctx = new_context(browser)
        page = new_page(ctx)

        try:
            goto(page, SET.base_url)

            # 무한 스크롤이 필요한 페이지라면 켜기
            # scroll_to_bottom(page, max_steps=20)

            data = extract_sample(page)
            print(f"[INFO] collected: {len(data)} items")
            save_jsonl("data/result.jsonl", data)

            # (선택) 로그인 후 세션 저장
            # persist_login_state(ctx)

        except PlaywrightTimeoutError as e:
            print("[TIMEOUT]", e)
            ensure_parent("logs/error.png")
            page.screenshot(path="logs/error.png", full_page=True)
        except Exception as e:
            print("[ERROR]", e)
            ensure_parent("logs/error.png")
            page.screenshot(path="logs/error.png", full_page=True)
            raise
        finally:
            ctx.close()
            browser.close()


if __name__ == "__main__":
    # 실행 전 원하는 기본 URL 지정
    # 예: SET.base_url = "https://news.ycombinator.com/"
    run()
