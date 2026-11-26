#!/usr/bin/env python3
"""Демо-отчёт: собирает CSV с продажами и делает Excel-отчёт.

Без внешних зависимостей — только стандартная библиотека Python.

Запуск:
    python report.py            # создать демо-данные (если нет) и отчёт
    python report.py --reset    # пересоздать демо-данные
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
sys.path.insert(0, str(BASE.parent / "common"))
from xlsx_writer import write_xlsx  # noqa: E402

CATALOG = {
    "Электроника": [("Наушники", 4500), ("Клавиатура", 3200), ("Мышь", 1800)],
    "Одежда": [("Футболка", 1200), ("Куртка", 6500), ("Джинсы", 3500)],
    "Книги": [("Роман", 700), ("Учебник", 1500), ("Комикс", 900)],
    "Дом": [("Лампа", 2200), ("Плед", 1800), ("Кружка", 600)],
}

MONTHS = ["2026-01", "2026-02", "2026-03"]


def make_demo_data(reset: bool = False) -> None:
    DATA.mkdir(exist_ok=True)
    existing = list(DATA.glob("sales_*.csv"))
    if existing and not reset:
        return

    random.seed(42)
    for month in MONTHS:
        path = DATA / f"sales_{month}.csv"
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(["date", "category", "product", "quantity", "price"])
            for day in range(1, 41):
                category = random.choice(list(CATALOG))
                product, price = random.choice(CATALOG[category])
                quantity = random.randint(1, 4)
                writer.writerow(
                    [
                        f"{month}-{random.randint(1, 28):02d}",
                        category,
                        product,
                        quantity,
                        price,
                    ]
                )


def load_rows() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(DATA.glob("sales_*.csv")):
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file, delimiter=";"):
                rows.append(
                    {
                        "date": row["date"],
                        "month": row["date"][:7],
                        "category": row["category"],
                        "product": row["product"],
                        "quantity": int(row["quantity"]),
                        "price": float(row["price"]),
                    }
                )
    return rows


def build_report(rows: list[dict]) -> dict:
    total = sum(row["quantity"] * row["price"] for row in rows)
    orders = len(rows)
    average = total / orders if orders else 0

    by_category: dict[str, float] = defaultdict(float)
    by_month: dict[str, float] = defaultdict(float)
    by_product: dict[str, list] = defaultdict(lambda: [0.0, 0])

    for row in rows:
        revenue = row["quantity"] * row["price"]
        by_category[row["category"]] += revenue
        by_month[row["month"]] += revenue
        by_product[row["product"]][0] += revenue
        by_product[row["product"]][1] += row["quantity"]

    return {
        "total": total,
        "orders": orders,
        "average": average,
        "by_category": dict(sorted(by_category.items(), key=lambda item: -item[1])),
        "by_month": dict(sorted(by_month.items())),
        "top_products": sorted(
            by_product.items(), key=lambda item: -item[1][0]
        )[:5],
    }


def save_report(report: dict) -> Path:
    summary = [
        ["Показатель", "Значение"],
        ["Выручка, ₽", round(report["total"])],
        ["Заказов", report["orders"]],
        ["Средний чек, ₽", round(report["average"])],
    ]

    categories = [["Категория", "Выручка, ₽", "Доля, %"]]
    for name, revenue in report["by_category"].items():
        share = revenue / report["total"] * 100 if report["total"] else 0
        categories.append([name, round(revenue), round(share, 1)])

    months = [["Месяц", "Выручка, ₽"]]
    for month, revenue in report["by_month"].items():
        months.append([month, round(revenue)])

    products = [["Товар", "Выручка, ₽", "Продано, шт."]]
    for name, (revenue, quantity) in report["top_products"]:
        products.append([name, round(revenue), quantity])

    path = BASE / "report.xlsx"
    write_xlsx(
        path,
        [
            {
                "name": "Сводка",
                "rows": summary,
                "widths": [30, 18],
                "header": True,
                "number_cols": {2},
            },
            {
                "name": "По категориям",
                "rows": categories,
                "widths": [25, 18, 12],
                "header": True,
                "number_cols": {2, 3},
            },
            {
                "name": "По месяцам",
                "rows": months,
                "widths": [15, 18],
                "header": True,
                "number_cols": {2},
            },
            {
                "name": "Топ товаров",
                "rows": products,
                "widths": [25, 18, 15],
                "header": True,
                "number_cols": {2, 3},
            },
        ],
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Демо-отчёт по продажам")
    parser.add_argument("--reset", action="store_true", help="пересоздать демо-данные")
    args = parser.parse_args()

    make_demo_data(reset=args.reset)
    rows = load_rows()
    if not rows:
        print("Нет данных в data/. Запустите с --reset.")
        return

    report = build_report(rows)
    path = save_report(report)

    print(f"Заказов: {report['orders']}")
    print(f"Выручка: {report['total']:,.0f} руб.".replace(",", " "))
    print(f"Средний чек: {report['average']:,.0f} руб.".replace(",", " "))
    print(f"Отчёт: {path}")


if __name__ == "__main__":
    main()
