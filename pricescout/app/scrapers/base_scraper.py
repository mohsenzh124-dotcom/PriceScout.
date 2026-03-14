"""Base scraper abstractions for PriceScout."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
import re
from typing import Any

from bs4 import BeautifulSoup

from pricescout.app.models import ScrapedOffer, ScraperDiagnostics


class BaseScraper(ABC):
    """Abstract scraper contract used by the comparison service."""

    _PRICE_PATTERN = re.compile(r"\d[\d\s\xa0]*(?:[.,]\d{1,2})?")

    def __init__(self, store_name: str, timeout_seconds: int, user_agent: str) -> None:
        self.store_name = store_name
        self.timeout_seconds = max(1, timeout_seconds)
        self.user_agent = user_agent.strip() or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
        self._last_diagnostics: ScraperDiagnostics | None = None

    @property
    def last_diagnostics(self) -> ScraperDiagnostics | None:
        """Return diagnostics from the most recent scraper run."""
        return self._last_diagnostics

    def build_headers(self) -> dict[str, str]:
        """Return default HTTP headers for realistic Russian marketplace requests."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def _set_diagnostics(self, diagnostics: ScraperDiagnostics) -> None:
        """Persist diagnostics for the latest scraper execution."""
        self._last_diagnostics = diagnostics

    def _build_diagnostics(
        self,
        *,
        query: str,
        request_url: str,
        final_url: str | None,
        status_code: int | None,
        response_bytes: int,
        html_card_count: int,
        html_offer_count: int,
        fallback_offer_count: int,
        parse_stage: str,
        reason: str,
    ) -> ScraperDiagnostics:
        """Construct an immutable diagnostics payload with normalized totals."""
        return ScraperDiagnostics(
            store_name=self.store_name,
            query=query,
            request_url=request_url,
            final_url=final_url,
            status_code=status_code,
            response_bytes=max(0, response_bytes),
            html_card_count=max(0, html_card_count),
            html_offer_count=max(0, html_offer_count),
            fallback_offer_count=max(0, fallback_offer_count),
            total_offer_count=max(0, html_offer_count + fallback_offer_count),
            parse_stage=parse_stage.strip() or "unknown",
            reason=reason.strip() or "No diagnostics reason provided",
        )

    def _parse_price_value(self, raw_price: str) -> float | None:
        """Parse first valid numeric price fragment from raw price text."""
        normalized = (
            (raw_price or "")
            .replace("\xa0", " ")
            .replace("₽", "")
            .replace("руб.", "")
            .replace("руб", "")
            .strip()
        )
        if not normalized:
            return None

        match = self._PRICE_PATTERN.search(normalized)
        if match is None:
            return None

        value = match.group(0).replace(" ", "").replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return None

    def _parse_json_ld_fallback(self, html_text: str, base_url: str) -> list[ScrapedOffer]:
        """Extract offers from JSON-LD blocks as a fallback when HTML cards fail."""
        try:
            soup = BeautifulSoup(html_text, "html.parser")
        except Exception:
            return []

        scripts = soup.select("script[type='application/ld+json']")
        if not scripts:
            return []

        offers: list[ScrapedOffer] = []
        for script in scripts:
            script_text = (script.get_text() or "").strip()
            if not script_text:
                continue

            try:
                payload = json.loads(script_text)
            except json.JSONDecodeError:
                continue

            for node in self._iter_json_ld_nodes(payload):
                if not isinstance(node, dict):
                    continue

                if not self._is_product_node(node):
                    continue

                product_name = str(node.get("name") or "").strip()
                product_url = self._normalize_url(str(node.get("url") or "").strip(), base_url)
                price_amount = self._extract_json_ld_price(node)
                if not product_name or not product_url or price_amount is None:
                    continue

                price_currency = self._extract_json_ld_currency(node) or "RUB"
                offers.append(
                    ScrapedOffer(
                        store_name=self.store_name,
                        product_name=product_name,
                        product_url=product_url,
                        currency=price_currency,
                        price_amount=price_amount,
                    )
                )

        return self._deduplicate_offers(offers)

    def _iter_json_ld_nodes(self, payload: Any) -> list[dict[str, Any]]:
        """Flatten JSON-LD payload into iterable dictionary nodes."""
        nodes: list[dict[str, Any]] = []

        if isinstance(payload, dict):
            nodes.append(payload)
            graph = payload.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    nodes.extend(self._iter_json_ld_nodes(item))
        elif isinstance(payload, list):
            for item in payload:
                nodes.extend(self._iter_json_ld_nodes(item))

        return nodes

    def _is_product_node(self, node: dict[str, Any]) -> bool:
        """Check whether a JSON-LD node describes a product."""
        node_type = node.get("@type")
        if isinstance(node_type, str):
            return node_type.lower() == "product"

        if isinstance(node_type, list):
            return any(str(item).lower() == "product" for item in node_type)

        return False

    def _extract_json_ld_price(self, node: dict[str, Any]) -> float | None:
        """Extract a numeric price value from JSON-LD product offers."""
        offers_payload = node.get("offers")
        if isinstance(offers_payload, dict):
            return self._extract_price_from_offer_node(offers_payload)

        if isinstance(offers_payload, list):
            for offer_node in offers_payload:
                if isinstance(offer_node, dict):
                    value = self._extract_price_from_offer_node(offer_node)
                    if value is not None:
                        return value

        return None

    def _extract_json_ld_currency(self, node: dict[str, Any]) -> str | None:
        """Extract currency from JSON-LD offer nodes."""
        offers_payload = node.get("offers")
        offer_nodes: list[dict[str, Any]] = []

        if isinstance(offers_payload, dict):
            offer_nodes.append(offers_payload)
        elif isinstance(offers_payload, list):
            offer_nodes.extend(item for item in offers_payload if isinstance(item, dict))

        for offer_node in offer_nodes:
            currency = str(offer_node.get("priceCurrency") or "").strip().upper()
            if currency:
                return currency

        return None

    def _extract_price_from_offer_node(self, offer_node: dict[str, Any]) -> float | None:
        """Extract price from an offer-like JSON-LD object."""
        for key in ("price", "lowPrice", "highPrice"):
            value = offer_node.get(key)
            if value is None:
                continue
            parsed = self._parse_price_value(str(value))
            if parsed is not None:
                return parsed

        return None

    def _normalize_url(self, raw_url: str, base_url: str) -> str:
        """Normalize a possibly relative URL to an absolute URL."""
        if not raw_url:
            return ""

        if raw_url.startswith("//"):
            return f"https:{raw_url}"

        if raw_url.startswith("http"):
            return raw_url

        if raw_url.startswith("/"):
            return f"{base_url.rstrip('/')}{raw_url}"

        return f"{base_url.rstrip('/')}/{raw_url.lstrip('/')}"

    def _deduplicate_offers(self, offers: list[ScrapedOffer]) -> list[ScrapedOffer]:
        """Remove duplicate offers to keep fallback output clean."""
        seen: set[tuple[str, str, float]] = set()
        deduplicated: list[ScrapedOffer] = []

        for offer in offers:
            signature = (offer.product_name, offer.product_url, offer.price_amount)
            if signature in seen:
                continue
            seen.add(signature)
            deduplicated.append(offer)

        return deduplicated

    @abstractmethod
    def search(self, product_query: str) -> list[ScrapedOffer]:
        """Return scraped offers for a product query."""
