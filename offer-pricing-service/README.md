# Offer & Pricing Service

**Сервис управления офферами и прайсингом** для системы аренды пауэрбанков (Команда 7).

## Описание

Offer & Pricing Service отвечает за:
- ✅ Создание офферов с расчётом тарифов
- ✅ Кэширование тарифов (LRU + TTL)
- ✅ Валидацию офферов при старте аренды
- ✅ Greedy pricing при недоступности User Service
- ✅ Интеграцию с User, Tariff, Config сервисами

## Архитектура

Проект следует принципам **чистой архитектуры**:

```
app/
├── domain/           # Бизнес-логика, модели, исключения
├── services/         # Сервисный слой (use-cases)
├── infrastructure/   # Внешние зависимости (клиенты, репозитории)
└── api/             # HTTP API (FastAPI)
```

### Слои

1. **Domain** — доменные модели (`Offer`, `TariffInfo`) и исключения
2. **Services** — бизнес-логика создания офферов и прайсинга
3. **Infrastructure** — клиенты внешних сервисов с кэшированием
4. **API** — REST endpoints через FastAPI

## Быстрый старт

### Требования

- Python 3.11+
- pip или poetry

### Установка

```bash
# Перейти в директорию проекта
cd offer-pricing-service

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Скопировать конфигурацию
cp .env.example .env
```

### Запуск

```bash
# Простой запуск
python run_dev.py

# Или через uvicorn напрямую
uvicorn app.main:app --reload --port 8001
```

Сервис будет доступен по адресу: **http://localhost:8001**

## API Endpoints

### Основные

- `GET /` — информация о сервисе
- `GET /health` — health check
- `GET /metrics` — Prometheus метрики

### Offers

- `POST /internal/offers` — создать оффер
- `GET /internal/offers/{offer_id}` — получить оффер
- `POST /internal/offers/{offer_id}/validate` — валидировать и использовать оффер

### Примеры запросов

#### Создание оффера

```bash
curl -X POST http://localhost:8001/internal/offers \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "station_id": "station-001",
    "user_segment": "STANDARD"
  }'
```

Ответ:
```json
{
  "offer_id": "123e4567-e89b-12d3-a456-426614174000",
  "expires_at": "2024-11-21T15:00:00Z",
  "tariff_details": {
    "tariff_id": "tariff-001",
    "base_rate": 5.0,
    "segment_multiplier": 1.0,
    "currency": "RUB"
  },
  "estimated_rate_per_minute": 5.0,
  "currency": "RUB"
}
```

#### Получение оффера

```bash
curl http://localhost:8001/internal/offers/123e4567-e89b-12d3-a456-426614174000
```

#### Валидация оффера (для Rental Command Service)

```bash
curl -X POST "http://localhost:8001/internal/offers/123e4567-e89b-12d3-a456-426614174000/validate?user_id=550e8400-e29b-41d4-a716-446655440000"
```

## Ключевые фичи

### 1. Кэширование тарифов (LRU + TTL)

```python
# TariffClient с LRU-кэшем
- TTL: 10 минут (конфигурируется)
- Размер: 1000 записей
- При протухании TTL → ошибка (не используем устаревшие тарифы)
```

### 2. Greedy Pricing (Fallback)

При недоступности User Service:
- Автоматически применяется "жадный" тариф
- Максимальная ставка × множитель (1.5x по умолчанию)
- Локальная деградация без проброса ошибки

### 3. Валидация офферов

При старте аренды проверяется:
- Срок действия (`expires_at`)
- Статус оффера (`ACTIVE`)
- Владелец оффера (`user_id`)

### 4. Мониторинг

Prometheus метрики:
- `offer_created_total` — счётчик созданных офферов
- `offer_creation_duration_seconds` — время создания оффера
- `offer_validate_total` — счётчик валидаций

## Конфигурация

Переменные окружения (`.env`):

```bash
# Внешние сервисы
USER_SERVICE_URL=http://localhost:8000
TARIFF_SERVICE_URL=http://localhost:8002
CONFIG_SERVICE_URL=http://localhost:8003

# Таймауты
USER_SERVICE_TIMEOUT=2.0
TARIFF_SERVICE_TIMEOUT=3.0
CONFIG_SERVICE_TIMEOUT=1.0

# Кэш
TARIFF_CACHE_TTL=600           # 10 минут
CONFIG_CACHE_TTL=60            # 1 минута

# Оффер
OFFER_DEFAULT_TTL=300          # 5 минут
GREEDY_PRICING_MULTIPLIER=1.5
```

## Хранилище данных

**Production & Development:** PostgreSQL с миграциями Alembic

**Testing:** PostgreSQL репозиторий с SQLite in-memory для быстрых тестов

### База данных PostgreSQL

```bash
# Применить миграции
alembic upgrade head

# Создать новую миграцию
alembic revision --autogenerate -m "Description"

# Откат миграции
alembic downgrade -1
```

**Схема БД:**
- `offers` - основная таблица офферов
- `offer_audit` - audit log событий

## Интеграция с другими сервисами

### User Service
- Получение сегмента пользователя
- Fallback на greedy pricing при недоступности

### Tariff Service
- Получение тарифной информации
- LRU-кэш с TTL

### Config Service
- Получение конфигурации
- Auto-refresh кэш с TTL

### Rental Command Service
- Вызывает `/internal/offers/{id}/validate` при старте аренды
- Получает `tariff_snapshot` для расчёта стоимости

## Структура проекта

```
offer-pricing-service/
├── app/
│   ├── api/                    # API endpoints
│   │   ├── routes.py          # Offer endpoints
│   │   ├── monitoring.py      # Health & metrics
│   │   └── dependencies.py    # DI контейнер
│   ├── domain/                # Доменный слой
│   │   ├── models.py          # Модели (Offer, TariffInfo)
│   │   └── exceptions.py      # Исключения
│   ├── services/              # Бизнес-логика
│   │   └── offer_service.py   # OfferService
│   ├── infrastructure/        # Внешние зависимости
│   │   ├── clients/           # HTTP клиенты
│   │   │   ├── tariff_client.py
│   │   │   ├── user_client.py
│   │   │   └── config_client.py
│   │   ├── repositories.py    # Интерфейс репозитория
│   │   └── repositories_inmemory.py  # In-memory реализация
│   ├── config.py              # Настройки
│   └── main.py                # Точка входа
├── requirements.txt           # Зависимости
├── run_dev.py                 # Скрипт запуска
├── .env.example               # Пример конфигурации
└── README.md                  # Этот файл
```

## Разработка

### Локальный запуск

```bash
# Установить зависимости
pip install -r requirements.txt

# Применить миграции (для PostgreSQL)
alembic upgrade head

# Запустить сервис
uvicorn app.main:app --reload --port 8001
```

### Docker

```bash
# Собрать образ
docker build -t offer-pricing-service .

# Запустить контейнер
docker run -p 8001:8001 \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@host:5432/offers_db \
  -e USE_POSTGRES=true \
  offer-pricing-service
```

### Форматирование кода

```bash
black app/
```

### Тестирование

```bash
# Запустить все тесты
python3 -m pytest tests/

# Тесты с покрытием
python3 -m pytest tests/ --cov=app --cov-report=html

# Только unit-тесты (изолированные слои)
python3 -m pytest tests/test_repositories.py tests/test_offer_service.py -v

# Интеграционные тесты API
python3 -m pytest tests/test_api.py -v
```

### Архитектура тестов

Тесты организованы по слоям для изоляции:

- **test_repositories.py** - тесты PostgreSQL репозитория с SQLite in-memory
- **test_offer_service.py** - тесты бизнес-логики (service layer)
- **test_api.py** - тесты API endpoints (API layer)

Все слои тестируются изолированно с использованием моков и fixtures.
Репозиторий тестируется с реальной БД (SQLite) для проверки SQL-запросов.

### Линтинг

```bash
flake8 app/
```

## ADR Reference

Реализация соответствует **ADR-0001** (Команда 7):

 Микросервисная архитектура  
Чистая архитектура (Domain, Services, Infrastructure, API)  
Greedy pricing при недоступности User Service  
LRU + TTL кэш для тарифов  
Контроль свежести офферов (expires_at, tariff_version)  
Prometheus метрики  

## Автор

Команда 7 — Система аренды пауэрбанков (HSE)

## Лицензия

MIT

