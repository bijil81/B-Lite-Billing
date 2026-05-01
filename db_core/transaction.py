"""Small transaction helpers for v5 services."""

from __future__ import annotations

from contextlib import contextmanager

from db_core.connection import get_connection


@contextmanager
def transaction_scope():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass
