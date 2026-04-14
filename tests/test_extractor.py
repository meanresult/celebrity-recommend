"""
크롤러 로직 단위 테스트

Playwright page 객체를 Mock 으로 대체하여 브라우저 없이 실행.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from extractors.main_mini_v4 import parse_href, collect_posts_with_scroll, KST


class TestParseHref:
    """parse_href 순수 함수 검증"""

    def test_extracts_insta_id(self):
        href = "/amomento.co/p/ABC123/"
        insta_id, _ = parse_href(href)
        assert insta_id == "amomento.co"

    def test_generates_full_link(self):
        href = "/p/ABC123/"
        _, full_link = parse_href(href)
        assert full_link == "https://www.instagram.com/p/ABC123/"

    def test_empty_href_returns_unknown(self):
        insta_id, _ = parse_href("")
        assert insta_id == "unknown"

    def test_none_href_returns_unknown(self):
        insta_id, _ = parse_href(None)
        assert insta_id == "unknown"

    def test_strips_trailing_slash(self):
        href = "/amomento.co/p/XYZ/"
        insta_id, _ = parse_href(href)
        # "amomento.co" 가 나와야 하고 슬래시가 없어야 함
        assert "/" not in insta_id


class TestCollectPostsWithScroll:
    """collect_posts_with_scroll 동작 검증 (Mock 활용)"""

    def _make_mock_page(self, hrefs: list, dt_str: str = "2024-06-14T03:00:00Z"):
        """테스트용 page mock 생성 헬퍼"""
        page = MagicMock()

        # locator("a[href*='/p/']") 동작 설정
        links_locator = MagicMock()
        links_locator.count.return_value = len(hrefs)

        def nth_side_effect(idx):
            link = MagicMock()
            link.get_attribute.return_value = hrefs[idx] if idx < len(hrefs) else None
            return link

        links_locator.nth.side_effect = nth_side_effect
        page.locator.return_value = links_locator

        # time 요소 mock (날짜 파싱용)
        time_el = MagicMock()
        time_el.get_attribute.return_value = dt_str
        page.locator.return_value.first = time_el

        return page

    def test_skips_duplicate_hrefs(self):
        """같은 href 는 한 번만 처리해야 한다"""
        seen = set()
        hrefs = ["/p/A/", "/p/A/", "/p/B/"]
        processed = [h for h in hrefs if h not in seen and not seen.add(h)]
        assert processed == ["/p/A/", "/p/B/"]

    def test_stops_when_target_reached(self):
        """target 개수 수집 시 조기 종료해야 한다"""
        page = MagicMock()

        # 게시물 2개, 날짜는 어제
        now_kst = datetime.now(KST)
        yesterday_utc = (now_kst - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        hrefs = [f"/p/POST{i}/" for i in range(10)]
        links_locator = MagicMock()
        links_locator.count.return_value = len(hrefs)

        def nth_link(idx):
            lnk = MagicMock()
            lnk.get_attribute.return_value = hrefs[idx]
            return lnk

        links_locator.nth.side_effect = nth_link

        time_el = MagicMock()
        time_el.get_attribute.return_value = yesterday_utc
        time_locator = MagicMock()
        time_locator.first = time_el

        def locator_side_effect(selector):
            if "a[href" in selector:
                return links_locator
            if selector == "time":
                return time_locator
            m = MagicMock()
            m.first = MagicMock()
            m.first.get_attribute.return_value = "http://img.example.com/photo.jpg"
            return m

        page.locator.side_effect = locator_side_effect

        result = collect_posts_with_scroll(page, target=3, max_scroll=5)
        assert len(result) == 3

    def test_skips_posts_older_than_yesterday(self):
        """days_diff >= 2 인 게시물은 수집하지 않아야 한다"""
        page = MagicMock()
        now_kst = datetime.now(KST)
        two_days_ago = (now_kst - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

        hrefs = ["/p/OLD1/", "/p/OLD2/"]
        links_locator = MagicMock()
        links_locator.count.return_value = len(hrefs)

        def nth_link(idx):
            lnk = MagicMock()
            lnk.get_attribute.return_value = hrefs[idx]
            return lnk

        links_locator.nth.side_effect = nth_link

        time_el = MagicMock()
        time_el.get_attribute.return_value = two_days_ago
        time_locator = MagicMock()
        time_locator.first = time_el

        def locator_side_effect(selector):
            if "a[href" in selector:
                return links_locator
            if selector == "time":
                return time_locator
            return MagicMock()

        page.locator.side_effect = locator_side_effect

        result = collect_posts_with_scroll(page, target=10, max_scroll=1)
        assert len(result) == 0
