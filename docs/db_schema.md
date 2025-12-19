# AvtoMat MVP — Схема БД (SQLite, Django)

Стек: Django/DRF + SQLite для MVP. JSON-поля — `models.JSONField` (SQLite сохраняет как TEXT). Индексы GIN недоступны; используем обычные btree и уникальные ограничения.

## 1. Справочники

### 1.1 `dict_city`
- `id` PK
- `name_ru` varchar not null
- `name_kz` varchar not null
- `is_active` bool default true
- `sort_order` int default 0
- Индексы: `(is_active, sort_order)`

### 1.2 `dict_category`
- `id` PK
- `code` varchar(10) unique not null (например, "B")
- `name_ru` varchar not null
- `name_kz` varchar not null
- `is_active` bool default true
- `sort_order` int default 0
- Индексы: `(is_active, sort_order)`

### 1.3 `dict_training_format`
- `id` PK
- `name_ru` varchar not null
- `name_kz` varchar not null
- `is_active` bool default true
- `sort_order` int default 0

### 1.4 `dict_tariff_plan`
- `id` PK
- `code` varchar(20) unique not null (`BASIC|STANDARD|PREMIUM`)
- `name_ru` varchar not null
- `name_kz` varchar not null
- `sort_order` int default 0
- `is_active` bool default true

## 2. Каталог автошкол и тарифов

### 2.1 `school`
- `id` PK
- `city_id` FK→dict_city not null
- `name_ru` varchar not null
- `name_kz` varchar not null
- `rating` numeric(2,1) default 0.0
- `trust_index` int default 0 (шкала 0–100)
- `address_ru` varchar not null
- `address_kz` varchar not null
- `nearest_intake_date` date null
- `nearest_intake_text_ru` varchar null
- `nearest_intake_text_kz` varchar null
- `contact_phone` varchar null
- `whatsapp_phone` varchar null
- `is_active` bool default true
- `created_at` timestamp
- `updated_at` timestamp
- Индексы: `(city_id, is_active)`, `(rating)`

### 2.2 `school_tariff`
- `id` PK
- `school_id` FK→school not null
- `tariff_plan_id` FK→dict_tariff_plan not null
- `price_kzt` int not null
- `currency` varchar(3) default "KZT"
- `description_ru` text null
- `description_kz` text null
- `is_active` bool default true
- Ограничение: unique `(school_id, tariff_plan_id)`
- Индексы: `(school_id, is_active)`

## 3. Каталог инструкторов

### 3.1 `instructor`
- `id` PK
- `city_id` FK→dict_city not null
- `display_name` varchar not null
- `gender` varchar(1) not null (`M|F`)
- `gearbox` varchar(10) not null (`AT|MT`)
- `price_kzt` int not null
- `rating` numeric(2,1) default 0.0
- `bio_ru` text null
- `bio_kz` text null
- `is_active` bool default true
- `created_at` timestamp
- `updated_at` timestamp
- Индексы: `(city_id, gearbox, gender, is_active)`, `(rating)`

## 4. Пользователи Telegram (бот)

### 4.1 `bot_user`
- `id` PK
- `telegram_user_id` bigint unique not null
- `username` varchar null
- `first_name` varchar null
- `last_name` varchar null
- `language` varchar(2) not null (`RU|KZ`)
- `phone` varchar null
- `created_at` timestamp
- `updated_at` timestamp
- `last_seen_at` timestamp null
- Индекс: unique `(telegram_user_id)`

## 5. Лиды и статусы

### 5.1 `lead`
- `id` PK (UUID рекомендован, в SQLite хранится TEXT)
- `type` varchar(20) not null (`SCHOOL|INSTRUCTOR|TESTS`)
- `status` varchar(20) not null (`NEW|CONFIRMED|PAID|DONE|CANCELED`)
- `bot_user_id` FK→bot_user null
- `language` varchar(2) not null
- `main_intent` varchar(30) null (`NO_LICENSE|REFRESH|CERT_NOT_PASSED`)

**Поля автошкол:**
- `city_id` FK→dict_city null
- `category_id` FK→dict_category null
- `training_format_id` FK→dict_training_format null
- `school_id` FK→school null
- `tariff_plan_id` FK→dict_tariff_plan null
- `tariff_price_kzt` int null (фиксируем цену на момент заявки)

**Поля инструкторов:**
- `instructor_id` FK→instructor null
- `gearbox` varchar(10) null (дублируем выбор)
- `preferred_instructor_gender` varchar(1) null
- `has_driver_license` bool null

**Контакты:**
- `name` varchar not null
- `phone` varchar not null
- `iin` varchar(12) null (TESTS)
- `whatsapp` varchar null (TESTS)
- `email` varchar null (TESTS)

**Служебные:**
- `source` varchar default "telegram_bot"
- `utm_source` varchar null
- `utm_campaign` varchar null
- `utm_medium` varchar null
- `created_at` timestamp
- `updated_at` timestamp

**Индексы:**
- `(status, created_at)`
- `(type, created_at)`
- `(school_id, status, created_at)`
- `(city_id, created_at)`
- `(phone)`

### 5.2 `lead_status_history`
- `id` PK
- `lead_id` FK→lead not null
- `old_status` varchar(20) null
- `new_status` varchar(20) not null
- `changed_by_user_id` FK→srm_user null
- `changed_at` timestamp
- `note` text null
- Индекс: `(lead_id, changed_at)`

## 6. Аналитика

### 6.1 `analytics_event`
- `id` PK
- `bot_user_id` FK→bot_user null
- `lead_id` FK→lead null
- `event_name` varchar(50) not null
- `payload` JSONField null (TEXT in SQLite)
- `created_at` timestamp
- Индексы: `(event_name, created_at)`, `(bot_user_id, created_at)`, `(lead_id, created_at)`

## 7. Настройки и шаблоны WhatsApp

### 7.1 `project_setting`
- `id` PK
- `key` varchar(100) unique not null (например, TESTS_PRICE_KZT, OWNER_WHATSAPP_PHONE)
- `value_json` JSONField not null
- `updated_at` timestamp

### 7.2 `whatsapp_template`
- `id` PK
- `scope` varchar(30) not null (`SCHOOL_CLIENT_MESSAGE|TESTS_OWNER_MESSAGE`)
- `language` varchar(2) not null (RU/KZ)
- `template_text` text not null
- `is_active` bool default true
- Ограничение: unique `(scope, language)`

## 8. Пользователи SRM

### 8.1 `srm_user`
- `id` PK
- `email` varchar unique
- `password_hash` (или Django auth)
- `role` varchar(20) not null (`OWNER|ADMIN|SCHOOL_MANAGER`)
- `school_id` FK→school null (обязательно при role = SCHOOL_MANAGER)
- `is_active` bool default true
- `created_at`, `updated_at`

## Мини-правила
1. В `lead` фиксируем цену тарифа (`tariff_price_kzt`) при создании.
2. Для `TESTS` обязательны `iin`, `whatsapp`, `email` на уровне валидации API.
3. Телефон хранить в нормализованном виде (+7XXXXXXXXXX) для поиска.

