"""Scraper package for PriceScout."""

from pricescout.app.scrapers.base_scraper import BaseScraper
from pricescout.app.scrapers.store_citilink import CitilinkScraper
from pricescout.app.scrapers.store_dns import DnsScraper
from pricescout.app.scrapers.store_ozon import OzonScraper
from pricescout.app.scrapers.store_wildberries import WildberriesScraper
from pricescout.app.scrapers.store_yandex_market import YandexMarketScraper

__all__ = [
    "BaseScraper",
    "OzonScraper",
    "WildberriesScraper",
    "YandexMarketScraper",
    "DnsScraper",
    "CitilinkScraper",
]
