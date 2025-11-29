# User Service (Auth & Profile)

Сервис аутентификации и управления пользователями для системы аренды пауэрбанков.

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

Используется in-memory хранилище (для разработки/тестирования):

- `users` - основная информация о пользователях
- `user_profiles` - профили пользователей
- `user_segments` - сегменты пользователей (STANDARD, PREMIUM, VIP)
- `refresh_tokens` - refresh токены

**Важно:** После перезапуска сервиса все данные теряются.

## Запуск тестов

```bash
pytest tests/ -v
```
