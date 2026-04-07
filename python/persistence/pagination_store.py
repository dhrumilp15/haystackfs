"""SQLite-backed persistence for paginated `/search` views.

Survives bot restarts so users can keep clicking Next/Back on a search result
message they posted earlier. State is keyed by a `row_id` (uuid4 hex) which is
baked into the persistent component custom_ids.
"""
import asyncio
import os
import time
import uuid
from typing import Optional

import aiosqlite


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pagination_rows (
    row_id        TEXT    PRIMARY KEY,
    message_id    INTEGER,
    channel_id    INTEGER NOT NULL,
    guild_id      INTEGER,
    user_id       INTEGER NOT NULL,
    query_json    TEXT    NOT NULL,
    pages_json    TEXT    NOT NULL,
    current_page  INTEGER NOT NULL DEFAULT 1,
    last_page     INTEGER NOT NULL DEFAULT -1,
    created_at    INTEGER NOT NULL,
    updated_at    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pagination_updated ON pagination_rows(updated_at);
"""


class PaginationStore:
    def __init__(self, path: str):
        self.path = path
        self._db: Optional[aiosqlite.Connection] = None
        self._locks: dict[str, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    async def init(self) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._db = await aiosqlite.connect(self.path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL;")
        await self._db.execute("PRAGMA synchronous=NORMAL;")
        await self._db.executescript(SCHEMA_SQL)
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def lock_for(self, row_id: str) -> asyncio.Lock:
        async with self._registry_lock:
            lock = self._locks.get(row_id)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[row_id] = lock
            return lock

    async def create(
        self,
        *,
        user_id: int,
        channel_id: int,
        guild_id: Optional[int],
        query_json: str,
        pages_json: str,
    ) -> str:
        row_id = uuid.uuid4().hex
        now = int(time.time())
        await self._db.execute(
            "INSERT INTO pagination_rows "
            "(row_id, channel_id, guild_id, user_id, query_json, pages_json, "
            "current_page, last_page, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 1, -1, ?, ?)",
            (row_id, channel_id, guild_id, user_id, query_json, pages_json, now, now),
        )
        await self._db.commit()
        return row_id

    async def attach_message(self, row_id: str, message_id: int) -> None:
        await self._db.execute(
            "UPDATE pagination_rows SET message_id=?, updated_at=? WHERE row_id=?",
            (message_id, int(time.time()), row_id),
        )
        await self._db.commit()

    async def load(self, row_id: str) -> Optional[dict]:
        async with self._db.execute(
            "SELECT row_id, message_id, channel_id, guild_id, user_id, "
            "query_json, pages_json, current_page, last_page "
            "FROM pagination_rows WHERE row_id=?",
            (row_id,),
        ) as cur:
            row = await cur.fetchone()
        return dict(row) if row is not None else None

    async def update(
        self,
        row_id: str,
        *,
        pages_json: str,
        current_page: int,
        last_page: int,
        query_json: str,
    ) -> None:
        await self._db.execute(
            "UPDATE pagination_rows SET pages_json=?, current_page=?, last_page=?, "
            "query_json=?, updated_at=? WHERE row_id=?",
            (pages_json, current_page, last_page, query_json, int(time.time()), row_id),
        )
        await self._db.commit()

    async def delete(self, row_id: str) -> None:
        await self._db.execute(
            "DELETE FROM pagination_rows WHERE row_id=?", (row_id,)
        )
        await self._db.commit()
        async with self._registry_lock:
            self._locks.pop(row_id, None)

    async def iter_active(self, ttl_seconds: int) -> list[dict]:
        """Return all rows with a message_id and updated_at within the TTL window."""
        cutoff = int(time.time()) - ttl_seconds
        async with self._db.execute(
            "SELECT row_id, message_id, channel_id, guild_id, user_id, "
            "query_json, pages_json, current_page, last_page "
            "FROM pagination_rows "
            "WHERE message_id IS NOT NULL AND updated_at >= ?",
            (cutoff,),
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def vacuum_old(self, ttl_seconds: int) -> int:
        cutoff = int(time.time()) - ttl_seconds
        cur = await self._db.execute(
            "DELETE FROM pagination_rows WHERE updated_at < ?", (cutoff,)
        )
        await self._db.commit()
        async with self._registry_lock:
            self._locks.clear()
        return cur.rowcount
