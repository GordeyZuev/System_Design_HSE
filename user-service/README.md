# User Service (Auth & Profile)

Сервис аутентификации и управления пользователями для системы аренды пауэрбанков.

**Статус:** Прототип с in-memory хранилищем (для демонстрации/разработки)

## Быстрый старт

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск сервиса
uvicorn app.main:app --host 0.0.0.0 --port 8081
```

## API Эндпоинты

### Публичные (через Gateway)

- `POST /auth/login` - Вход пользователя
  - Request: `{email, password}`
  - Response: `{access_token, refresh_token, user_id}`

- `POST /auth/refresh` - Обновление токена
  - Request: `{refresh_token}`
  - Response: `{access_token, refresh_token}`

### Internal (для других сервисов)

- `GET /api/v1/users/{user_id}` - Получение информации о пользователе
  - Response: `{user_id, email, segment, status, phone}`

- `POST /api/v1/jwt/validate` - Валидация JWT токена
  - Request: `{token}`
  - Response: `{valid, user_id?, segment?, roles?}`

### Dev (для разработки)

- `POST /dev/create-test-user` - Создание тестового пользователя
  - Response: `{message, user_id, email, password, segment}`

### Мониторинг

- `GET /health` - Health check
- `GET /metrics` - Prometheus метрики

## Тестирование

### Создание тестового пользователя

```bash
curl -X POST http://localhost:8081/dev/create-test-user
```

Создаст пользователя:
- Email: `test@example.com`
- Password: `testpassword123`
- Segment: `STANDARD`

### Примеры запросов

**Логин:**
```bash
curl -X POST http://localhost:8081/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpassword123"}'
```

**Получение информации о пользователе:**
```bash
curl http://localhost:8081/api/v1/users/{user_id}
```

**Валидация JWT:**
```bash
curl -X POST http://localhost:8081/api/v1/jwt/validate \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_TOKEN"}'
```

## Структура проекта

```
user-service/
├── app/
│   ├── api/              # HTTP слой (routes, dependencies, monitoring)
│   ├── domain/           # Доменные модели и исключения
│   ├── services/         # Бизнес-логика (auth, user)
│   └── infrastructure/   # Репозитории и JWT handler
├── tests/                # Тесты
└── requirements.txt
```

## Конфигурация

Переменные окружения:

- `JWT_SECRET` - Секретный ключ для JWT (обязательно в production)
- `APP_PORT` - Порт приложения (по умолчанию 8081)
- `LOG_LEVEL` - Уровень логирования (по умолчанию INFO)

## Хранилище

**Тип БД:** In-memory (для прототипа/демонстрации)

**Структуры данных:**
- `users(user_id, email, phone, password_hash, status, created_at)` - основная информация о пользователях
- `user_profiles(user_id, name, extra_metadata_json)` - профили пользователей
- `user_segments(user_id, segment, updated_at)` - сегменты пользователей (STANDARD, PREMIUM, VIP)
- `refresh_tokens(token_id, user_id, expires_at, revoked)` - refresh токены

**Особенности:**
- Простые in-memory словари для быстрого прототипирования
- Данные не персистентны (теряются при перезапуске)
- Для production потребуется миграция на PostgreSQL

## Запуск тестов

```bash
pytest tests/ -v
```
