"""WSGI application entry point for PriceScout."""

from __future__ import annotations

from wsgiref.simple_server import make_server

from pricescout.app.api.routes import handle_request
from pricescout.app.config import get_settings
from pricescout.app.db import DatabaseClient
from pricescout.app.scrapers.store_citilink import CitilinkScraper
from pricescout.app.scrapers.store_dns import DnsScraper
from pricescout.app.scrapers.store_ozon import OzonScraper
from pricescout.app.scrapers.store_wildberries import WildberriesScraper
from pricescout.app.scrapers.store_yandex_market import YandexMarketScraper
from pricescout.app.services.price_comparator import PriceComparator

_SETTINGS = get_settings()
_DB = DatabaseClient(_SETTINGS.db_path)
_DB.init_db()
_COMPARATOR = PriceComparator(
    db_client=_DB,
    scrapers=[
        OzonScraper(timeout_seconds=_SETTINGS.request_timeout, user_agent=_SETTINGS.user_agent),
        WildberriesScraper(timeout_seconds=_SETTINGS.request_timeout, user_agent=_SETTINGS.user_agent),
        YandexMarketScraper(timeout_seconds=_SETTINGS.request_timeout, user_agent=_SETTINGS.user_agent),
        DnsScraper(timeout_seconds=_SETTINGS.request_timeout, user_agent=_SETTINGS.user_agent),
        CitilinkScraper(timeout_seconds=_SETTINGS.request_timeout, user_agent=_SETTINGS.user_agent),
    ],
)


def application(environ, start_response):
    """WSGI application callable."""
    method = (environ.get("REQUEST_METHOD") or "GET").upper()
    path = environ.get("PATH_INFO") or "/"
    query_string = environ.get("QUERY_STRING") or ""

    status_code, content_type, payload = handle_request(
        method=method,
        path=path,
        query_string=query_string,
        comparator=_COMPARATOR,
    )

    status_line = f"{status_code.value} {status_code.phrase}"
    headers = [
        ("Content-Type", f"{content_type}; charset=utf-8"),
        ("Content-Length", str(len(payload))),
    ]
    start_response(status_line, headers)
    return [payload]


def main() -> None:
    """Run the local development server."""
    print(f"PriceScout API running at http://{_SETTINGS.host}:{_SETTINGS.port}")
    with make_server(_SETTINGS.host, _SETTINGS.port, application) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
