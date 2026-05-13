"""
v5 relational DB connection helpers.

Safe by design:
- reuses the existing SQLite file from db.py
- does not replace current db.py behavior
- only provides a cleaner connection entry point for new v5 code
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from db import DB_PATH


from db import get_db

def get_connection() -> sqlite3.Connection:
    """Return the shared thread-local connection from db.py."""
    return get_db()

@contextmanager
def connection_scope():
    """
    Provides a connection scope that shares the db.py connection.
    It commits and rolls back ONLY if it's not inside a db_transaction.
    """
    conn = get_connection()
    # Check if managed by db.py db_transaction
    from db import _local
    is_managed = getattr(_local, "in_transaction", False)

    try:
        yield conn
        if not is_managed:
            conn.commit()
    except Exception:
        if not is_managed:
            conn.rollback()
        raise
