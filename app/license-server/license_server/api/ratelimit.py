"""activate 固定窗口限流：每 IP 10 次/分钟（可在设置中调整），内存实现。"""
from __future__ import annotations

import threading
import time


class FixedWindowRateLimiter:
    def __init__(self, limit: int = 10, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            window_start, count = self._buckets.get(key, (now, 0))
            if now - window_start >= self.window_seconds:
                self._buckets[key] = (now, 1)
                return True
            if count >= self.limit:
                return False
            self._buckets[key] = (window_start, count + 1)
            return True

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
