#!/usr/bin/env python3
"""Демо Telegram-бота: приём заявок и уведомления.

Без внешних зависимостей — только стандартная библиотека Python.

Запуск:
    python bot.py --selftest   # проверка без токена и без сети
    python bot.py --demo       # диалог в консоли, без Telegram
    python bot.py              # реальный бот, нужен BOT_TOKEN в .env
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "orders.db"

MAIN_KEYBOARD = {
    "keyboard": [["Оставить заявку"], ["Помощь"]],
    "resize_keyboard": True,
}

STATES: dict[int, dict] = {}


def load_env() -> None:
    env_file = BASE / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def api(token: str, method: str, **params):
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def send(token: str, chat_id: int, text: str, keyboard=None) -> None:
    params = {"chat_id": chat_id, "text": text}
    if keyboard is not None:
        params["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    api(token, "sendMessage", **params)


def init_db() -> None:
    with contextlib.closing(sqlite3.connect(DB_PATH)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                comment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()


def save_order(chat_id: int, name: str, phone: str, comment: str) -> int:
    init_db()
    with contextlib.closing(sqlite3.connect(DB_PATH)) as connection:
        cursor = connection.execute(
            "INSERT INTO orders (chat_id, name, phone, comment) VALUES (?, ?, ?, ?)",
            (chat_id, name, phone, comment),
        )
        connection.commit()
        return int(cursor.lastrowid)


def process_text(chat_id: int, text: str) -> str:
    """Логика бота отдельно от Telegram — так её можно тестировать."""
    state = STATES.get(chat_id)

    if text in ("/start", "Старт"):
        STATES.pop(chat_id, None)
        return "Здравствуйте! Я бот для заявок.\nНажмите «Оставить заявку»."

    if text == "Помощь":
        return (
            "Нажмите «Оставить заявку» — я задам три вопроса "
            "и передам заявку менеджеру."
        )

    if text == "Оставить заявку":
        STATES[chat_id] = {"step": "name"}
        return "Как вас зовут?"

    if state:
        step = state["step"]
        if step == "name":
            state["name"] = text
            state["step"] = "phone"
            return "Укажите телефон или Telegram для связи."
        if step == "phone":
            state["phone"] = text
            state["step"] = "comment"
            return "Коротко опишите задачу (или напишите «нет»)."
        if step == "comment":
            comment = "" if text.lower() == "нет" else text
            order_id = save_order(chat_id, state["name"], state["phone"], comment)
            STATES.pop(chat_id, None)
            return f"Заявка №{order_id} принята. Мы свяжемся с вами."

    return "Не понял. Нажмите «Оставить заявку» или «Помощь»."


def run_bot(token: str, admin_id: int | None) -> None:
    init_db()
    offset = 0
    print("Бот запущен. Ctrl+C — остановка.")
    while True:
        try:
            data = api(token, "getUpdates", offset=offset, timeout=25)
        except Exception as error:  # сеть может отвалиться — не падаем
            print("Ошибка сети:", error)
            time.sleep(3)
            continue

        for update in data.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message") or {}
            chat_id = message.get("chat", {}).get("id")
            text = (message.get("text") or "").strip()
            if not chat_id or not text:
                continue

            reply = process_text(chat_id, text)
            send(token, chat_id, reply, MAIN_KEYBOARD)

            if admin_id and reply.startswith("Заявка №"):
                send(
                    token,
                    admin_id,
                    f"Новая заявка №{reply.split('№')[1].split()[0]} от {chat_id}",
                )


def selftest() -> None:
    global DB_PATH
    DB_PATH = BASE / "orders_test.db"
    if DB_PATH.exists():
        DB_PATH.unlink()

    init_db()
    chat_id = 1
    script = [
        "/start",
        "Оставить заявку",
        "Андрей",
        "+7 900 000-00-00",
        "Нужен Telegram-бот для заявок",
    ]
    for text in script:
        print(f"Вы: {text}")
        print(f"Бот: {process_text(chat_id, text)}")

    with contextlib.closing(sqlite3.connect(DB_PATH)) as connection:
        rows = connection.execute(
            "SELECT name, phone, comment FROM orders"
        ).fetchall()

    expected = [("Андрей", "+7 900 000-00-00", "Нужен Telegram-бот для заявок")]
    if rows != expected:
        raise AssertionError(f"Неожиданные данные в базе: {rows}")

    DB_PATH.unlink()
    print("\nOK: сценарий пройден, заявка сохранена в SQLite.")


def demo() -> None:
    print("Демо без Telegram. Команды: /start, Оставить заявку, Помощь, выход.")
    chat_id = 0
    while True:
        try:
            text = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in ("выход", "exit", "q"):
            break
        print("Бот:", process_text(chat_id, text))


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="Демо Telegram-бота")
    parser.add_argument("--selftest", action="store_true", help="проверка без токена")
    parser.add_argument("--demo", action="store_true", help="диалог в консоли")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return
    if args.demo:
        demo()
        return

    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        print("Нет BOT_TOKEN. Создайте .env по образцу .env.example.")
        sys.exit(1)

    admin_raw = os.environ.get("ADMIN_ID", "").strip()
    admin_id = int(admin_raw) if admin_raw.isdigit() else None
    run_bot(token, admin_id)


if __name__ == "__main__":
    main()
