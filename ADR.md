# ADR-0001: Архитектура сервиса аренды пауэрбанков (Команда 7)

### Архитектурный стиль

Выбран подход **микросервисной архитектуры с выделенными доменами и CQRS**, без единой точки отказа.

#### Ключевые сервисы:

- **API Gateway (nginx)** — единая точка входа, маршрутизирует запросы на нужный сервис.
- **Offer & Pricing Service** — отвечает за офферы и прайсинг (использует внешние tariffs, config и обращается к User Service для сегментов/статусов), может работать автономно для чтения.
- **Rental Command Service** — операции старта/завершения аренды (использует оффер и взаимодействует с внешними stations/payments). Содержит эндпоинты для чтения арендов и текущей стоимости.
- **User Service (Auth & Profile)** — аутентификация, авторизация, профили, сегменты пользователей. Единственный источник истины по пользователям для остальных сервисов.

**Горячие пути разделены:**
- создание оффера,
- старт/финиш аренды,
- чтение состояния аренды/стоимости — масштабируются независимо.

Внешние зависимости (мокируются или предполагаются):
- **Stations Service** — управление станциями, резервирование/выдача/возврат пауэрбанков.
- **Payments Service** — списание/возврат средств, работа через Outbox-паттерн.
- **Tariff Service** — предоставление тарифов, используется через клиент с LRU-кэшем.
- **Config Service** — централизованная конфигурация, используется через клиент с TTL-кэшем.

### Компоненты

#### API Gateway (nginx)
- Единая точка входа для всех клиентских запросов.
- Маршрутизация на внутренние сервисы.
- Терминация TLS (опционально).

#### Offer & Pricing Service
- Создание офферов с актуальными тарифами.
- Валидация и использование офферов при старте аренды.
- Контроль свежести оффера (expires_at, tariff_version).
- Хранит `offers` и `offer_audit` в PostgreSQL.


#### Rental Command Service
- Управляет жизненным циклом аренды (старт/финиш).
- Command endpoints: `POST /internal/rentals/start`, `POST /internal/rentals/{rental_id}/finish`.
- Query endpoints: `GET /internal/rentals/{rental_id}` — чтение аренды и текущей стоимости.
- Хранит `rentals`, `rental_events`, `outbox_payments` в PostgreSQL.
- Взаимодействует с внешними Stations и Payments через HTTP API.

#### User Service (Auth & Profile)
- Аутентификация и авторизация через JWT.
- Управление профилями и сегментами пользователей для персонализации тарифов.
- **Хранилище:** In-memory (для прототипа/демонстрации).

### Данные и хранилище

#### Контроль свежести оффера
- Проверка `expires_at` и `tariff_version` при создании аренды.
- Если оффер протух — HTTP 409 и новый оффер.

#### Шардирование
- Реализовано в **Rental Command Service** и **Offer & Pricing Service**.
- По `user_id` (MD5 hash-based).
- Единая стратегия для консистентности и data locality.

### Нефункциональные требования

#### Maintainability
- Чёткие слои: API, Service, Domain, Repository.
- Bounded contexts, SOLID, чистая архитектура.
- Конфигурация через env.

#### Reliability
- Retry/timeout для критичных клиентов (stations, payments).
- Outbox для платежей.
- Fallback и кэш для некритичных.

#### Scalability
- Stateless Rental Service.
- Горизонтальное масштабирование.
- Read scaling через реплики БД.
- Кэширование для снижения нагрузки.


#### Integration
- Работа с stations/payments, idempotency.
- Поведение при истёкшем TTL tariffs.

#### Load
- 1000 RPS на `POST /rentals/start`.
- 100x `GET /rentals/{id}` на одну аренду.


### Развёртывание

- Docker и docker-compose.
- Prometheus + Grafana.
- Автоматические миграции БД.

## Фиксированные архитектурные решения

1. **Сетевые границы**
   - Внешние клиенты взаимодействуют только с **API Gateway**.
   - Все внутренние вызовы между сервисами идут по публичным contract-first API (HTTP/gRPC).

2. **User Service (Auth & Profile)**
   - **Единственный источник истины по пользователям**.
   - Выдаёт JWT; остальные сервисы доверяют токену и клеймам.

3. **Greedy pricing**
   - Реализовано в **Offer & Pricing Service**.
   - Условие активации: таймаут или ошибка обращения к User Service при расчёте прайсинга.

4. **Tariffs / Config**
   - Tariffs и Config доступны только через соответствующие клиенты (адаптеры) с кэшем.
   - При протухании TTL для тарифов всегда возвращается ошибка; использование устаревших тарифов запрещено (применяется default).

5. **Stations / Payments**
   - Критичные зависимости для команд аренды (требуют трассировки).
   - При недоступности — операции старта аренды не выполняются.

---

## Хранилища по сервисам

### API Gateway
- **Хранилище:** нет бизнес-БД.
- **Состояние:** stateless.

### User Service (Auth & Profile)
- **Тип БД:** In-memory (для прототипа).
- **Структуры данных:**
  - `users(user_id, email, phone, password_hash, status, created_at)`
  - `user_profiles(user_id, name, extra_metadata)`
  - `user_segments(user_id, segment, updated_at)`
  - `refresh_tokens(token_id, user_id, expires_at, revoked)`
- **Особенности:**
  - Простые in-memory словари для быстрого прототипирования.
  - Данные не персистентны (теряются при перезапуске).
  - Для production потребуется миграция на PostgreSQL.

### Offer & Pricing Service
- **Тип БД:** PostgreSQL.
- **Таблицы:**

**`offers`:**
- `offer_id` (UUID, PK)
- `user_id` (UUID, NOT NULL, INDEX)
- `station_id` (VARCHAR(255), NOT NULL, INDEX)
- `tariff_snapshot` (JSON, NOT NULL) — ставка/правила для расчёта стоимости
- `created_at` (TIMESTAMP, NOT NULL, INDEX)
- `expires_at` (TIMESTAMP, NOT NULL, INDEX)
- `status` (ENUM: ACTIVE, USED, EXPIRED, NOT NULL, INDEX)
- `tariff_version` (VARCHAR(50), NULLABLE)
- Индексы: `(user_id, status)`, `(status, expires_at)`

**`offer_audit`:**
- `id` (UUID, PK)
- `offer_id` (UUID, NOT NULL, INDEX)
- `event_type` (VARCHAR(50), NOT NULL)
- `ts` (TIMESTAMP, NOT NULL, INDEX)
- `payload_json` (JSON, NULLABLE)
- Индекс: `(offer_id, ts)`

- **API Endpoints:**

- `POST /internal/offers` — создать оффер
  - Request: `{user_id: UUID, station_id: str, user_segment: str?}`
  - Response: `{offer_id: UUID, expires_at: datetime, tariff_details: {...}, estimated_rate_per_minute: float, currency: str}`
  - Errors: 503 (Tariff Service недоступен), 500 (БД ошибка)

- `GET /internal/offers/{offer_id}` — получить оффер
  - Query params: `user_id: UUID?`
  - Response: `{offer_id: UUID, user_id: UUID, station_id: str, tariff_snapshot: {...}, expires_at: datetime, status: str}`
  - Errors: 404 (оффер не найден), 500 (БД ошибка)

- `POST /internal/offers/{offer_id}/validate` — валидировать и использовать оффер
  - Query params: `user_id: UUID`
  - Response: `{offer_id: UUID, tariff_snapshot: {...}, expires_at: datetime}`
  - Errors: 404 (оффер не найден), 409 (оффер истёк/уже использован), 500 (БД ошибка)
- **Шардирование:**
  - По `user_id` (MD5 hash-based)
  - Формула: `shard_index = int(md5(user_id).hexdigest(), 16) % len(SHARDS)`
  - Текущая конфигурация: 2 шарда (DB_URL_OFFER_SHARD_0, DB_URL_OFFER_SHARD_1)

### Rental Command Service
- **Тип БД:** PostgreSQL, логически отделён от Offer.
- **Таблицы:**

**`rentals`:**
- `rental_id` (UUID, PK)
- `offer_id` (UUID, NOT NULL, INDEX)
- `user_id` (UUID, NOT NULL, INDEX)
- `station_id` (VARCHAR, NOT NULL)
- `started_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)
- `finished_at` (TIMESTAMP WITH TIME ZONE, NULLABLE)
- `status` (ENUM: PENDING, ACTIVE, FINISHED, CANCELLED, NOT NULL)
- `tariff_snapshot` (JSON, NOT NULL) — копия из оффера
- `tariff_version` (VARCHAR, NULLABLE)

**`rental_events`:**
- `event_id` (UUID, PK)
- `rental_id` (UUID, NOT NULL, FK → rentals.rental_id, INDEX)
- `ts` (TIMESTAMP WITH TIME ZONE, NOT NULL)
- `type` (VARCHAR, NOT NULL) — rental_started, rental_finished, etc.
- `payload` (JSON, NULLABLE)

**`rental_cost_snapshots`:**
- `id` (UUID, PK)
- `rental_id` (UUID, NOT NULL, FK → rentals.rental_id, INDEX)
- `ts` (TIMESTAMP WITH TIME ZONE, NOT NULL)
- `cost_amount` (NUMERIC(10, 2), NOT NULL)
- `details` (JSON, NULLABLE)

**`payment_outbox`:**
- `id` (UUID, PK)
- `rental_id` (UUID, NOT NULL)
- `amount` (NUMERIC, NOT NULL)
- `created_at` (TIMESTAMP, NOT NULL)
- `processed` (BOOLEAN, DEFAULT FALSE)
- **API Endpoints:**

**Command endpoints:**
- `POST /internal/rentals/start` — создать аренду
  - Request: `{offer_id: UUID}`
  - Response: `{rental_id: UUID, started_at: datetime, status: str}`
  - Errors: 409 (оффер истёк/использован), 503 (Stations недоступен), 500 (БД ошибка)

- `POST /internal/rentals/{rental_id}/finish` — завершить аренду
  - Request: `{station_id: str}`
  - Response: `{rental_id: UUID, finished_at: datetime, final_cost: float, status: str}`
  - Errors: 404 (аренда не найдена), 409 (неверный user_id/статус), 503 (Stations недоступен), 500 (БД ошибка)

**Query endpoints:**
- `GET /internal/rentals/{rental_id}` — получить информацию об аренде и текущей стоимости
  - Response: `{rental_id: UUID, status: str, station_id: str, started_at: datetime, finished_at: datetime?, current_cost: float}`
  - Errors: 404 (аренда не найдена), 403 (неверный user_id)
- **Шардирование:**
  - По `user_id` (hash-based).
  - Формула: `shard_index = int(md5(user_id).hexdigest(), 16) % len(SHARDS)`
  - Текущая конфигурация: 2 шарда (DB_URL_SHARD_0, DB_URL_SHARD_1)
  - Шарды загружаются из переменных окружения DB_URL_SHARD_*


---

## Надежность 

### Rental Command Service

При недоступности внешних сервисов (Offer Service, Stations Adapter) или ошибке чтения/записи выбрасываются исключения и происходит откат БД — все операции в атомарных транзакциях.

Если на любом этапе start_rental или finish_rental внешний сервис недоступен/возвращает ошибку, выбрасывается исключение. Операция в транзакции, поэтому происходит полный откат. Аренда не создаётся/не завершается, состояние консистентно, клиент получает 4xx или 5xx.

Ошибка на уровне ORM/БД (потеря соединения, нарушение ограничений) приводит к выбросу исключения. Операция в транзакции, поэтому все изменения отменяются, состояние БД остаётся неизменным. 

Операция finish_rental считается успешной только если выполнены все шаги:
1. Чтение сущности аренды по rental_id
2. Проверка совпадения user_id запроса и user_id из записи в БД
3. Проверка статуса аренды (ACTIVE)
4. Успешный вызов Stations Adapter (return_powerbank)
5. Успешное обновление записи в rentals (установка finished_at, статуса, итоговой стоимости)
6. Запись события в rental_events
7. Создание записи в outbox_payments

Если любая из операций завершается ошибкой, вся транзакция откатывается: аренда остается в статусе ACTIVE, запись в outbox не появляется, клиент получает ошибку.

Одна транзакция на весь процесс гарантирует атомарность: операции не могут быть частично применены, состояние либо в исходной точке, либо полностью обновлено.


### Offer & Pricing Service

Сервис имеет три внешние зависимости с разными стратегиями обработки отказов:

**1. User Service (некритичная зависимость)**
- **Timeout:** 2 секунды
- **Retry:** нет (быстрый fail)
- **Fallback:** Greedy Pricing
- **Поведение при отказе:** Сервис продолжает работать, создавая офферы с максимальным тарифом.

**2. Tariff Service (критичная зависимость)**
- **Timeout:** 3 секунды
- **Retry:** нет
- **Cache:** LRU + TTL (10 минут, размер 1000 записей)
- **Поведение при отказе:** 
  - Cache HIT — сервис работает нормально
  - Cache MISS + ошибка Tariff Service — HTTP 503, оффер не создаётся

**3. Config Service (некритичная зависимость)**
- **Timeout:** 1 секунда
- **Cache:** TTL 60 секунд с auto-refresh
- **Поведение при отказе:** Используется закэшированная конфигурация. При полном отсутствии конфига применяются дефолтные значения (offer_ttl=300s).

**Операции с БД:**
- Все операции создания/обновления офферов выполняются в транзакциях PostgreSQL
- При ошибке записи в БД (потеря соединения, constraint violation) транзакция откатывается
- Клиент получает HTTP 500, оффер не создаётся
- Audit log записывается в отдельной транзакции (best effort — не блокирует основную операцию)

**Валидация оффера (endpoint для Rental Service):**
- Атомарная операция: проверка статуса + обновление на USED
- При конфликте — HTTP 409, при отсутствии оффера — HTTP 404


**Итог:** Плавная деградация при недоступности User Service, работа из кэша при проблемах с Config, отказ в создании офферов при недоступности Tariff Service.

---

## Use-case потоки

Ключевые сценарии:

### 1. Аутентификация и получение токена
1. Client → **User Service**: `POST /auth/login {email, password}`.
2. User Service валидирует пользователя и возвращает:
   - `access_token` (JWT с `sub=user_id`, `segment`, `roles`).
3. Client в последующих запросах передаёт `Authorization: Bearer <access_token>`.

### 2. Создание оффера аренды
1. Client → **API Gateway**: `POST /offers {station_id}` + JWT.
2. Gateway валидирует JWT (через публичный ключ User Service).
3. Gateway → **Offer & Pricing Service**: `POST /internal/offers` с данными:
   - `user_id` из токена,
   - `station_id`,
   - `user_segment` из токена (если есть).
4. Offer & Pricing Service:
   - Читает актуальный config из кэша.
   - Читает tariffs через LRU-кэш; при miss — запрашивает Tariffs Service.
   - При необходимости — запрос к User Service для уточнения сегмента.
   - При недоступности User Service применяет greedy pricing.
   - Формирует `tariff_snapshot_json` и `expires_at`.
   - Создаёт запись в `offers`.
5. Ответ Gateway → Client:
   - `offer_id`, `expires_at`, описание тарифа.

### 3. Старт аренды (использование оффера)
1. Client → **API Gateway**: `POST /rentals/start {offer_id}` + JWT.
2. Gateway → **Rental Command Service**: `POST /internal/rentals/start` с данными:
   - `user_id` из токена,
   - `offer_id`.
3. Rental Command Service:
   - Читает оффер из **Offer & Pricing Service** через API.
   - Проверяет:
     - `expires_at >= now`,
     - статус оффера `ACTIVE`.
   - Вызывает **Stations Adapter**: `POST /stations/reserve_or_issue {station_id, user_id}`.
   - При успехе создаёт `rental` в `rentals` и событие `rental_started` в `rental_events`.
4. Ответ Gateway → Client:
   - `rental_id`, `start_time`, базовые тарифные условия.

### 4. Завершение аренды
1. Client → **API Gateway**: `POST /rentals/{rental_id}/finish {station_id}` + JWT.
2. Gateway → **Rental Command Service**.
3. Rental Command Service:
   - Проверяет совпадение `user_id`.
   - Вычисляет стоимость по `tariff_snapshot_json` оффера + фактическому времени.
   - Вызывает **Stations Adapter**: `POST /stations/return {station_id, rental_id}`.
   - Создаёт запись в `outbox_payments` на списание.
   - Обновляет `rentals.status = FINISHED`, пишет `rental_events`.
4. Payments процессинг (асинхронно):
   - Payments Adapter читает `outbox_payments`, вызывает внешний Payments Service.
   - При успехе помечает запись как `SENT`.
5. Ответ Gateway → Client:
   - Финальная стоимость, статус `FINISHED`.

### 5. Получение информации об аренде и текущей стоимости
1. Client → **API Gateway**: `GET /rentals/{rental_id}` + JWT.
2. Gateway → **Rental Command Service**: `GET /internal/rentals/{rental_id}` с:
   - `user_id` из токена.
3. Rental Command Service (query endpoint):
   - Проверяет владение `rental.user_id == token.user_id`.
   - Если `status = ACTIVE`:
     - Использует `tariff_snapshot` и `started_at` для расчёта `current_cost` на момент запроса.
   - Если `status = FINISHED`:
     - Возвращает сохранённую конечную стоимость.
4. Ответ:
   - `rental_id, status, station_id, started_at, finished_at, current_cost, tariff_details`.

### 6. Интеграции с внешними сервисами

#### Config Service
- Клиенты обращаются через **ConfigClient** с кэшем TTL=60s и auto-refresh.
- При истечении TTL запрашивает Config Service заново.

#### Tariff Service
- **Offer & Pricing Service** обращается через **TariffClient**:
  - LRU-кэш по ключу (station_id, tariff_type, segment).
  - TTL (по умолчанию 10 минут, конфигурируемый).
  - При истекшем TTL выполняет запрос к Tariffs Service.
  - Если запрос завершился ошибкой — возвращает ошибку, оффер не создаётся.

#### Fallback: Greedy Pricing
- Активируется в **Offer & Pricing Service** при недоступности User Service.
- Процесс:
  1. Offer & Pricing пытается получить сегмент пользователя от User Service.
  2. При таймауте/ошибке: выбирает тариф с максимальной ставкой из доступных для данной станции.
  3. Формирует оффер на основе greedy тарифа (защита от потери выручки).

---

## Архитектура
![Архитектура системы](docs/design.png)

---

## Рассмотренные альтернативы

### Архитектурный стиль

**Альтернатива: Монолитная архитектура**

**Плюсы:**
- Простота разработки (один репозиторий)
- ACID транзакции между офферами и арендами
- Быстрый старт MVP
- Проще отладка

**Минусы:**
- Невозможность независимого масштабирования (офферы создаются чаще, чем завершаются аренды)
- Единая точка отказа
- Разный профиль нагрузки: офферы (CPU-bound, кэш, внешние вызовы) vs аренды (IO-bound, транзакции)
- Сложность поддержки при росте команды

**Сравнение:**

| Критерий | Монолит | Микросервисы (выбран) |
|----------|---------|----------------------|
| Масштабирование | Единое, нельзя масштабировать части независимо | Независимое: офферы (CPU-bound) и аренды (IO-bound) отдельно |
| Производительность | Ограничена единой точкой | 1000 RPS на старт, 100x чтений — достижимо |
| Надёжность | Единая точка отказа | Изоляция отказов по доменам |
| Разработка | Проще (один репозиторий) | Сложнее, но команда может работать параллельно |
| Транзакции | ACID между офферами и арендами | Транзакции внутри сервиса, eventual consistency между сервисами |

**Вывод:** Выбрана микросервисная архитектура с разделением Offer и Rental для независимого масштабирования (1000 RPS на старт аренды, 100x чтений).

---

### Выбор базы данных

**Альтернатива 1: Managed PostgreSQL**

**Плюсы:**
- Автоматические бэкапы и point-in-time recovery
- Автоматическое масштабирование storage
- Managed репликация и failover
- Мониторинг из коробки

**Минусы:**
- Высокая стоимость для учебного проекта
- Vendor lock-in
- Сложность локальной разработки (нужны credentials, VPN)
- Для MVP избыточно

**Альтернатива 2: NoSQL (MongoDB, DynamoDB, Cassandra)**

**Плюсы:**
- Горизонтальное масштабирование "из коробки"
- Гибкая схема (tariff_snapshot как JSON без миграций)
- Высокая доступность

**Минусы:**
- Отсутствие ACID транзакций (критично для `validate_and_use_offer` — race condition)
- Сложность обеспечения консистентности (оффер ACTIVE в USED должно быть атомарным)
- Eventual consistency не подходит для критичных операций (старт аренды)

**Сравнение:**

| Критерий | Managed PostgreSQL | NoSQL | Self-hosted PostgreSQL (выбран) |
|----------|-------------------|-------|--------------------------------|
| ACID транзакции | Да | Нет | Да |
| Консистентность | Строгая | Eventual | Строгая |
| Горизонтальное масштабирование | Через реплики | Да | Через шардирование |
| Управление | Автоматическое | Managed | Ручное |
| Стоимость | Высокая | Средняя | Нулевая (MVP) |
| Локальная разработка | Сложная | Средняя | Простая (docker-compose) |
| Vendor lock-in | Есть | Есть | Нет |
| Критичные операции | SELECT FOR UPDATE | Race conditions | SELECT FOR UPDATE |

**Вывод:** Выбран self-hosted PostgreSQL в Docker. NoSQL отклонён из-за отсутствия ACID транзакций. Managed PostgreSQL отклонён из-за высокой стоимости и сложности локальной разработки.

**Trade-off:** Принимаем необходимость ручного управления репликацией и бэкапами в обмен на контроль и нулевую стоимость для MVP.

---

### Стратегия шардирования

#### Расчет объемов данных

**Исходные данные:**
- **X = 1000 RPS** — создание аренд (write)
- **Y = 100** — сколько раз пользователь просматривает один заказ (коэффициент)
- **Z = 100 КБ** — размер записи о заказе в БД
- **Read RPS = X * Y = 1000 * 100 = 100,000 RPS** (каждую аренду просматривают ~100 раз)

**Целевая нагрузка:** 1M пользователей, 2 аренды/месяц

**Rental Command Service (retention 3 года):**
- Записей: 1M users * 2 аренды/мес * 12 мес * 3 года = **72M**
- Объем: 72M * 100 КБ = **7.2 TB**
- Write: **1000 RPS** (создание/завершение аренд) → 100 МБ/с
- Read: **100,000 RPS** (просмотр статуса, Y=100 просмотров на аренду) → **10 ГБ/с (80 Гбит/с)**

**Offer Service (retention 7 дней):**
- Записей: ~500K активных офферов
- Объем: 500K * 5 КБ = **2.5 GB**
- Write: **1000 RPS** (создание перед арендой)
- Read: **1000 RPS** (валидация при старте)

#### Стратегия шардирования

**Ключ:** `user_id` (MD5 hash → `shard_index = md5(user_id) % num_shards`)

**Обоснование:**
- Все запросы содержат `user_id` из JWT → single-shard query
- Данные пользователя изолированы в одном шарде
- Офферы и аренды на одном шарде → data locality

**Текущая конфигурация (MVP):**
- Rental Service: **2 шарда** PostgreSQL
- Offer Service: **2 шарда** PostgreSQL
- Роутинг на уровне приложения

#### План роста

| Пользователи | Шардов | TB/шард | RPS/шард (w/r) | Статус |
|--------------|--------|---------|----------------|--------|
| 100K (MVP) | 2 | 0.36 TB | 500w / 50K r |  Превышен лимит 200GB |
| 500K | 4 | 0.9 TB | 250w / 25K r | Превышен лимит |
| 1M | 8 | 0.9 TB | 125w / 12.5K r | Превышен лимит |
| 5M | 20 | 0.36 TB | 50w / 5K r | ✅ Норма |

**Критерии добавления шарда:** Storage > 200GB или CPU > 70% или p99 > 200ms

**Вывод:** Для целевой нагрузки (1M users, 7.2TB) минимально **8 шардов**. Для MVP (100K users) достаточно **2-4 шарда**.

**Процесс добавления шардов:**
1. Создать новые PostgreSQL инстансы (docker-compose)
2.  Downtime: rehashing и миграция данных (~30-60 мин)
3. Обновить конфигурацию, рестарт сервисов

**Для production:** Миграция на consistent hashing или Citus для минимизации downtime.

#### Расчет железа

**Для 1M пользователей (8 шардов):**

**1 шард Rental Service:**
- Storage: 0.9 TB + 30% запас = **1.2 TB SSD**
- RAM: **128 GB** (индексы ~80GB + OS + буферы)
- CPU: **16 cores** (нагрузка 125w / 12.5K r)
- Network: **10 Гбит/с** (12.5K RPS * 100КБ = 1.25 ГБ/с)

**1 шард Offer Service:**
- Storage: **100 GB SSD** (весь dataset ~320MB в памяти)
- RAM: **32 GB**
- CPU: **8 cores**

**Итого БД (8+8 шардов):**
- Storage: 8*1.2TB + 8*0.1TB = **10.4 TB**
- RAM: 8*128GB + 8*32GB = **1.3 TB**
- CPU: 8*16 + 8*8 = **192 cores**
- Серверов: **16 штук**

**Application серверы (Rental + Offer + User):**
- 8-10 инстансов для HA
- По 8 CPU / 16GB = **64-80 cores, 128-160 GB RAM**

**API Gateway (nginx):**
- 2-3 инстанса
- По 4 CPU / 8GB = **8-12 cores, 16-24 GB RAM**

**Итого система (1M users):**
- **Storage:** ~10.5 TB SSD
- **RAM:** ~1.5 TB
- **CPU:** ~270 cores
- **Network:** ~80 Гбит/с суммарная (10 ГБ/с read трафик)
- **Серверов:** ~26-30 штук
