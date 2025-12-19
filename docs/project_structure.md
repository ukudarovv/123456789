# AvtoMat MVP — структура проекта (aiogram + Django/DRF + SQLite)

## Корень репозитория
- `bot/` — Telegram-бот (aiogram)
- `srm_backend/` — Django/DRF backend + admin
- `docs/` — спецификации (схема БД, API, бэклог)
- `.env.example` — переменные окружения
- `Makefile`/`taskfile` (опц.) — быстрые команды
- `docker-compose.yml` (опц. для dev; SQLite не требует контейнера)

## bot/
- `app.py` — точка входа (polling/webhook)
- `config.py` — загрузка env (API_KEY, BASE_URL, BOT_TOKEN, LANGUAGE_DEFAULT)
- `i18n/` — словари RU/KZ (json/py)
- `keyboards/` — Reply/Inline keyboards
- `handlers/` — FSM состояния по потокам (schools, instructors, tests, common)
- `states/` — классы FSM
- `services/` — клиенты к SRM API (requests/httpx), генерация wa.me ссылок
- `models/` — pydantic-схемы для запросов к API
- `middlewares/` — логирование, анти-флуд (опц.)
- `analytics/` — отправка событий (`analytics_event`)
- `utils/` — валидация телефона/ИИН/email, форматирование
- `tests/` — unit/flow tests (опц.)

## srm_backend/
- `manage.py`
- `config/settings.py` — SQLite DSN, DRF, CORS, auth
- `config/urls.py`
- `requirements.txt` / `pyproject.toml`

### Приложения
- `dictionaries/` — модели/сериализаторы/вью для dict_city/category/training_format/tariff_plan
- `catalog/` — school, school_tariff, instructor
- `accounts/` — srm_user (либо Django auth + profile), роли/permissions
- `botusers/` — bot_user модель/админка
- `leads/` — lead, lead_status_history, API, фильтры, экспорт CSV
- `analytics/` — analytics_event
- `settings_app/` — project_setting, whatsapp_template

### Важные файлы внутри приложений
- `models.py` — модели по схеме
- `serializers.py` — DRF сериализаторы
- `views.py` / `api.py` — API эндпоинты
- `urls.py`
- `admin.py` — кастомизация Django Admin (фильтры, search, ограничение видимости)
- `permissions.py` — Role-based доступы
- `filters.py` — django-filter для списков
- `services/export.py` — CSV экспорт для лидов
- `migrations/` — авто миграции

## Env переменные (пример)
- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `BOT_API_KEY` (service token для бота)
- `BOT_BASE_URL` (URL SRM API)
- `BOT_TELEGRAM_TOKEN`
- `DEFAULT_LANGUAGE=RU`
- `OWNER_WHATSAPP_PHONE`
- `TESTS_PRICE_KZT`

## Запуск dev (SQLite)
```bash
cd srm_backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata seed_dictionaries.json   # города/категории/форматы/тарифы
python manage.py runserver
```
Бот:
```bash
cd bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Примечания по SQLite
- JSONField хранится в TEXT; сложные фильтры по JSON недоступны — использовать простые поля.
- Конкурентность записи ограничена: для MVP/малых нагрузок ок; для прод — миграция на Postgres.

