"""Diagnostic utility to validate live scraper coverage across product categories."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote_plus

# Ensure imports work even when the script is launched from outside repository root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pricescout.app.api.routes import handle_request
from pricescout.app.config import get_settings
from pricescout.app.db import DatabaseClient
from pricescout.app.scrapers.store_citilink import CitilinkScraper
from pricescout.app.scrapers.store_dns import DnsScraper
from pricescout.app.scrapers.store_ozon import OzonScraper
from pricescout.app.scrapers.store_wildberries import WildberriesScraper
from pricescout.app.scrapers.store_yandex_market import YandexMarketScraper
from pricescout.app.services.price_comparator import PriceComparator

QUERIES: tuple[str, ...] = (
    "laptop",
    "gaming mouse",
    "4k monitor",
    "graphics card",
    "bluetooth headphones",
)


STORE_NAMES: tuple[str, ...] = (
    "Ozon",
    "Wildberries",
    "Yandex Market",
    "DNS Shop",
    "Citilink",
)


def _build_comparator(db_path: str) -> tuple[PriceComparator, DatabaseClient]:
    """Create a comparator configured like runtime but bound to an isolated database."""
    settings = get_settings()
    db_client = DatabaseClient(db_path)
    db_client.init_db()

    comparator = PriceComparator(
        db_client=db_client,
        scrapers=[
            OzonScraper(timeout_seconds=settings.request_timeout, user_agent=settings.user_agent),
            WildberriesScraper(timeout_seconds=settings.request_timeout, user_agent=settings.user_agent),
            YandexMarketScraper(timeout_seconds=settings.request_timeout, user_agent=settings.user_agent),
            DnsScraper(timeout_seconds=settings.request_timeout, user_agent=settings.user_agent),
            CitilinkScraper(timeout_seconds=settings.request_timeout, user_agent=settings.user_agent),
        ],
    )
    return comparator, db_client


def _get_query_offers(comparator: PriceComparator, query: str) -> list[dict]:
    """Run compare logic via existing route handler and return offers."""
    status_code, _, payload = handle_request(
        method="GET",
        path="/api/compare",
        query_string=f"q={quote_plus(query)}",
        comparator=comparator,
    )

    if status_code.value != 200:
        raise RuntimeError(f"Compare route returned unexpected status {status_code.value}.")

    try:
        response_data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Failed to decode compare response payload.") from exc

    offers = response_data.get("offers")
    if not isinstance(offers, list):
        raise RuntimeError("Compare response does not contain a valid offers list.")

    return offers


def _count_by_store(offers: list[dict], store_name: str) -> int:
    """Count offers that match an exact store name."""
    return sum(1 for offer in offers if offer.get("store_name") == store_name)


def main() -> None:
    """Run scraper coverage diagnostics for all configured queries."""
    with TemporaryDirectory(prefix="pricescout_scraper_diag_") as temp_dir:
        temp_db_path = Path(temp_dir) / "diagnostic_pricescout.db"

        previous_db_path = os.environ.get("PRICESCOUT_DB_PATH")
        os.environ["PRICESCOUT_DB_PATH"] = str(temp_db_path)

        db_client: DatabaseClient | None = None
        try:
            comparator, db_client = _build_comparator(str(temp_db_path))

            for query in QUERIES:
                print(f"Query: {query}")
                try:
                    offers = _get_query_offers(comparator, query)
                    counts_by_store = {
                        store_name: _count_by_store(offers, store_name) for store_name in STORE_NAMES
                    }
                    total_count = len(offers)
                except Exception as exc:
                    print(f"Error: {exc}")
                    counts_by_store = {store_name: 0 for store_name in STORE_NAMES}
                    total_count = 0

                for store_name in STORE_NAMES:
                    print(f"{store_name} results: {counts_by_store[store_name]}")
                print(f"Total offers: {total_count}")
                print()
        finally:
            if db_client is not None:
                # Explicit close is required on Windows before temp directory cleanup.
                db_client.close()

            if previous_db_path is None:
                os.environ.pop("PRICESCOUT_DB_PATH", None)
            else:
                os.environ["PRICESCOUT_DB_PATH"] = previous_db_path


if __name__ == "__main__":
    main()
