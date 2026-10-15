"""Deterministic API smoke checks for PriceScout WSGI endpoints."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from urllib.parse import quote_plus

# Allow running as `python scripts/api_smoke_check.py` from the repository root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pricescout.app.main import _DB, application
from pricescout.app.models import Offer


def call_app(method: str, path: str, query: str = "") -> tuple[str, dict[str, str], bytes]:
    """Call the WSGI application directly and return status, headers, and body."""
    status_holder: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_holder["status"] = status
        status_holder["headers"] = headers

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "SERVER_NAME": "127.0.0.1",
        "SERVER_PORT": "8010",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": BytesIO(b""),
        "wsgi.errors": BytesIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }

    body = b"".join(application(environ, start_response))
    headers = dict(status_holder.get("headers", []))
    status = str(status_holder.get("status", ""))
    return status, headers, body


def _add_result(results: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    """Append a check result and keep output formatting consistent."""
    results.append(payload)


def main() -> None:
    """Run smoke checks and print a JSON report."""
    smoke_query = os.getenv("PRICESCOUT_SMOKE_QUERY", "laptop").strip() or "laptop"
    encoded_query = quote_plus(smoke_query)

    seed_offer = Offer(
        product_query=smoke_query,
        store_name="SeedStore",
        product_name=f"Seed {smoke_query.title()}",
        product_url=f"https://seed.local/products/{encoded_query}",
        currency="USD",
        price_amount=19.99,
        collected_at=datetime.now(tz=UTC).isoformat(),
    )
    _DB.insert_offers([seed_offer])

    results: list[dict[str, Any]] = []

    status, headers, body = call_app("GET", "/health")
    _add_result(
        results,
        {
            "name": "GET /health",
            "status": status,
            "content_type": headers.get("Content-Type", ""),
            "body": body.decode("utf-8", errors="replace"),
            "pass": status.startswith("200") and body == b"ok",
        },
    )

    status, headers, body = call_app("GET", "/api/compare")
    missing_q_payload = json.loads(body.decode("utf-8"))
    _add_result(
        results,
        {
            "name": "GET /api/compare (missing q)",
            "status": status,
            "content_type": headers.get("Content-Type", ""),
            "body": missing_q_payload,
            "pass": status.startswith("400")
            and missing_q_payload.get("error") == "Missing required query parameter: q",
        },
    )

    status, headers, body = call_app("GET", "/api/compare", f"q={encoded_query}")
    compare_payload = json.loads(body.decode("utf-8"))
    offers = compare_payload.get("offers", [])
    _add_result(
        results,
        {
            "name": f"GET /api/compare?q={encoded_query}",
            "status": status,
            "content_type": headers.get("Content-Type", ""),
            "query": compare_payload.get("query"),
            "total_offers": compare_payload.get("total_offers"),
            "has_best_offer": compare_payload.get("best_offer") is not None,
            "has_offers": isinstance(offers, list) and len(offers) > 0,
            "pass": status.startswith("200")
            and compare_payload.get("query") == smoke_query
            and isinstance(offers, list)
            and len(offers) > 0
            and compare_payload.get("best_offer") is not None,
        },
    )

    status, headers, body = call_app("POST", "/health")
    _add_result(
        results,
        {
            "name": "POST /health",
            "status": status,
            "content_type": headers.get("Content-Type", ""),
            "body": body.decode("utf-8", errors="replace"),
            "pass": status.startswith("405") and body == b"Method not allowed",
        },
    )

    status, headers, body = call_app("GET", "/does-not-exist")
    _add_result(
        results,
        {
            "name": "GET /does-not-exist",
            "status": status,
            "content_type": headers.get("Content-Type", ""),
            "body": body.decode("utf-8", errors="replace"),
            "pass": status.startswith("404") and body == b"Not found",
        },
    )

    status, headers, body = call_app("GET", "/api/compare", "q=%20%20")
    blank_q_payload = json.loads(body.decode("utf-8"))
    _add_result(
        results,
        {
            "name": "GET /api/compare?q=%20%20 (blank q)",
            "status": status,
            "content_type": headers.get("Content-Type", ""),
            "body": blank_q_payload,
            "pass": status.startswith("400")
            and blank_q_payload.get("error") == "Missing required query parameter: q",
        },
    )

    passed = sum(1 for result in results if result.get("pass"))
    report = {
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
        },
        "results": results,
    }
    print(json.dumps(report, indent=2))
    _DB.close()


if __name__ == "__main__":
    main()
