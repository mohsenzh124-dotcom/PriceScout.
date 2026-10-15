# PriceScout

Price comparison engine for electronics. Search for a product once and PriceScout collects offers from several Russian online stores, stores them in SQLite and shows the cheapest one.

محرّك لمقارنة أسعار الإلكترونيات: تبحث عن المنتج مرة واحدة، فيجمع PriceScout العروض من عدة متاجر روسية، ويحفظها في قاعدة بيانات SQLite، ويعرض لك أرخص عرض.

## Supported stores

| Store | Scraper |
|---|---|
| Ozon | `pricescout/app/scrapers/store_ozon.py` |
| Wildberries | `pricescout/app/scrapers/store_wildberries.py` |
| Yandex Market | `pricescout/app/scrapers/store_yandex_market.py` |
| DNS Shop | `pricescout/app/scrapers/store_dns.py` |
| Citilink | `pricescout/app/scrapers/store_citilink.py` |

## Quick start

Requires Python 3.11+.

### Windows: double-click

Double-click `Start_PriceScout.bat`. It picks the local `venv` Python if there is one, installs missing packages, starts the server and opens the browser.

### Manual

```bash
python -m venv venv
# Windows: venv\Scripts\activate    Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python run.py
```

Then open <http://127.0.0.1:8010>.

## API

| Endpoint | Description |
|---|---|
| `GET /` | Web interface |
| `GET /health` | Returns `ok` when the server is up |
| `GET /api/compare?q=<query>` | Collects offers for `<query>` and returns them with the best offer |

## Configuration

Copy `.env.example` to `.env` (or set the variables in your shell):

| Variable | Default |
|---|---|
| `PRICESCOUT_HOST` | `127.0.0.1` |
| `PRICESCOUT_PORT` | `8010` |
| `PRICESCOUT_DB_PATH` | `pricescout.db` |
| `PRICESCOUT_REQUEST_TIMEOUT` | `10` |
| `PRICESCOUT_USER_AGENT` | Chrome desktop user agent |

## Scripts

| Command | What it does |
|---|---|
| `python scripts/run_scraper.py --product "laptop"` | Scrape all stores for one product and save the offers |
| `python scripts/api_smoke_check.py` | Call the API in-process and check the response shape |
| `python scripts/scraper_coverage_check.py` | Live check of which stores return results for sample queries |

## Tests

```bash
python -m unittest discover -s tests -t .
```

## Project layout

```
.
├── pricescout/              # Application package
│   └── app/
│       ├── main.py          # WSGI app and dev server
│       ├── config.py        # Settings from environment variables
│       ├── db.py            # SQLite storage
│       ├── models.py, schemas.py
│       ├── api/routes.py    # HTTP routes
│       ├── services/        # Price comparison logic
│       ├── scrapers/        # One scraper per store
│       └── web/             # Frontend (HTML, CSS, JS)
├── scripts/                 # Command-line utilities
├── tests/                   # Unit tests
├── run.py                   # Start the server
├── run_gui.py               # Start the server and open the browser
├── Start_PriceScout.bat     # Windows launcher
└── requirements.txt
```
