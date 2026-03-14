"""Simple Python web application.

Run:
    python app.py
Then open http://127.0.0.1:8000
"""

from __future__ import annotations

import json
from http import HTTPStatus
from wsgiref.simple_server import make_server

from utils import load_items_from_csv, render_home_page

HOST = "127.0.0.1"
PORT = 8000
DATA_FILE = "data.csv"


def application(environ, start_response):
    """WSGI application entry point."""
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/")

    if method != "GET":
        status = f"{HTTPStatus.METHOD_NOT_ALLOWED.value} {HTTPStatus.METHOD_NOT_ALLOWED.phrase}"
        body = b"Method not allowed"
        headers = [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(body)))]
        start_response(status, headers)
        return [body]

    if path == "/":
        items = load_items_from_csv(DATA_FILE)
        html_body = render_home_page(items)
        payload = html_body.encode("utf-8")
        status = f"{HTTPStatus.OK.value} {HTTPStatus.OK.phrase}"
        headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(payload)))]
        start_response(status, headers)
        return [payload]

    if path == "/health":
        payload = b"ok"
        status = f"{HTTPStatus.OK.value} {HTTPStatus.OK.phrase}"
        headers = [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(payload)))]
        start_response(status, headers)
        return [payload]

    if path == "/api/items":
        items = load_items_from_csv(DATA_FILE)
        payload = json.dumps({"items": items}, ensure_ascii=False).encode("utf-8")
        status = f"{HTTPStatus.OK.value} {HTTPStatus.OK.phrase}"
        headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(payload)))]
        start_response(status, headers)
        return [payload]

    status = f"{HTTPStatus.NOT_FOUND.value} {HTTPStatus.NOT_FOUND.phrase}"
    payload = b"Not found"
    headers = [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(payload)))]
    start_response(status, headers)
    return [payload]


def main() -> None:
    """Start the local development server."""
    print(f"Starting server at http://{HOST}:{PORT}")
    with make_server(HOST, PORT, application) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
