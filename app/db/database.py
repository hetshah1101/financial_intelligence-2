# app/db/database.py - Database connection and schema management

import sqlite3
import logging
from contextlib import contextmanager
from typing import Generator

from app.config import config

logger = logging.getLogger(__name__)


def get_db_path() -> str:
    return config.database.path


def init_db() -> None:
    """Initialize database with all required tables."""
    db_path = get_db_path()
    logger.info(f"Initializing database at {db_path}")

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                amount      REAL NOT NULL CHECK(amount >= 0),
                type        TEXT NOT NULL CHECK(type IN ('income','expense','investment')),
                category    TEXT NOT NULL,
                subcategory TEXT,
                description TEXT,
                account     TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_dedup
                ON transactions(date, amount, type, category, description, account);

            CREATE INDEX IF NOT EXISTS idx_transactions_date
                ON transactions(date);

            CREATE INDEX IF NOT EXISTS idx_transactions_type
                ON transactions(type);

            CREATE TABLE IF NOT EXISTS monthly_aggregates (
                month            TEXT NOT NULL,
                total_income     REAL DEFAULT 0,
                total_expense    REAL DEFAULT 0,
                total_investment REAL DEFAULT 0,
                net_savings      REAL DEFAULT 0,
                savings_rate     REAL DEFAULT 0,
                updated_at       TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (month)
            );

            CREATE TABLE IF NOT EXISTS category_aggregates (
                month               TEXT NOT NULL,
                category            TEXT NOT NULL,
                total_amount        REAL DEFAULT 0,
                percentage_of_total REAL DEFAULT 0,
                updated_at          TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (month, category)
            );

            CREATE TABLE IF NOT EXISTS insights_cache (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                month        TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                content      TEXT,
                created_at   TEXT DEFAULT (datetime('now'))
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_insights_month_type
                ON insights_cache(month, insight_type);
        """)
        conn.commit()

    logger.info("Database initialized successfully")


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections with row factory."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
