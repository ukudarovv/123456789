# AvtoMat MVP — API контракты (Django/DRF, SQLite)

Авторизация:
- Bot → SRM: header `Authorization: Api-Key <token>` (service token).
- SRM UI → API: session/JWT (вне рамок бота).

Базовый формат ошибок (DRF):
```json
{"detail": "error message"}
```

## 1. Справочники

### GET /api/dicts/cities
Параметры: `is_active` (bool, опц).
Ответ:
```json
[{"id":1,"name_ru":"Алматы","name_kz":"Алматы"}]
```

### GET /api/dicts/categories
Ответ: `id, code, name_ru, name_kz`

### GET /api/dicts/training-formats
Ответ: `id, name_ru, name_kz`

### GET /api/dicts/tariff-plans
Ответ: `id, code, name_ru, name_kz`

## 2. Каталог автошкол

### GET /api/schools
Параметры:
- `city_id` (int, обязателен для выдачи)
- `category_id` (опц)
- `training_format_id` (опц)
- `active_only` (bool, default true)
Ответ (сокращённый):
```json
[{
  "id": 10,
  "name": {"ru": "Автошкола 1", "kz": "Автошкола 1"},
  "city_id": 1,
  "rating": 4.7,
  "trust_index": 85,
  "nearest_intake": {"date": "2025-01-15", "text_ru": "каждый понедельник", "text_kz": null},
  "address": {"ru": "ул. Абая, 10", "kz": "Абая к-сі, 10"}
}]
```

### GET /api/schools/{id}
Ответ (детали + тарифы):
```json
{
  "id": 10,
  "name": {"ru": "Автошкола 1", "kz": "Автошкола 1"},
  "city_id": 1,
  "rating": 4.7,
  "trust_index": 85,
  "address": {"ru": "ул. Абая, 10", "kz": "Абая к-сі, 10"},
  "nearest_intake": {"date": "2025-01-15", "text_ru": "каждый понедельник", "text_kz": null},
  "contact_phone": "+77001234567",
  "whatsapp_phone": "+77001234567",
  "tariffs": [
    {"tariff_plan_id": 1, "code": "BASIC", "price_kzt": 60000, "description_ru": "10 занятий", "description_kz": null}
  ]
}
```

## 3. Каталог инструкторов

### GET /api/instructors
Параметры:
- `city_id` (обяз)
- `gearbox` (`AT|MT`, опц)
- `gender` (`M|F`, опц)
- `active_only` (bool, default true)
Ответ:
```json
[{
  "id": 5,
  "display_name": "Аман",
  "gender": "M",
  "gearbox": "AT",
  "price_kzt": 9000,
  "rating": 4.9,
  "bio": {"ru": null, "kz": null}
}]
```

## 4. Настройки

### GET /api/settings
Ответ:
```json
{
  "tests_price_kzt": 15000,
  "owner_whatsapp": "+77001234567"
}
```

## 5. Лиды

### POST /api/leads
Создание лида для всех типов.
Тело (общие поля):
```json
{
  "type": "SCHOOL",
  "language": "RU",
  "main_intent": "NO_LICENSE",
  "bot_user": {
    "telegram_user_id": 123456,
    "username": "ivan",
    "language": "RU",
    "phone": "+77001112233"
  },
  "contact": {"name": "Иван", "phone": "+77001112233"},
  "source": "telegram_bot",
  "utm": {"source": null, "campaign": null, "medium": null},
  "payload": { }  // см. ниже по типам
}
```

#### 5.1 Тип SCHOOL
`payload`:
```json
{
  "city_id": 1,
  "category_id": 2,
  "training_format_id": 1,
  "school_id": 10,
  "tariff_plan_id": 1,
  "tariff_price_kzt": 60000
}
```

#### 5.2 Тип INSTRUCTOR
`payload`:
```json
{
  "city_id": 1,
  "gearbox": "AT",
  "preferred_instructor_gender": "M",
  "has_driver_license": true,
  "instructor_id": 5
}
```

#### 5.3 Тип TESTS
`payload`:
```json
{
  "city_id": null,
  "iin": "950101123456",
  "whatsapp": "+77001234567",
  "email": "test@example.com"
}
```

Ответ 201:
```json
{"id": "uuid", "status": "NEW"}
```

Валидация:
- PHONE: формат KZ (+7, 10–11 цифр).
- IIN: 12 цифр (обязательно для TESTS).
- Email: стандартный формат (обязательно для TESTS).
- Для SCHOOL: `city_id`, `category_id`, `training_format_id`, `school_id` обязательны; `tariff_price_kzt` фиксируется.
- Для INSTRUCTOR: `city_id`, `gearbox`, `instructor_id` обязательны.

## 6. SRM — заявки (UI/админ)

### GET /api/leads
Фильтры: `status`, `type`, `city_id`, `school_id`, `created_from`, `created_to`, `phone`.
Права: `SCHOOL_MANAGER` видит только по своему `school_id`.

### PATCH /api/leads/{id}
Тело:
```json
{"status": "CONFIRMED", "manager_comment": "Созвон назначен"}
```
Действия:
- Меняет статус, пишет запись в `lead_status_history` (changed_by_user_id).

### GET /api/leads/{id}
Детали + история статусов.

### GET /api/leads/export?format=csv
Фильтры аналогичны `/api/leads`; ответ — файл CSV.

## 7. Аналитика

### POST /api/analytics/events
Тело:
```json
{
  "bot_user_id": 1,
  "lead_id": "uuid-or-null",
  "event_name": "language_selected",
  "payload": {"language": "RU"},
  "created_at": "2025-01-10T12:00:00Z"  // опц, иначе серверное время
}
```
Ответ: 201.

## 8. Аутентификация SRM UI
- Использовать Django auth/JWT (не детализируется здесь).
- Роли: `OWNER|ADMIN|SCHOOL_MANAGER`.
- Доступы: менеджер видит только свои лиды/школу.

