"""Database Query Tool — execute read-only SQL queries.

Uses SQLite locally for development.  The interface is designed so that
a production implementation can swap in RDS/Aurora via SQLAlchemy.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from langchain_core.tools import tool

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sample.db"


def _ensure_sample_db(db_path: Path) -> None:
    """Create a tiny sample database if it doesn't exist yet."""
    if db_path.exists():
        return
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS products "
        "(id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL)"
    )
    sample_rows = [
        (1, "Widget A", "electronics", 19.99),
        (2, "Widget B", "electronics", 29.99),
        (3, "Gadget X", "accessories", 9.99),
        (4, "Gadget Y", "accessories", 14.99),
        (5, "Gizmo Z", "tools", 49.99),
    ]
    cur.executemany("INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?)", sample_rows)
    conn.commit()
    conn.close()


@tool
def database_query(query: str, db_path: str = "") -> str:
    """Execute a read-only SQL query against the database.

    Only SELECT statements are allowed.  Returns rows as formatted text.
    The default database contains a 'products' table with columns:
    id, name, category, price.
    """
    normalized = query.strip().upper()
    if not normalized.startswith("SELECT"):
        return "Error: Only SELECT queries are permitted."

    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    _ensure_sample_db(path)

    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        conn.close()
    except sqlite3.Error as exc:
        return f"SQL Error: {exc}"

    if not rows:
        return "Query returned no results."

    columns = rows[0].keys()
    header = " | ".join(columns)
    separator = "-+-".join("-" * max(len(c), 8) for c in columns)
    body_lines = []
    for row in rows:
        body_lines.append(" | ".join(str(row[c]) for c in columns))

    return f"{header}\n{separator}\n" + "\n".join(body_lines)
