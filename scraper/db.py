"""
SQLite 数据库读写工具。

只有一张表 news，url 作为唯一键去重（同一条新闻重复抓到会更新而不是重复插入）。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "policy.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS news (
    url TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    published TEXT,
    first_seen TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def upsert_items(conn: sqlite3.Connection, items: List[Dict]) -> None:
    """插入新条目；如果url已存在则更新标题/日期（不重复插入，也不丢失first_seen）"""
    for item in items:
        conn.execute(
            """
            INSERT INTO news (url, source, title, published)
            VALUES (:url, :source, :title, :published)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                published = excluded.published,
                source = excluded.source
            """,
            item,
        )
    conn.commit()


def fetch_all(conn: sqlite3.Connection, source: Optional[str] = None,
              search: Optional[str] = None) -> List[Dict]:
    """查询新闻，可选按来源筛选、按标题关键词搜索，按日期倒序返回"""
    query = "SELECT url, source, title, published FROM news WHERE 1=1"
    params: Dict = {}

    if source:
        query += " AND source = :source"
        params["source"] = source

    if search:
        query += " AND title LIKE :search"
        params["search"] = f"%{search}%"

    query += " ORDER BY (published IS NULL), published DESC"

    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def count_by_source(conn: sqlite3.Connection) -> Dict[str, int]:
    rows = conn.execute("SELECT source, COUNT(*) AS cnt FROM news GROUP BY source").fetchall()
    return {row["source"]: row["cnt"] for row in rows}
