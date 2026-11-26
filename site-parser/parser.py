#!/usr/bin/env python3
"""Демо-парсер: собирает цитаты с quotes.toscrape.com в CSV и XLSX.

Без внешних зависимостей — только стандартная библиотека Python.

Запуск:
    python parser.py --demo          # без сети, встроенные данные
    python parser.py --pages 3       # реальный сайт, 3 страницы
"""

from __future__ import annotations

import argparse
import csv
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent / "common"))
from xlsx_writer import write_xlsx  # noqa: E402

OUTPUT = BASE / "output"

DEMO_HTML = """
<html><body>
  <div class="quote">
    <span class="text">Простота — залог надёжности.</span>
    <small class="author">Андрей</small>
    <div class="tags"><a class="tag">код</a><a class="tag">python</a></div>
  </div>
  <div class="quote">
    <span class="text">Лучше сделать и пожалеть, чем не сделать и пожалеть.</span>
    <small class="author">Народная мудрость</small>
    <div class="tags"><a class="tag">жизнь</a></div>
  </div>
  <div class="quote">
    <span class="text">Автоматизируй то, что делаешь дважды.</span>
    <small class="author">Правило программиста</small>
    <div class="tags"><a class="tag">автоматизация</a><a class="tag">работа</a></div>
  </div>
</body></html>
"""


class QuotesHTMLParser(HTMLParser):
    """Достаёт текст, автора и теги из карточек quotes.toscrape.com."""

    def __init__(self) -> None:
        super().__init__()
        self.quotes: list[dict] = []
        self._in_quote = False
        self._in_text = False
        self._in_author = False
        self._in_tag = False
        self._buffer: list[str] = []
        self._text = ""
        self._author = ""
        self._tags: list[str] = []

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class", "").split()
        if tag == "div" and "quote" in classes:
            self._in_quote = True
            self._text = ""
            self._author = ""
            self._tags = []
        elif self._in_quote and tag == "span" and "text" in classes:
            self._in_text = True
            self._buffer = []
        elif self._in_quote and tag == "small" and "author" in classes:
            self._in_author = True
            self._buffer = []
        elif self._in_quote and tag == "a" and "tag" in classes:
            self._in_tag = True
            self._buffer = []

    def handle_endtag(self, tag):
        if tag == "span" and self._in_text:
            self._text = "".join(self._buffer).strip()
            self._in_text = False
        elif tag == "small" and self._in_author:
            self._author = "".join(self._buffer).strip()
            self._in_author = False
        elif tag == "a" and self._in_tag:
            self._tags.append("".join(self._buffer).strip())
            self._in_tag = False
        elif tag == "div" and self._in_quote:
            self.quotes.append(
                {
                    "text": self._text,
                    "author": self._author,
                    "tags": ", ".join(self._tags),
                }
            )
            self._in_quote = False

    def handle_data(self, data):
        if self._in_text or self._in_author or self._in_tag:
            self._buffer.append(data)


def parse_html(html: str) -> list[dict]:
    parser = QuotesHTMLParser()
    parser.feed(html)
    return parser.quotes


def fetch(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (freelance-demo parser)"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def save_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["Цитата", "Автор", "Теги"])
        for row in rows:
            writer.writerow([row["text"], row["author"], row["tags"]])


def save_xlsx(rows: list[dict], path: Path) -> None:
    data = [["Цитата", "Автор", "Теги"]]
    data += [[row["text"], row["author"], row["tags"]] for row in rows]
    write_xlsx(
        path,
        [
            {
                "name": "Цитаты",
                "rows": data,
                "widths": [70, 25, 30],
                "header": True,
            }
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Демо-парсер цитат")
    parser.add_argument("--pages", type=int, default=1, help="сколько страниц собрать")
    parser.add_argument("--demo", action="store_true", help="без сети, встроенные данные")
    parser.add_argument("--out", default="quotes", help="имя выходных файлов")
    args = parser.parse_args()

    if args.demo:
        rows = parse_html(DEMO_HTML)
        source = "встроенные данные"
    else:
        rows = []
        for page in range(1, max(1, args.pages) + 1):
            url = f"https://quotes.toscrape.com/page/{page}/"
            print(f"Загружаю {url}")
            rows.extend(parse_html(fetch(url)))
        source = f"quotes.toscrape.com, страниц: {args.pages}"

    if not rows:
        print("Не удалось собрать данные. Проверьте интернет или разметку сайта.")
        return

    OUTPUT.mkdir(exist_ok=True)
    csv_path = OUTPUT / f"{args.out}.csv"
    xlsx_path = OUTPUT / f"{args.out}.xlsx"
    save_csv(rows, csv_path)
    save_xlsx(rows, xlsx_path)

    print(f"Источник: {source}")
    print(f"Собрано записей: {len(rows)}")
    print(f"CSV:  {csv_path}")
    print(f"XLSX: {xlsx_path}")


if __name__ == "__main__":
    main()
