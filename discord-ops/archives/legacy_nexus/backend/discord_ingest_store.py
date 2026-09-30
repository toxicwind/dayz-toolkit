from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ChannelStatus:
    channel_id: int
    tag: str = ""
    exists: bool = False
    can_read: bool = False
    can_history: bool = False
    can_send: bool = False
    last_event_ts: str | None = None
    last_error: str | None = None
    backfill_cursor: str | None = None
    validated_at: str | None = None


@dataclass
class ChannelEvent:
    seq: int
    message_id: int
    channel_id: int
    channel_tag: str
    author: str
    author_id: int
    content: str
    created_at: str


class DiscordIngestStore:
    """
    Thread-safe, in-memory buffer for Discord channel events + diagnostics.
    Designed for cross-thread use (bot thread writes, API thread reads).
    """

    def __init__(self, max_events: int = 2000):
        self._lock = threading.Lock()
        self._seq = 0
        self._events: deque[ChannelEvent] = deque(maxlen=max_events)
        self._statuses: dict[int, ChannelStatus] = {}

    # --------------------------- Status ---------------------------
    def upsert_status(self, status: ChannelStatus) -> None:
        with self._lock:
            self._statuses[status.channel_id] = status

    def update_status(self, channel_id: int, **kwargs: Any) -> None:
        with self._lock:
            st = self._statuses.get(channel_id)
            if not st:
                st = ChannelStatus(channel_id=channel_id)
                self._statuses[channel_id] = st
            for k, v in kwargs.items():
                if hasattr(st, k):
                    setattr(st, k, v)

    def get_status_matrix(self) -> list[dict[str, Any]]:
        with self._lock:
            return [status.__dict__.copy() for status in self._statuses.values()]

    # --------------------------- Events ---------------------------
    def record_event(
        self,
        message_id: int,
        channel_id: int,
        channel_tag: str,
        author: str,
        author_id: int,
        content: str,
        created_at: datetime,
    ) -> ChannelEvent:
        with self._lock:
            self._seq += 1
            evt = ChannelEvent(
                seq=self._seq,
                message_id=message_id,
                channel_id=channel_id,
                channel_tag=channel_tag,
                author=author,
                author_id=author_id,
                content=content,
                created_at=created_at.isoformat(),
            )
            self._events.append(evt)
            st = self._statuses.get(channel_id)
            if st:
                st.last_event_ts = evt.created_at
                st.last_error = None
            return evt

    def get_events_since(self, since_seq: int = 0, channel_ids: list[int] | None = None) -> list[ChannelEvent]:
        with self._lock:
            filtered = [
                evt
                for evt in self._events
                if evt.seq > since_seq and (channel_ids is None or evt.channel_id in channel_ids)
            ]
            return list(filtered)


# Singleton store shared between bot + API
store = DiscordIngestStore()
