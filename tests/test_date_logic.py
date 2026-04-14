"""
날짜 계산 순수 함수 테스트

브라우저/Playwright 없이 실행 가능 — CI에서 항상 통과 가능한 테스트.
"""
import pytest
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from extractors.main_mini_v4 import calculate_days_diff, KST


class TestCalculateDaysDiff:
    """calculate_days_diff 핵심 로직 검증"""

    def test_utc_to_kst_conversion(self):
        """UTC 00:00 은 KST 09:00 으로 변환되어야 한다"""
        result_kst, _, _ = calculate_days_diff("2024-01-15T00:00:00Z")
        assert result_kst.hour == 9
        assert result_kst.tzinfo == KST

    def test_days_diff_yesterday(self):
        """어제 게시물은 days_diff == 1 이어야 한다"""
        now_kst = datetime(2024, 6, 15, 12, 0, 0, tzinfo=KST)
        yesterday_str = "2024-06-14T03:00:00Z"  # KST 2024-06-14 12:00

        _, _, days_diff = calculate_days_diff(yesterday_str, now_kst=now_kst)
        assert days_diff == 1

    def test_days_diff_today(self):
        """오늘 게시물은 days_diff == 0 이어야 한다"""
        now_kst = datetime(2024, 6, 15, 12, 0, 0, tzinfo=KST)
        today_str = "2024-06-15T03:00:00Z"  # KST 2024-06-15 12:00

        _, _, days_diff = calculate_days_diff(today_str, now_kst=now_kst)
        assert days_diff == 0

    def test_days_diff_old_post(self):
        """3일 전 게시물은 days_diff == 3 이어야 한다"""
        now_kst = datetime(2024, 6, 15, 12, 0, 0, tzinfo=KST)
        old_str = "2024-06-12T03:00:00Z"

        _, _, days_diff = calculate_days_diff(old_str, now_kst=now_kst)
        assert days_diff == 3

    def test_returns_correct_post_date(self):
        """반환된 post_date 가 KST 기준 날짜인지 확인"""
        now_kst = datetime(2024, 6, 15, 12, 0, 0, tzinfo=KST)
        dt_str = "2024-06-14T15:00:00Z"  # UTC 15:00 = KST 2024-06-15 00:00

        post_dt_kst, post_date, _ = calculate_days_diff(dt_str, now_kst=now_kst)
        assert post_date.year == 2024
        assert post_date.month == 6
        assert post_date.day == 15

    def test_invalid_format_raises_value_error(self):
        """잘못된 datetime 문자열은 ValueError 를 발생시켜야 한다"""
        with pytest.raises(ValueError):
            calculate_days_diff("not-a-date")

    def test_midnight_boundary_kst(self):
        """UTC 23:59 게시물이 KST 에서는 다음날인 경우"""
        now_kst = datetime(2024, 6, 15, 12, 0, 0, tzinfo=KST)
        # UTC 2024-06-14 23:59 = KST 2024-06-15 08:59 → 오늘
        dt_str = "2024-06-14T23:59:00Z"

        _, post_date, days_diff = calculate_days_diff(dt_str, now_kst=now_kst)
        assert post_date.day == 15
        assert days_diff == 0
