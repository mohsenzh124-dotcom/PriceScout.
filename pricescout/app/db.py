"""SQLite database access helpers for PriceScout."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from pricescout.app.models import Offer


class DatabaseClient:
    """Small SQLite wrapper for offer persistence and retrieval."""

    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None

    def _get_connection(self) -> sqlite3.Connection:
        """Return an open SQLite connection, creating it lazily."""
        if self._connection is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self._db_path)
        return self._connection

    def close(self) -> None:
        """Close the active SQLite connection if it exists."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def init_db(self) -> None:
        """Create database schema if it does not exist and enforce dedup constraints."""
        connection = self._get_connection()
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_query TEXT NOT NULL,
                store_name TEXT NOT NULL,
                product_name TEXT NOT NULL,
                product_url TEXT NOT NULL,
                currency TEXT NOT NULL,
                price_amount REAL NOT NULL,
                collected_at TEXT NOT NULL
            )
            """
        )

        # Keep one canonical row per product URL before creating the unique index.
        connection.execute(
            """
            DELETE FROM offers
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM offers
                GROUP BY product_url
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_offers_product_url_unique
            ON offers(product_url)
            """
        )
        connection.commit()

    def insert_offers(self, offers: Iterable[Offer]) -> None:
        """Insert or update offers with URL-based deduplication via upsert."""
        records = [
            (
                offer.product_query,
                offer.store_name,
                offer.product_name,
                offer.product_url,
                offer.currency,
                offer.price_amount,
                offer.collected_at,
            )
            for offer in offers
            if offer.product_url.strip()
        ]
        if not records:
            return

        connection = self._get_connection()
        connection.executemany(
            """
            INSERT INTO offers (
                product_query,
                store_name,
                product_name,
                product_url,
                currency,
                price_amount,
                collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_url) DO UPDATE SET
                product_query = excluded.product_query,
                store_name = excluded.store_name,
                product_name = excluded.product_name,
                currency = excluded.currency,
                price_amount = excluded.price_amount,
                collected_at = excluded.collected_at
            """,
            records,
        )
        connection.commit()

    def get_latest_offers(self, product_query: str) -> list[Offer]:
        """Return latest offers by collection timestamp for a product query."""
        connection = self._get_connection()
        rows = connection.execute(
            """
            SELECT
                product_query,
                store_name,
                product_name,
                product_url,
                currency,
                price_amount,
                collected_at
            FROM offers
            WHERE product_query = ?
            ORDER BY collected_at DESC, price_amount ASC
            LIMIT 100
            """,
            (product_query,),
        ).fetchall()

        return [
            Offer(
                product_query=row[0],
                store_name=row[1],
                product_name=row[2],
                product_url=row[3],
                currency=row[4],
                price_amount=float(row[5]),
                collected_at=row[6],
            )
            for row in rows
        ]
