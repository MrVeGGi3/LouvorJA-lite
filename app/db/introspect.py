import sqlite3
from functools import lru_cache

from app.config import DB_PATH


@lru_cache(maxsize=4)
def _tables_for_mtime(mtime: float) -> frozenset[str]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return frozenset(r[0] for r in rows)
    finally:
        conn.close()


def available_tables() -> frozenset[str]:
    return _tables_for_mtime(DB_PATH.stat().st_mtime)


def has_table(name: str) -> bool:
    return name in available_tables()
