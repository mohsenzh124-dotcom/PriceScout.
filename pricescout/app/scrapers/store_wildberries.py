"""Wildberries scraper implementation for PriceScout."""

from __future__ import annotations

from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from pricescout.app.models import ScrapedOffer
from pricescout.app.scrapers.base_scraper import BaseScraper


class WildberriesScraper(BaseScraper):
    """Scrape Wildberries search results with defensive parsing and diagnostics."""

    _BASE_URL = "https://www.wildberries.ru"

    def __init__(self, timeout_seconds: int, user_agent: str) -> None:
        super().__init__(store_name="Wildberries", timeout_seconds=timeout_seconds, user_agent=user_agent)

    def search(self, product_query: str) -> list[ScrapedOffer]:
        """Fetch and parse Wildberries results for a product query."""
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

        search_url = f"{self._BASE_URL}/catalog/0/search.aspx?search={quote_plus(normalized_query)}"
        try:
            response = requests.get(search_url, headers=self.build_headers(), timeout=self.timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            self._set_diagnostics(
                self._build_diagnostics(
                    query=normalized_query,
                    request_url=search_url,
                    final_url=None,
                    status_code=None,
                    response_bytes=0,
                    html_card_count=0,
                    html_offer_count=0,
                    fallback_offer_count=0,
                    parse_stage="request",
                    reason=f"Request failed: {exc.__class__.__name__}",
                )
            )
            return []

        html_text = response.text
        html_offers, html_card_count = self._parse_html_offers(html_text)
        fallback_offers: list[ScrapedOffer] = []
        if not html_offers:
            fallback_offers = self._parse_json_ld_fallback(html_text=html_text, base_url=self._BASE_URL)

        offers = html_offers or fallback_offers
        if html_offers:
            parse_stage = "html"
            reason = "Parsed offers from HTML card selectors"
        elif fallback_offers:
            parse_stage = "json_ld_fallback"
            reason = "HTML selectors returned no offers; JSON-LD fallback produced offers"
        else:
            parse_stage = "empty"
            reason = "No offers found via HTML selectors or JSON-LD fallback"

        self._set_diagnostics(
            self._build_diagnostics(
                query=normalized_query,
                request_url=search_url,
                final_url=response.url,
                status_code=response.status_code,
                response_bytes=len(response.content or b""),
                html_card_count=html_card_count,
                html_offer_count=len(html_offers),
                fallback_offer_count=len(fallback_offers),
                parse_stage=parse_stage,
                reason=reason,
            )
        )
        return offers

    def _parse_search_results(self, html_text: str) -> list[ScrapedOffer]:
        """Parse Wildberries HTML and return normalized offers."""
        offers, _ = self._parse_html_offers(html_text)
        return offers

    def _parse_html_offers(self, html_text: str) -> tuple[list[ScrapedOffer], int]:
        """Parse Wildberries HTML cards and return offers with card count."""
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            cards = soup.select("article.product-card, div.product-card, div.j-card-item")
        except Exception:
            return [], 0

        offers: list[ScrapedOffer] = []
        for card in cards[:40]:
            try:
                link_element = card.select_one("a.product-card__link, a[href*='/catalog/']")
                price_element = card.select_one(
                    "ins.price__lower-price, span.price__lower-price, span.lower-price"
                )
                product_name = self._extract_first_non_empty_text(
                    card,
                    selectors=(
                        "span.product-card__name",
                        "span.goods-name",
                        "a.product-card__link",
                        "a[href*='/catalog/']",
                    ),
                )

                if not link_element or not price_element or not product_name:
                    continue

                price_amount = self._parse_price_value(price_element.get_text(" ", strip=True))
                if price_amount is None:
                    continue

                href = (link_element.get("href") or "").strip()
                product_url = self._normalize_url(raw_url=href, base_url=self._BASE_URL)
                if not product_url:
                    continue

                offers.append(
                    ScrapedOffer(
                        store_name=self.store_name,
                        product_name=product_name,
                        product_url=product_url,
                        currency="RUB",
                        price_amount=price_amount,
                    )
                )
            except Exception:
                continue

        return offers, len(cards)

    def _extract_first_non_empty_text(self, card: Tag, selectors: tuple[str, ...]) -> str:
        """Return the first non-empty text for provided selector candidates."""
        for selector in selectors:
            element = card.select_one(selector)
            if element is None:
                continue

            value = (element.get_text(" ", strip=True) or "").strip()
            if value:
                return value

        return ""
