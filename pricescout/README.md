# PriceScout

PriceScout is a starter Python web app for comparing product prices across multiple online stores.

## Features in this scaffold

- Minimal WSGI web API with health and comparison endpoints
- Modular app structure (`api`, `services`, `scrapers`)
- SQLite integration for storing collected price records
- Store scraper base class with Amazon/eBay starter adapters
- Unit tests for core comparison and parser behavior

## Quick start

### Windows double-click launcher (recommended)

- Double-click `Start_PriceScout.bat` in the project root.
- The launcher prefers `venv\Scripts\python.exe`, then `py -3`, then `python`.
- It starts `run_gui.py`, which launches the backend and opens the browser automatically.

### Manual start

1. Create and activate a virtual environment (recommended).
2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Run the app:

   ```powershell
   python run.py
   ```

4. Open:

- `http://127.0.0.1:8010/health`
- `http://127.0.0.1:8010/api/compare?q=wireless+mouse`

## Run tests

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## Project layout

- `app/main.py`: WSGI app bootstrap and server runner
- `app/api/routes.py`: HTTP route handlers
- `app/services/price_comparator.py`: normalization and comparison logic
- `app/scrapers/*`: scraper interface and store adapters
- `app/db.py`: SQLite persistence for offers
- `scripts/run_scraper.py`: script entry point for collecting and storing offers
