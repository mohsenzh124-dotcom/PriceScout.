"""Domain models for PriceScout."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScrapedOffer:
    """A product offer returned directly by a scraper."""

    store_name: str
    product_name: str
    product_url: str
    currency: str
    price_amount: float


@dataclass(frozen=True)
class Offer:
    """A normalized and persisted product offer record."""

    product_query: str
    store_name: str
    product_name: str
    product_url: str
    currency: str
    price_amount: float
    collected_at: str


@dataclass(frozen=True)
class ScraperDiagnostics:
    """Per-scraper request and parsing diagnostics for observability."""

    store_name: str
    query: str
    request_url: str
    final_url: str | None
    status_code: int | None
    response_bytes: int
    html_card_count: int
    html_offer_count: int
    fallback_offer_count: int
    total_offer_count: int
    parse_stage: str
    reason: str
