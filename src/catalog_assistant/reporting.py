from __future__ import annotations

from pathlib import Path

from jinja2 import Template
from markdown import markdown

from .config import REPORTS_DIR


HTML_TEMPLATE = Template(
    """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>{{ title }}</title>
  <style>
    body { font-family: Georgia, serif; margin: 2rem auto; max-width: 900px; color: #1f2937; line-height: 1.6; }
    h1, h2, h3 { color: #111827; }
    code { background: #f3f4f6; padding: 0.1rem 0.3rem; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid #d1d5db; padding: 0.5rem; text-align: left; }
  </style>
</head>
<body>
{{ content | safe }}
</body>
</html>
"""
)


def write_markdown_report(filename: str, title: str, content: str) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    markdown_path = REPORTS_DIR / f"{filename}.md"
    html_path = REPORTS_DIR / f"{filename}.html"
    markdown_path.write_text(content, encoding="utf-8")
    html_body = markdown(content, extensions=["tables", "fenced_code"])
    html_path.write_text(HTML_TEMPLATE.render(title=title, content=html_body), encoding="utf-8")
    return markdown_path, html_path
