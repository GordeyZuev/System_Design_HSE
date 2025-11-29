# Rental Command Service


## Описание

Rental Command Service:
- Управляет офферами и арендой
- Контролирует свежесть оффера
- Интеграция с Payments Adapter, Stations Adapter, Offer & Pricing

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

1. **Domain** — доменные модели и исключения
2. **Services** — бизнес-логика начала и окончания аренды 
3. **Infrastructure** — клиенты внешних сервисов с кэшированием
4. **API** — REST endpoints через FastAPI

## Быстрый старт

### Требования

- Python 3.12+
- pip или poetry

### Установка

```bash
# Перейти в директорию проекта
cd rental-command-service

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
python main.py

# Или через uvicorn напрямую
uvicorn app.main:app --reload --port 8002
```

Сервис будет доступен по адресу: **http://localhost:8002**

## API Endpoints

### Основные

- `GET /` — информация о сервисе
- `GET /health` — health check

### Rentals

- `POST /internal/rentals/start` — создать оффер
- `POST /internal/rentals/{rental_id}/finish` — окончание аренды

### Примеры запросов

#### Старт аренды

```bash
curl -X POST "http://localhost:8000/internal/rentals/start" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
        "offer_id": "123e4567-e89b-12d3-a456-426614174000"
      }'
```

Ответ:
```json
{
  "rental_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "started_at": "2025-11-29T12:34:56.789Z",
  "status": "ACTIVE"
}
```

#### Окончание аренды

```bash
curl -X POST "http://localhost:8000/internal/rentals/123e4567-e89b-12d3-a456-426614174000/finish" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
        "station_id": "station_42"
      }'
```
Ответ:

```json
{
  "rental_id": "123e4567-e89b-12d3-a456-426614174000",
  "finished_at": "2025-11-29T14:30:00Z",
  "final_cost": 12.50,
  "status": "finished"
}
```

## Основные фичи

- **Начало аренды**
  - Валидация офферов (статус, принадлежность, срок действия)
  - Предотвращение нескольких активных аренд у одного пользователя
  - Резервирование пауэрбэнка через StationsAdapter
  - Сохранение аренды с тарифом и версией тарифа
  - Генерация события `rental_started` 

- **Завершение аренды**
  - Проверка существования аренды и соответствия пользователя
  - Предотвращение повторного завершения аренды
  - Расчёт итоговой стоимости по тарифу и времени аренды
  - Возврат устройства на станцию через StationsAdapter
  - Обновление статуса аренды и генерация события `rental_finished`
  - Создание записи в outbox для асинхронной оплаты

- **Интеграция с внешними сервисами**
  - Валидация офферов через `OfferClient`
  - Операции со станциями через `StationsAdapter`
  - Асинхронная обработка платежей через паттерн Outbox

- **Шардированная БД**

- **Гибкая работа с тарифами**
  - Хранение и использование `tariff_snapshot` для расчёта стоимости
  - Поддержка начального тарифа и тарифа за минуту




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



## Разработка

### Тестирование

```bash
 python3 -m pytest tests/
```

### Линтинг

```bash
flake8 app/
```

## ADR Reference

Реализация соответствует **ADR-0001** (Команда 7):


## Автор

Команда 7 — Система аренды пауэрбанков (HSE)

## Лицензия

MIT

