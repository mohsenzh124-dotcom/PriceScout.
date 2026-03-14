"""Schema helpers for PriceScout API payloads."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from pricescout.app.models import Offer


@dataclass(frozen=True)
class ComparisonResponse:
    """Normalized comparison response returned by the API."""

    query: str
    offers: list[Offer]
    best_offer: Offer | None

    @property
    def total_offers(self) -> int:
        """Return total number of offers in the response."""
        return len(self.offers)

    def to_dict(self) -> dict:
        """Convert response to a JSON-serializable dictionary."""
        return {
            "query": self.query,
            "offers": [asdict(offer) for offer in self.offers],
            "best_offer": asdict(self.best_offer) if self.best_offer else None,
            "total_offers": self.total_offers,
        }
