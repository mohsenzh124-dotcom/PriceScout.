"""Utility helpers for the simple web application."""

from __future__ import annotations

import csv
import html
from pathlib import Path


def load_items_from_csv(file_path: str) -> list[dict[str, str]]:
    """Load item rows from a CSV file.

    Expected columns:
    - name
    - description

    Returns an empty list if the file does not exist.
    """
    path = Path(file_path)
    if not path.exists():
        return []

    items: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if not row:
                continue
            name = (row.get("name") or "").strip()
            description = (row.get("description") or "").strip()
            if not name and not description:
                continue
            items.append({"name": name, "description": description})

    return items


def render_home_page(items: list[dict[str, str]]) -> str:
    """Render a minimal HTML page listing items."""
    list_markup_parts: list[str] = []

    for item in items:
        safe_name = html.escape(item.get("name", ""))
        safe_description = html.escape(item.get("description", ""))
        list_markup_parts.append(
            "<li>"
            f"<strong>{safe_name}</strong>"
            f"<br><span>{safe_description}</span>"
            "</li>"
        )

    if not list_markup_parts:
        list_markup_parts.append("<li>No items found.</li>")

    list_markup = "\n".join(list_markup_parts)

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Simple Python Web App</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; line-height: 1.5; }}
    h1 {{ margin-bottom: 0.5rem; }}
    .hint {{ color: #555; margin-bottom: 1rem; }}
    ul {{ padding-left: 1.2rem; }}
    li {{ margin-bottom: 0.9rem; }}
  </style>
</head>
<body>
  <h1>Simple Python Web App</h1>
  <p class=\"hint\">Try <code>/api/items</code> for JSON and <code>/health</code> for health checks.</p>
  <ul>
    {list_markup}
  </ul>
</body>
</html>
"""