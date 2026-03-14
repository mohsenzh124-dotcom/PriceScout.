"""Price comparison service for PriceScout."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Protocol

from pricescout.app.models import Offer, ScraperDiagnostics
from pricescout.app.scrapers.base_scraper import BaseScraper


class OfferRepositoryProtocol(Protocol):
    """Repository interface required by the comparator service."""

    def insert_offers(self, offers: list[Offer]) -> None:
        """Persist offers."""

    def get_latest_offers(self, product_query: str) -> list[Offer]:
        """Fetch latest offers by query."""


class PriceComparator:
    """Coordinate scraper collection and best-offer selection."""

    def __init__(self, db_client: OfferRepositoryProtocol, scrapers: list[BaseScraper]) -> None:
        self._db_client = db_client
        self._scrapers = scrapers
        self._last_diagnostics: list[ScraperDiagnostics] = []

    @property
    def last_diagnostics(self) -> list[ScraperDiagnostics]:
        """Return diagnostics captured during the latest collection run."""
        return list(self._last_diagnostics)

    def collect_offers(self, product_query: str) -> list[Offer]:
        """Collect offers from all configured scrapers and persist them."""
        normalized_query = product_query.strip()
        if not normalized_query:
            self._last_diagnostics = []
            return []

        collected_at = datetime.now(tz=UTC).isoformat()
        collected_offers: list[Offer] = []
        diagnostics: list[ScraperDiagnostics] = []

        for scraper in self._scrapers:
            try:
                scraped_offers = scraper.search(normalized_query)
            except Exception as exc:
                diagnostics.append(
                    ScraperDiagnostics(
                        store_name=scraper.store_name,
                        query=normalized_query,
                        request_url="",
                        final_url=None,
                        status_code=None,
                        response_bytes=0,
                        html_card_count=0,
                        html_offer_count=0,
                        fallback_offer_count=0,
                        total_offer_count=0,
                        parse_stage="exception",
                        reason=f"Unhandled scraper exception: {exc.__class__.__name__}",
                    )
                )
                continue

            if scraper.last_diagnostics is not None:
                diagnostics.append(scraper.last_diagnostics)

            for scraped_offer in scraped_offers:
                collected_offers.append(
                    Offer(
                        product_query=normalized_query,
                        store_name=scraped_offer.store_name,
                        product_name=scraped_offer.product_name,
                        product_url=scraped_offer.product_url,
                        currency=scraped_offer.currency,
                        price_amount=float(scraped_offer.price_amount),
                        collected_at=collected_at,
                    )
                )

        self._last_diagnostics = diagnostics

        if collected_offers:
            self._db_client.insert_offers(collected_offers)

        return collected_offers

    def get_best_prices(self, product_query: str) -> dict:
        """Return normalized comparison payload for API consumers."""
        normalized_query = product_query.strip()
        if not normalized_query:
            return {
                "query": "",
                "offers": [],
                "best_offer": None,
                "total_offers": 0,
                "diagnostics": [],
            }

        offers = self.collect_offers(normalized_query)
        if not offers:
            offers = self._db_client.get_latest_offers(normalized_query)

        sorted_offers = sorted(offers, key=lambda offer: offer.price_amount)
        best_offer = sorted_offers[0] if sorted_offers else None

        return {
            "query": normalized_query,
            "offers": [asdict(offer) for offer in sorted_offers],
            "best_offer": asdict(best_offer) if best_offer else None,
            "total_offers": len(sorted_offers),
            "diagnostics": [asdict(item) for item in self._last_diagnostics],
        }
