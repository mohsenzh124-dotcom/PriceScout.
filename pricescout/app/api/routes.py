"""HTTP route handlers for PriceScout."""

from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs

from pricescout.app.services.price_comparator import PriceComparator

_WEB_DIR = Path(__file__).resolve().parent.parent / "web"
_INDEX_FILE = _WEB_DIR / "index.html"
_STATIC_FILES: dict[str, tuple[str, Path]] = {
    "style.css": ("text/css", _WEB_DIR / "style.css"),
    "app.js": ("application/javascript", _WEB_DIR / "app.js"),
}


def _json_response(payload: dict) -> bytes:
    """Serialize a JSON payload to UTF-8 bytes."""
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _load_file(file_path: Path) -> bytes | None:
    """Read a UTF-8 text file and return bytes, or None if unavailable."""
    try:
        return file_path.read_text(encoding="utf-8").encode("utf-8")
    except OSError:
        return None


def _handle_frontend(path: str) -> tuple[HTTPStatus, str, bytes] | None:
    """Handle frontend page and static asset requests."""
    if path == "/":
        payload = _load_file(_INDEX_FILE)
        if payload is None:
            return HTTPStatus.INTERNAL_SERVER_ERROR, "text/plain", b"Frontend index is unavailable"
        return HTTPStatus.OK, "text/html", payload

    if path.startswith("/static/"):
        file_name = path.split("/", 2)[-1]
        static_file = _STATIC_FILES.get(file_name)
        if static_file is None:
            return HTTPStatus.NOT_FOUND, "text/plain", b"Not found"

        content_type, file_path = static_file
        payload = _load_file(file_path)
        if payload is None:
            return HTTPStatus.INTERNAL_SERVER_ERROR, "text/plain", b"Static asset is unavailable"
        return HTTPStatus.OK, content_type, payload

    return None


def handle_request(
    *,
    method: str,
    path: str,
    query_string: str,
    comparator: PriceComparator,
) -> tuple[HTTPStatus, str, bytes]:
    """Dispatch incoming requests and return a normalized HTTP response tuple."""
    if method != "GET":
        return HTTPStatus.METHOD_NOT_ALLOWED, "text/plain", b"Method not allowed"

    frontend_response = _handle_frontend(path)
    if frontend_response is not None:
        return frontend_response

    if path == "/health":
        return HTTPStatus.OK, "text/plain", b"ok"

    if path == "/api/compare":
        query_params = parse_qs(query_string, keep_blank_values=False)
        query = (query_params.get("q") or [""])[0].strip()
        if not query:
            return (
                HTTPStatus.BAD_REQUEST,
                "application/json",
                _json_response({"error": "Missing required query parameter: q"}),
            )

        comparison = comparator.get_best_prices(query)
        return HTTPStatus.OK, "application/json", _json_response(comparison)

    return HTTPStatus.NOT_FOUND, "text/plain", b"Not found"
