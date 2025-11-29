# Поток обработки оффера в Offer & Pricing Service

## 1. Создание оффера (Create Offer Flow)

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /internal/offers
       │ {user_id, station_id, segment?}
       ▼
┌─────────────────────────────────────────────────┐
│           API Layer (routes.py)                 │
│  ┌───────────────────────────────────────────┐  │
│  │ create_offer(request, service)            │  │
│  │  - Принимает CreateOfferRequest          │  │
│  │  - Вызывает OfferService                 │  │
│  │  - Обрабатывает исключения                │  │
│  └───────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│        Service Layer (offer_service.py)         │
│  ┌───────────────────────────────────────────┐  │
│  │ create_offer(request)                     │  │
│  │  1. Получить config (ConfigClient)       │  │
│  │  2. Определить user_segment              │  │
│  │     ├─ Если не передан → UserClient      │  │
│  │     └─ Если UserService недоступен →     │  │
│  │        GREEDY PRICING FALLBACK            │  │
│  │  3. Получить тариф (TariffClient)        │  │
│  │     ├─ Обычный тариф для сегмента        │  │
│  │     └─ Greedy тариф (макс. ставка×1.5)   │  │
│  │  4. Создать tariff_snapshot              │  │
│  │  5. Сохранить оффер (Repository)         │  │
│  └───────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────┘
                  │
        ┌─────────┼─────────┬─────────┐
        ▼         ▼         ▼         ▼
    ┌────────┐┌────────┐┌────────┐┌────────────┐
    │ User   ││ Tariff ││ Config ││ PostgreSQL │
    │ Client ││ Client ││ Client ││ Repository │
    └────────┘└────────┘└────────┘└────────────┘
        │         │         │         │
        │ GET     │ GET     │ GET     │ INSERT
        │ /users  │ /tariffs│ /config │ offers
        │         │ +cache  │ +cache  │
        ▼         ▼         ▼         ▼
    External   External   External   Database
    Service    Service    Service    (offers)


Результат:
{
  "offer_id": "uuid",
  "expires_at": "2024-11-29T15:00:00Z",
  "tariff_details": {...},
  "estimated_rate_per_minute": 5.0,
  "currency": "RUB"
}
```

## 2. Валидация и использование оффера (Validate & Use Flow)

```
┌──────────────────┐
│ Rental Command   │
│    Service       │
└────────┬─────────┘
         │ POST /internal/offers/{offer_id}/validate
         │ ?user_id=uuid
         ▼
┌─────────────────────────────────────────────────┐
│           API Layer (routes.py)                 │
│  ┌───────────────────────────────────────────┐  │
│  │ validate_offer(offer_id, user_id)         │  │
│  │  - Проверяет параметры                    │  │
│  │  - Вызывает OfferService                 │  │
│  │  - Возвращает tariff_snapshot             │  │
│  └───────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│        Service Layer (offer_service.py)         │
│  ┌───────────────────────────────────────────┐  │
│  │ validate_and_use_offer(offer_id, user_id) │  │
│  │                                           │  │
│  │  1. Получить оффер из репозитория        │  │
│  │  2. Проверить владельца (user_id)        │  │
│  │  3. Проверить статус == ACTIVE           │  │
│  │  4. Проверить expires_at > now           │  │
│  │  5. Обновить статус → USED               │  │
│  │  6. Вернуть оффер с tariff_snapshot      │  │
│  │                                           │  │
│  │  Исключения:                              │  │
│  │   ❌ OfferNotFoundException               │  │
│  │   ❌ OfferExpiredException                │  │
│  │   ❌ OfferAlreadyUsedException            │  │
│  └───────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │   PostgreSQL   │
         │   Repository   │
         └────────────────┘
                  │
                  │ 1. SELECT offer WHERE offer_id=?
                  │ 2. UPDATE status='USED'
                  │ 3. INSERT audit_log
                  ▼
            ┌──────────┐
            │ Database │
            │ (offers) │
            └──────────┘


Результат:
{
  "offer_id": "uuid",
  "status": "VALIDATED",
  "tariff_snapshot": {
    "tariff_id": "tariff-001",
    "base_rate": 5.0,
    "segment_multiplier": 1.0,
    "currency": "RUB",
    "rules": {...}
  }
}
```

## 3. Архитектура слоев

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                              │
│  - HTTP endpoints (FastAPI)                                 │
│  - Request/Response validation (Pydantic)                   │
│  - Error handling → HTTP status codes                       │
│  - Dependency injection                                     │
└────────────────────────┬────────────────────────────────────┘
                         │ зависит от
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                            │
│  - Бизнес-логика (use cases)                               │
│  - Greedy pricing fallback                                  │
│  - Валидация офферов                                        │
│  - Работа через абстракции (интерфейсы)                    │
└────────────────────────┬────────────────────────────────────┘
                         │ зависит от
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer                             │
│  - Модели (Offer, TariffInfo, UserInfo)                    │
│  - Исключения (OfferNotFoundException, etc.)               │
│  - Enum (OfferStatus, UserSegment)                         │
│  - Без зависимостей от фреймворков                         │
└─────────────────────────────────────────────────────────────┘
                         ▲
                         │ реализует интерфейсы
                         │
┌─────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Repositories (PostgreSQL)                            │  │
│  │   - PostgresOfferRepository                           │  │
│  │   - CRUD операции                                     │  │
│  │   - Audit logging                                     │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  HTTP Clients                                         │  │
│  │   - UserClient (User Service)                         │  │
│  │   - TariffClient (Tariff Service + LRU cache)        │  │
│  │   - ConfigClient (Config Service + TTL cache)        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 4. Жизненный цикл оффера

```
     СОЗДАНИЕ           ИСПОЛЬЗОВАНИЕ        ЗАВЕРШЕНИЕ
         │                    │                   │
         ▼                    ▼                   ▼
    ┌─────────┐          ┌──────┐          ┌──────────┐
    │ ACTIVE  │─────────▶│ USED │          │ EXPIRED  │
    └─────────┘          └──────┘          └──────────┘
         │                                       ▲
         │ expires_at < now                     │
         └──────────────────────────────────────┘

Статусы:
  ACTIVE    - оффер создан и может быть использован
  USED      - оффер использован для старта аренды
  EXPIRED   - время действия истекло
  CANCELLED - отменен (не используется в текущей версии)
```

## 5. Greedy Pricing Fallback

```
User Service недоступен
         │
         ▼
    ┌─────────────────────────────────┐
    │ TariffClient.get_greedy_tariff()│
    └─────────────┬───────────────────┘
                  │
                  ▼
    ┌──────────────────────────────────┐
    │ Выбор максимальной ставки        │
    │ base_rate × 1.5 (multiplier)     │
    └──────────────┬───────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────┐
    │ Создание оффера с greedy тарифом │
    │ tariff_snapshot.is_greedy = true │
    └──────────────────────────────────┘
```
