"""Unit tests for interval calculation logic."""

import pytest
from datetime import datetime, timedelta, timezone

from nixpkgs_index.github import calculate_target_times, create_query_window, TimeWindow


class TestCalculateTargetTimes:
    def test_basic_intervals(self):
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        step_interval = timedelta(days=7)
        max_steps = 3

        target_times = calculate_target_times(start_time, step_interval, max_steps)

        assert len(target_times) == 3
        assert target_times[0] == datetime(2024, 12, 25, 12, 0, 0, tzinfo=timezone.utc)  # 21 days ago
        assert target_times[1] == datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)    # 14 days ago
        assert target_times[2] == datetime(2025, 1, 8, 12, 0, 0, tzinfo=timezone.utc)    # 7 days ago

    def test_intervals_are_evenly_spaced(self):
        start_time = datetime(2025, 10, 24, 12, 0, 0, tzinfo=timezone.utc)
        step_interval = timedelta(days=14)
        max_steps = 5

        target_times = calculate_target_times(start_time, step_interval, max_steps)

        expected_times = [
            datetime(2025, 8, 15, 12, 0, 0, tzinfo=timezone.utc),  # 70 days ago (5 * 14)
            datetime(2025, 8, 29, 12, 0, 0, tzinfo=timezone.utc),  # 56 days ago (4 * 14)
            datetime(2025, 9, 12, 12, 0, 0, tzinfo=timezone.utc),  # 42 days ago (3 * 14)
            datetime(2025, 9, 26, 12, 0, 0, tzinfo=timezone.utc),  # 28 days ago (2 * 14)
            datetime(2025, 10, 10, 12, 0, 0, tzinfo=timezone.utc), # 14 days ago (1 * 14)
        ]

        assert target_times == expected_times

        for i in range(len(target_times) - 1):
            diff = target_times[i + 1] - target_times[i]
            assert diff == step_interval, f"Interval {i} is not {step_interval}: got {diff}"

    def test_with_since_limit(self):
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        step_interval = timedelta(days=7)
        max_steps = 10
        since = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        target_times = calculate_target_times(start_time, step_interval, max_steps, since)

        assert len(target_times) == 2
        assert all(t >= since for t in target_times)

    def test_hourly_intervals(self):
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        step_interval = timedelta(hours=6)
        max_steps = 4

        target_times = calculate_target_times(start_time, step_interval, max_steps)

        assert len(target_times) == 4
        assert target_times[0] == datetime(2025, 1, 14, 12, 0, 0, tzinfo=timezone.utc)  # 24 hours ago
        assert target_times[1] == datetime(2025, 1, 14, 18, 0, 0, tzinfo=timezone.utc)  # 18 hours ago
        assert target_times[2] == datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc)   # 12 hours ago
        assert target_times[3] == datetime(2025, 1, 15, 6, 0, 0, tzinfo=timezone.utc)   # 6 hours ago

    def test_returns_empty_when_since_is_after_first_step(self):
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        step_interval = timedelta(days=7)
        max_steps = 5
        since = datetime(2025, 1, 10, 0, 0, 0, tzinfo=timezone.utc)

        target_times = calculate_target_times(start_time, step_interval, max_steps, since)

        assert len(target_times) == 0

    def test_chronological_order(self):
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        step_interval = timedelta(days=3)
        max_steps = 5

        target_times = calculate_target_times(start_time, step_interval, max_steps)

        for i in range(len(target_times) - 1):
            assert target_times[i] < target_times[i + 1], "Times should be in ascending order"

    def test_large_max_steps_with_since(self):
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        step_interval = timedelta(days=1)
        max_steps = 1000
        since = datetime(2025, 1, 10, 0, 0, 0, tzinfo=timezone.utc)

        target_times = calculate_target_times(start_time, step_interval, max_steps, since)

        assert len(target_times) == 5
        assert target_times[0] >= since
        assert target_times[-1] < start_time


class TestCreateQueryWindow:
    def test_default_window_size(self):
        target_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        window = create_query_window(target_time)

        assert window.start == datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
        assert window.end == datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

    def test_custom_window_size(self):
        target_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        window_size = timedelta(hours=3)

        window = create_query_window(target_time, window_size)

        assert window.start == datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        assert window.end == datetime(2025, 1, 15, 15, 0, 0, tzinfo=timezone.utc)

    def test_window_is_centered(self):
        target_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        window_size = timedelta(minutes=30)

        window = create_query_window(target_time, window_size)

        before = target_time - window.start
        after = window.end - target_time

        assert before == after == window_size

    def test_window_with_minute_precision(self):
        target_time = datetime(2025, 1, 15, 12, 34, 56, tzinfo=timezone.utc)
        window_size = timedelta(minutes=15)

        window = create_query_window(target_time, window_size)

        assert window.start == datetime(2025, 1, 15, 12, 19, 56, tzinfo=timezone.utc)
        assert window.end == datetime(2025, 1, 15, 12, 49, 56, tzinfo=timezone.utc)

    def test_returns_time_window_dataclass(self):
        target_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        window = create_query_window(target_time)

        assert isinstance(window, TimeWindow)
        assert hasattr(window, 'start')
        assert hasattr(window, 'end')


class TestIntervalLogicIntegration:
    def test_fourteen_day_intervals_fifty_steps(self):
        start_time = datetime(2025, 10, 24, 23, 52, 36, tzinfo=timezone.utc)
        step_interval = timedelta(days=14)
        max_steps = 50

        target_times = calculate_target_times(start_time, step_interval, max_steps)

        assert len(target_times) == 50

        for i in range(len(target_times) - 1):
            diff = target_times[i + 1] - target_times[i]
            assert diff == timedelta(days=14), f"Step {i}: expected 14 days, got {diff}"

        expected_oldest = start_time - (step_interval * 50)
        assert target_times[0] == expected_oldest

        expected_newest = start_time - step_interval
        assert target_times[-1] == expected_newest

    def test_windows_dont_overlap_for_small_intervals(self):
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        step_interval = timedelta(days=7)
        max_steps = 5

        target_times = calculate_target_times(start_time, step_interval, max_steps)
        windows = [create_query_window(t) for t in target_times]

        for i in range(len(windows) - 1):
            assert windows[i].end <= windows[i + 1].start, f"Windows {i} and {i+1} overlap"

    def test_windows_may_overlap_for_small_intervals(self):
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        step_interval = timedelta(minutes=30)
        max_steps = 3

        target_times = calculate_target_times(start_time, step_interval, max_steps)
        windows = [create_query_window(t) for t in target_times]

        overlaps = any(windows[i].end > windows[i + 1].start for i in range(len(windows) - 1))
        assert overlaps, "Windows should overlap when interval < window size"
