from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import time
from typing import Any


@dataclass
class CacheEntry:
    expires_at: float
    payload: Any
    etag: str


class ResponseCache:
    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}
        self._lock = RLock()

    def get(self, key: str) -> CacheEntry | None:
        now = time()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._store.pop(key, None)
                return None
            return entry

    def set(self, key: str, payload: Any, ttl_seconds: int, etag: str) -> None:
        with self._lock:
            self._store[key] = CacheEntry(
                expires_at=time() + ttl_seconds,
                payload=payload,
                etag=etag,
            )

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
