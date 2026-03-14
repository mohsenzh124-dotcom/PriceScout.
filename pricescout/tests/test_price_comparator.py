"""Unit tests for PriceScout price comparison service."""

from __future__ import annotations

import tempfile
import unittest

from pricescout.app.db import DatabaseClient
from pricescout.app.models import ScrapedOffer
from pricescout.app.scrapers.base_scraper import BaseScraper
from pricescout.app.services.price_comparator import PriceComparator


class _FixedScraper(BaseScraper):
    """Deterministic scraper used for service-level tests."""

    def __init__(self, store_name: str, prices: list[float], fixed_url: str | None = None) -> None:
        super().__init__(store_name=store_name, timeout_seconds=5, user_agent="UnitTest")
        self._prices = prices
        self._fixed_url = fixed_url

    def search(self, product_query: str) -> list[ScrapedOffer]:
        normalized_query = product_query.strip()
        if not normalized_query:
            self._set_diagnostics(
                self._build_diagnostics(
                    query="",
                    request_url="",
                    final_url=None,
                    status_code=None,
                    response_bytes=0,
                    html_card_count=0,
                    html_offer_count=0,
                    fallback_offer_count=0,
                    parse_stage="validation",
                    reason="Query is empty after trimming",
                )
            )
            return []

        offers: list[ScrapedOffer] = []
        for index, price in enumerate(self._prices, start=1):
            product_url = self._fixed_url or f"https://example.test/{self.store_name.lower()}/{index}"
            offers.append(
                ScrapedOffer(
                    store_name=self.store_name,
                    product_name=f"{normalized_query} option {index}",
                    product_url=product_url,
                    currency="USD",
                    price_amount=price,
                )
            )

        self._set_diagnostics(
            self._build_diagnostics(
                query=normalized_query,
                request_url=f"https://example.test/search?q={normalized_query}",
                final_url=f"https://example.test/search?q={normalized_query}",
                status_code=200,
                response_bytes=1024,
                html_card_count=len(self._prices),
                html_offer_count=len(offers),
                fallback_offer_count=0,
                parse_stage="html",
                reason="Deterministic test scraper parsed fixture cards",
            )
        )

        return offers


class _FailingScraper(BaseScraper):
    """Scraper that raises to verify comparator-level exception diagnostics."""

    def __init__(self, store_name: str) -> None:
        super().__init__(store_name=store_name, timeout_seconds=5, user_agent="UnitTest")

    def search(self, product_query: str) -> list[ScrapedOffer]:
        raise RuntimeError("boom")


class PriceComparatorTests(unittest.TestCase):
    """Validate core comparison behavior for the service layer."""

    def test_get_best_prices_returns_sorted_offers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_client = DatabaseClient(f"{tmp_dir}/pricescout_test.db")
            try:
                db_client.init_db()

                comparator = PriceComparator(
                    db_client=db_client,
                    scrapers=[
                        _FixedScraper(store_name="StoreA", prices=[1299.99, 1179.49]),
                        _FixedScraper(store_name="StoreB", prices=[1321.00]),
                    ],
                )

                payload = comparator.get_best_prices("gaming laptop")
            finally:
                db_client.close()

        self.assertEqual(payload["query"], "gaming laptop")
        self.assertEqual(payload["total_offers"], 3)
        self.assertIsNotNone(payload["best_offer"])
        self.assertEqual(payload["best_offer"]["price_amount"], 1179.49)
        prices = [offer["price_amount"] for offer in payload["offers"]]
        self.assertEqual(prices, sorted(prices))

    def test_get_best_prices_for_empty_query_returns_empty_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_client = DatabaseClient(f"{tmp_dir}/pricescout_test.db")
            try:
                db_client.init_db()
                comparator = PriceComparator(db_client=db_client, scrapers=[])
                payload = comparator.get_best_prices("   ")
            finally:
                db_client.close()

        self.assertEqual(payload["query"], "")
        self.assertEqual(payload["total_offers"], 0)
        self.assertEqual(payload["offers"], [])
        self.assertIsNone(payload["best_offer"])
        self.assertEqual(payload["diagnostics"], [])

    def test_insert_deduplicates_same_product_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_client = DatabaseClient(f"{tmp_dir}/pricescout_test.db")
            try:
                db_client.init_db()
                comparator = PriceComparator(
                    db_client=db_client,
                    scrapers=[
                        _FixedScraper(
                            store_name="StoreA",
                            prices=[299.00, 279.00],
                            fixed_url="https://example.test/shared/headphones",
                        )
                    ],
                )

                payload = comparator.get_best_prices("noise cancelling headphones")
                saved = db_client.get_latest_offers("noise cancelling headphones")
            finally:
                db_client.close()

        self.assertEqual(payload["total_offers"], 2)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].product_url, "https://example.test/shared/headphones")

    def test_get_best_prices_includes_per_scraper_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_client = DatabaseClient(f"{tmp_dir}/pricescout_test.db")
            try:
                db_client.init_db()
                comparator = PriceComparator(
                    db_client=db_client,
                    scrapers=[
                        _FixedScraper(store_name="StoreA", prices=[999.0]),
                        _FailingScraper(store_name="StoreBroken"),
                    ],
                )

                payload = comparator.get_best_prices("smartphone")
            finally:
                db_client.close()

        diagnostics = payload.get("diagnostics")
        self.assertIsInstance(diagnostics, list)
        self.assertEqual(len(diagnostics), 2)

        by_store = {entry["store_name"]: entry for entry in diagnostics}
        self.assertIn("StoreA", by_store)
        self.assertIn("StoreBroken", by_store)

        ok_entry = by_store["StoreA"]
        self.assertEqual(ok_entry["query"], "smartphone")
        self.assertEqual(ok_entry["status_code"], 200)
        self.assertGreater(ok_entry["response_bytes"], 0)
        self.assertEqual(ok_entry["parse_stage"], "html")
        self.assertEqual(ok_entry["total_offer_count"], 1)

        failed_entry = by_store["StoreBroken"]
        self.assertEqual(failed_entry["parse_stage"], "exception")
        self.assertEqual(failed_entry["total_offer_count"], 0)
        self.assertIn("Unhandled scraper exception", failed_entry["reason"])


if __name__ == "__main__":
    unittest.main()
