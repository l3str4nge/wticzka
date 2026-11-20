"""Baza SQLite z listą artykułów."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "wticzka.db"

STATUSES = {
    "to_read": "Do przeczytania",
    "read": "Przeczytane",
    "archived": "Archiwum",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id          INTEGER PRIMARY KEY,
    url         TEXT NOT NULL,
    page_title  TEXT NOT NULL DEFAULT '',
    text        TEXT NOT NULL DEFAULT '',
    title       TEXT,
    lead        TEXT,
    body_html   TEXT,
    state       TEXT NOT NULL DEFAULT 'pending',  -- pending | done | error
    error       TEXT,
    status      TEXT NOT NULL DEFAULT 'to_read',  -- to_read | read | archived
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    read_at     TEXT
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init():
    with connect() as c:
        c.executescript(SCHEMA)


def add(url, page_title, text):
    with connect() as c:
        cur = c.execute(
            "INSERT INTO articles (url, page_title, text) VALUES (?, ?, ?)",
            (url, page_title, text),
        )
        return cur.lastrowid


def url_exists(url):
    with connect() as c:
        return c.execute("SELECT 1 FROM articles WHERE url = ? LIMIT 1", (url,)).fetchone() is not None


def get(article_id):
    with connect() as c:
        return c.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()


def list_by_status(status):
    with connect() as c:
        return c.execute(
            "SELECT * FROM articles WHERE status = ? ORDER BY id DESC", (status,)
        ).fetchall()


def counts():
    with connect() as c:
        rows = c.execute("SELECT status, COUNT(*) AS n FROM articles GROUP BY status")
        found = {r["status"]: r["n"] for r in rows}
    return {s: found.get(s, 0) for s in STATUSES}


def pending_ids():
    with connect() as c:
        return [r["id"] for r in c.execute("SELECT id FROM articles WHERE state = 'pending'")]


def set_pending(article_id):
    with connect() as c:
        c.execute("UPDATE articles SET state = 'pending', error = NULL WHERE id = ?", (article_id,))


def set_page(article_id, page_title, text):
    with connect() as c:
        c.execute(
            "UPDATE articles SET page_title = ?, text = ? WHERE id = ?", (page_title, text, article_id)
        )


def set_result(article_id, title, lead, body_html):
    with connect() as c:
        c.execute(
            "UPDATE articles SET state = 'done', error = NULL, title = ?, lead = ?, body_html = ?"
            " WHERE id = ?",
            (title, lead, body_html, article_id),
        )


def set_error(article_id, error):
    with connect() as c:
        c.execute("UPDATE articles SET state = 'error', error = ? WHERE id = ?", (error, article_id))


def set_status(article_id, status):
    with connect() as c:
        c.execute(
            "UPDATE articles SET status = ?,"
            " read_at = CASE WHEN ? = 'read' THEN datetime('now', 'localtime') ELSE read_at END"
            " WHERE id = ?",
            (status, status, article_id),
        )


def delete(article_id):
    with connect() as c:
        c.execute("DELETE FROM articles WHERE id = ?", (article_id,))
