"""Unit tests for PriceScout scraper parsing behavior."""

from __future__ import annotations

import unittest

from pricescout.app.scrapers.store_citilink import CitilinkScraper
from pricescout.app.scrapers.store_dns import DnsScraper
from pricescout.app.scrapers.store_ozon import OzonScraper
from pricescout.app.scrapers.store_wildberries import WildberriesScraper
from pricescout.app.scrapers.store_yandex_market import YandexMarketScraper


class MarketplaceScraperParsingTests(unittest.TestCase):
    """Validate Russian marketplace parser behavior with static HTML fixtures."""

    def test_ozon_parse_search_results_extracts_expected_offer(self) -> None:
        scraper = OzonScraper(timeout_seconds=5, user_agent="UnitTest")
        html = """
        <html>
          <body>
            <div data-index="1">
              <a href="/product/super-laptop-123/">
                <span>Ноутбук Super Laptop 15</span>
              </a>
              <span class="tsBody500Medium">129 990 ₽</span>
            </div>
          </body>
        </html>
        """

        offers = scraper._parse_search_results(html)

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].store_name, "Ozon")
        self.assertEqual(offers[0].product_name, "Ноутбук Super Laptop 15")
        self.assertEqual(offers[0].product_url, "https://www.ozon.ru/product/super-laptop-123/")
        self.assertEqual(offers[0].currency, "RUB")
        self.assertEqual(offers[0].price_amount, 129990.0)

    def test_wildberries_parse_search_results_extracts_expected_offer(self) -> None:
        scraper = WildberriesScraper(timeout_seconds=5, user_agent="UnitTest")
        html = """
        <html>
          <body>
            <article class="product-card">
              <a class="product-card__link" href="/catalog/123/detail.aspx"></a>
              <span class="product-card__name">Игровая мышь HyperSpeed</span>
              <ins class="price__lower-price">4 590 ₽</ins>
            </article>
          </body>
        </html>
        """

        offers = scraper._parse_search_results(html)

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].store_name, "Wildberries")
        self.assertEqual(offers[0].product_name, "Игровая мышь HyperSpeed")
        self.assertEqual(offers[0].product_url, "https://www.wildberries.ru/catalog/123/detail.aspx")
        self.assertEqual(offers[0].currency, "RUB")
        self.assertEqual(offers[0].price_amount, 4590.0)

    def test_yandex_market_parse_search_results_extracts_expected_offer(self) -> None:
        scraper = YandexMarketScraper(timeout_seconds=5, user_agent="UnitTest")
        html = """
        <html>
          <body>
            <article data-zone-name="snippet-card">
              <h3 data-auto="snippet-title">
                <a href="/product--videokarta-ultra/123"><span>Видеокарта Ultra RTX</span></a>
              </h3>
              <span data-auto="snippet-price-current">79 999 ₽</span>
            </article>
          </body>
        </html>
        """

        offers = scraper._parse_search_results(html)

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].store_name, "Yandex Market")
        self.assertEqual(offers[0].product_name, "Видеокарта Ultra RTX")
        self.assertEqual(offers[0].product_url, "https://market.yandex.ru/product--videokarta-ultra/123")
        self.assertEqual(offers[0].currency, "RUB")
        self.assertEqual(offers[0].price_amount, 79999.0)

    def test_dns_parse_search_results_extracts_expected_offer(self) -> None:
        scraper = DnsScraper(timeout_seconds=5, user_agent="UnitTest")
        html = """
        <html>
          <body>
            <div class="catalog-product">
              <a class="catalog-product__name" href="/product/abc/monitor-4k/"><span>Монитор 4K Vision</span></a>
              <div class="product-buy__price">35 490 ₽</div>
            </div>
          </body>
        </html>
        """

        offers = scraper._parse_search_results(html)

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].store_name, "DNS Shop")
        self.assertEqual(offers[0].product_name, "Монитор 4K Vision")
        self.assertEqual(offers[0].product_url, "https://www.dns-shop.ru/product/abc/monitor-4k/")
        self.assertEqual(offers[0].currency, "RUB")
        self.assertEqual(offers[0].price_amount, 35490.0)

    def test_citilink_parse_search_results_extracts_expected_offer(self) -> None:
        scraper = CitilinkScraper(timeout_seconds=5, user_agent="UnitTest")
        html = """
        <html>
          <body>
            <div class="ProductCardHorizontal">
              <a class="ProductCardHorizontal__title" href="/product/12345/naushniki-pro/">Наушники Pro Sound</a>
              <span class="ProductCardHorizontal__price_current-price">8 990 ₽</span>
            </div>
          </body>
        </html>
        """

        offers = scraper._parse_search_results(html)

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].store_name, "Citilink")
        self.assertEqual(offers[0].product_name, "Наушники Pro Sound")
        self.assertEqual(offers[0].product_url, "https://www.citilink.ru/product/12345/naushniki-pro/")
        self.assertEqual(offers[0].currency, "RUB")
        self.assertEqual(offers[0].price_amount, 8990.0)

    def test_scrapers_skip_malformed_cards_without_crashing(self) -> None:
        fixtures: list[tuple[object, str]] = [
            (
                OzonScraper(timeout_seconds=5, user_agent="UnitTest"),
                "<div data-index='1'><a href='/product/x/'><span>Товар</span></a></div>",
            ),
            (
                WildberriesScraper(timeout_seconds=5, user_agent="UnitTest"),
                "<article class='product-card'><span class='product-card__name'>Товар</span></article>",
            ),
            (
                YandexMarketScraper(timeout_seconds=5, user_agent="UnitTest"),
                "<article data-zone-name='snippet-card'><h3 data-auto='snippet-title'><a href='/p'><span>Товар</span></a></h3></article>",
            ),
            (
                DnsScraper(timeout_seconds=5, user_agent="UnitTest"),
                "<div class='catalog-product'><a class='catalog-product__name' href='/p'><span>Товар</span></a></div>",
            ),
            (
                CitilinkScraper(timeout_seconds=5, user_agent="UnitTest"),
                "<div class='ProductCardHorizontal'><a class='ProductCardHorizontal__title' href='/p'>Товар</a></div>",
            ),
        ]

        for scraper, html in fixtures:
            with self.subTest(scraper=scraper.__class__.__name__):
                offers = scraper._parse_search_results(html)
                self.assertEqual(offers, [])

    def test_json_ld_fallback_extracts_offer_from_embedded_script(self) -> None:
        scraper = OzonScraper(timeout_seconds=5, user_agent="UnitTest")
        html = """
        <html>
          <head>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "Product",
              "name": "Смартфон HyperPhone X",
              "url": "/product/hyperphone-x/",
              "offers": {
                "@type": "Offer",
                "price": "45990",
                "priceCurrency": "RUB"
              }
            }
            </script>
          </head>
          <body></body>
        </html>
        """

        offers = scraper._parse_json_ld_fallback(html_text=html, base_url="https://www.ozon.ru")

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].store_name, "Ozon")
        self.assertEqual(offers[0].product_name, "Смартфон HyperPhone X")
        self.assertEqual(offers[0].product_url, "https://www.ozon.ru/product/hyperphone-x/")
        self.assertEqual(offers[0].currency, "RUB")
        self.assertEqual(offers[0].price_amount, 45990.0)

    def test_build_headers_contains_required_request_headers(self) -> None:
        scraper = OzonScraper(timeout_seconds=5, user_agent="UnitTestAgent/1.0")

        headers = scraper.build_headers()

        self.assertEqual(headers.get("User-Agent"), "UnitTestAgent/1.0")
        self.assertIn("Accept-Language", headers)
        self.assertEqual(headers.get("Connection"), "keep-alive")
        self.assertIn("Accept", headers)


if __name__ == "__main__":
    unittest.main()
