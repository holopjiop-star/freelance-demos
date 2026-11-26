# freelance-demos

Три небольших проекта на чистом Python — без внешних зависимостей.
Демонстрируют навыки, которые нужны для заказов на фрилансе:
Telegram-боты, парсинг сайтов и автоматизация отчётов в Excel.

## Проекты

| Папка | Что делает | Стек |
|---|---|---|
| `telegram-bot/` | Бот принимает заявки, сохраняет в SQLite, уведомляет админа | Python, `urllib`, `sqlite3` |
| `site-parser/` | Собирает данные с сайта, выгружает в CSV и XLSX | Python, `html.parser`, `csv` |
| `excel-report/` | Собирает CSV, считает сводку, делает Excel с 4 листами | Python, `csv`, собственный XLSX-writer |

## Требования

- Python 3.10+
- Никаких `pip install` — только стандартная библиотека.

## Быстрый запуск

```bash
# 1. Telegram-бот: проверка логики без токена
python telegram-bot/bot.py --selftest

# 2. Парсер: демо-данные без интернета
python site-parser/parser.py --demo

# 3. Отчёт: создаёт данные и report.xlsx
python excel-report/report.py
```

## Telegram-бот: реальный запуск

1. Получите токен у [@BotFather](https://t.me/BotFather).
2. Скопируйте `telegram-bot/.env.example` в `telegram-bot/.env`.
3. Впишите `BOT_TOKEN` и свой `ADMIN_ID` (узнать можно у [@userinfobot](https://t.me/userinfobot)).
4. Запустите:

```bash
python telegram-bot/bot.py
```

## Структура

```
freelance-demos/
├── common/
│   └── xlsx_writer.py      # генератор .xlsx без openpyxl
├── telegram-bot/
│   ├── bot.py
│   └── .env.example
├── site-parser/
│   └── parser.py
└── excel-report/
    └── report.py
```

## Что показывает каждое демо

- **telegram-bot** — работа с API, long polling, состояния диалога, SQLite, обработка ошибок сети.
- **site-parser** — HTTP-запросы, разбор HTML, пагинация, выгрузка в CSV/Excel.
- **excel-report** — чтение CSV, агрегация данных, генерация XLSX с форматированием.

## Ограничения

- Демо, а не production: нет тестов, логирования в файл и конфигурации через переменные окружения (кроме бота).
- Парсер настроен на учебный сайт `quotes.toscrape.com`; для другого сайта меняется парсер.
- XLSX-writer поддерживает только базовое форматирование: заголовки, ширины, числовой формат.
