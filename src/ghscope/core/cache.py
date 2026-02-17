"""SQLite cache with TTL."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any


CACHE_DIR = Path.home() / ".ghscope"
CACHE_DB = CACHE_DIR / "cache.db"
DEFAULT_TTL = 3600  # 1 hour


def _get_conn() -> sqlite3.Connection:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CACHE_DB))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS cache (
            repo TEXT NOT NULL,
            query_key TEXT NOT NULL,
            data TEXT NOT NULL,
            fetched_at REAL NOT NULL,
            PRIMARY KEY (repo, query_key)
        )"""
    )
    conn.commit()
    return conn


def get(repo: str, key: str, ttl: int = DEFAULT_TTL) -> Any | None:
    """Get cached data if fresh enough."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT data, fetched_at FROM cache WHERE repo = ? AND query_key = ?",
            (repo, key),
        ).fetchone()
        if row is None:
            return None
        data, fetched_at = row
        if time.time() - fetched_at > ttl:
            return None
        return json.loads(data)
    finally:
        conn.close()


def get_offline(repo: str, key: str) -> Any | None:
    """Get cached data regardless of TTL (for --offline mode)."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT data FROM cache WHERE repo = ? AND query_key = ?",
            (repo, key),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])
    finally:
        conn.close()


def put(repo: str, key: str, data: Any) -> None:
    """Store data in cache."""
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO cache (repo, query_key, data, fetched_at)
               VALUES (?, ?, ?, ?)""",
            (repo, key, json.dumps(data, default=str), time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def clear(repo: str | None = None) -> None:
    """Clear cache for a repo or all repos."""
    conn = _get_conn()
    try:
        if repo:
            conn.execute("DELETE FROM cache WHERE repo = ?", (repo,))
        else:
            conn.execute("DELETE FROM cache")
        conn.commit()
    finally:
        conn.close()
