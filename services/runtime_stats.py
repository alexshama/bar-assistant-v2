"""
In-memory runtime counters for basic operational statistics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class RuntimeStats:
    started_at: datetime
    total_requests: int = 0
    text_requests: int = 0
    voice_requests: int = 0
    image_requests: int = 0
    failed_requests: int = 0

    def mark_text(self) -> None:
        self.total_requests += 1
        self.text_requests += 1

    def mark_voice(self) -> None:
        self.total_requests += 1
        self.voice_requests += 1

    def mark_image(self) -> None:
        self.total_requests += 1
        self.image_requests += 1

    def mark_failed(self) -> None:
        self.failed_requests += 1

    def uptime_seconds(self) -> int:
        now = datetime.now(timezone.utc)
        return max(0, int((now - self.started_at).total_seconds()))


runtime_stats = RuntimeStats(started_at=datetime.now(timezone.utc))
