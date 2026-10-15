"""CLI script to collect offers for a product query (enhanced)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pricescout.app.config import get_settings
from pricescout.app.db import DatabaseClient
from pricescout.app.scrapers.store_citilink import CitilinkScraper
from pricescout.app.scrapers.store_dns import DnsScraper
from pricescout.app.scrapers.store_ozon import OzonScraper
from pricescout.app.scrapers.store_wildberries import WildberriesScraper
from pricescout.app.scrapers.store_yandex_market import YandexMarketScraper
from pricescout.app.services.price_comparator import PriceComparator


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for scraper execution."""
    parser = argparse.ArgumentParser(description="Collect PriceScout offers for a query")
    parser.add_argument("--product", required=True, help="Product search query")
    parser.add_argument(
        "--save-json",
        help="Optional: save collected offers to a JSON file",
        default=None,
    )
    return parser


def main() -> None:
    """Run scraper collection and print a short summary."""
    args = build_parser().parse_args()
    settings = get_settings()

    db_client = DatabaseClient(settings.db_path)
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

    try:
        offers = comparator.collect_offers(args.product)
        if not offers:
            print(f"⚠️  No offers were collected for query: {args.product}")
        else:
            print(f"✅ Collected {len(offers)} offers for query: {args.product}")

        if args.save_json:
            with open(args.save_json, "w", encoding="utf-8") as file:
                json.dump(
                    [offer.__dict__ for offer in offers],
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
            print(f"📄 Results saved to {args.save_json}")
    finally:
        db_client.close()


if __name__ == "__main__":
    main()
