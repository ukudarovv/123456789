# AvtoMat SRM Backend (Django + DRF + SQLite)

## Установка (dev)
```
cd srm_backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata fixtures/seed_dictionaries.json fixtures/seed_settings.json fixtures/seed_catalog.json
python manage.py createsuperuser
python manage.py runserver
```

## Переменные окружения
- SECRET_KEY
- DEBUG
- ALLOWED_HOSTS
- BOT_API_KEY
- TESTS_PRICE_KZT (опц., дублируется в project_setting)
- OWNER_WHATSAPP_PHONE (опц.)
- (bot) BOT_TELEGRAM_TOKEN, BOT_API_BASE_URL

## API
- Dicts: `/api/dicts/*`
- Schools: `/api/schools`, `/api/schools/{id}`
- Instructors: `/api/instructors`
- Settings: `/api/settings`, `/api/settings/whatsapp-templates`
- Leads: POST `/api/leads`, GET `/api/leads/list`, GET `/api/leads/<uuid>`, PATCH `/api/leads/<uuid>/status`, GET `/api/leads/export`
- Analytics: POST `/api/analytics/events`

Bot авторизация: `Authorization: Api-Key <BOT_API_KEY>`

## Роли
- OWNER/ADMIN — видят все.
- SCHOOL_MANAGER — видит только свои лиды (по school_id), может менять статусы.

## Фикстуры
- `fixtures/seed_dictionaries.json` — города, категории, форматы, тариф-планы.
- `fixtures/seed_settings.json` — тестовая цена, номер владельца, WA шаблоны.

