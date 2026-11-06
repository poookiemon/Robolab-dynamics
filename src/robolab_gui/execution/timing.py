"""Live execution timer, speed factor multiplier, and pause compensation."""

import time
from typing import Optional, List


class ExecutionTimer:
    """Calculates active elapsed time, speed factor, and remaining countdown duration."""

    def __init__(self, step_baselines: List[float]):
        self.step_baselines = step_baselines
        self.total_baseline = sum(step_baselines)
        self.start_time: Optional[float] = None
        self.total_paused_seconds: float = 0.0
        self._pause_start: Optional[float] = None
        self.live_speed_factor: float = 1.0

    def start(self) -> None:
        self.start_time = time.time()
        self.total_paused_seconds = 0.0
        self._pause_start = None
        self.live_speed_factor = 1.0

    def pause(self) -> None:
        if self._pause_start is None:
            self._pause_start = time.time()

    def resume(self) -> None:
        if self._pause_start is not None:
            self.total_paused_seconds += (time.time() - self._pause_start)
            self._pause_start = None

    def get_active_elapsed(self, current_time: Optional[float] = None) -> float:
        if self.start_time is None:
            return 0.0
        now = current_time or time.time()
        in_pause = (now - self._pause_start) if self._pause_start else 0.0
        return max(0.0, now - self.start_time - self.total_paused_seconds - in_pause)

    def update_speed_factor(self, completed_step_index: int) -> float:
        if completed_step_index <= 0 or not self.step_baselines:
            return 1.0
        completed_baseline = sum(self.step_baselines[:completed_step_index])
        if completed_baseline <= 0:
            return 1.0
        active_elapsed = self.get_active_elapsed()
        raw_factor = active_elapsed / completed_baseline
        self.live_speed_factor = max(0.25, min(4.0, raw_factor))
        return self.live_speed_factor

    def get_remaining_seconds(self, current_step_index: int) -> float:
        if current_step_index >= len(self.step_baselines):
            return 0.0
        remaining_baseline = sum(self.step_baselines[current_step_index:])
        return round(remaining_baseline * self.live_speed_factor, 1)
