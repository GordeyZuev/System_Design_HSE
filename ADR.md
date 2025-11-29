# ADR-0001: Архитектура сервиса аренды пауэрбанков (Команда 7)

### Архитектурный стиль

Выбран подход **микросервисной архитектуры с выделенными доменами и CQRS**, без жёсткой зависимости всех запросов от одного сервиса.

Ключевые сервисы:

- **API Gateway** — единая точка входа, маршрутизирует запросы на нужный сервис.
- **Offer & Pricing Service** — отвечает за офферы и прайсинг (использует tariffs, config и обращается к отдельному User Service для сегментов/статусов), самодостаточный по чтению.
- **Rental Command Service** — операции старта/завершения аренды (использует оффер и данные станций/платежей).
- **Rental Query Service** — быстрые чтения по арендам и текущей стоимости (CQRS, postgres).
- **Stations Adapter** — критичный сервис взаимодействия со станциями.
- **Payments Adapter** — критичный сервис взаимодействия с платежами.
- **Tariffs, Config Clients** — обёртки над внешними сервисами с кэшем и falcоlback-политиками.
- **User Service (Auth & Profile)** — отдельный сервис рядом с API Gateway: аутентификация, авторизация, профили, сегменты пользователей. Другие сервисы обращаются к нему как к единому источнику правды по пользователям.

Горячие пути разделены:
- создание оффера,
- старт/финиш аренды,
- чтение состояния аренды/стоимости — масштабируются независимо.


### Компоненты

#### Rental Service (Core)
- Управляет офферами и арендой.
- Контролирует свежесть оффера (expires_at, tariff_version).
- Endpoint: `GET /rentals/{rental_id}` — возвращает статус и текущую стоимость.
- Хранит состояние в PostgreSQL.

#### Stations Adapter
- Проверяет наличие и доступность станций.
- Обеспечивает команду на выдачу/возврат пауэрбанка.
- При сбое — fail fast + retry.

#### Payments Adapter
- Отправляет команды на списание/возврат денег.
- Идемпотентен: операции по `rental_id`.
- Использует Outbox-паттерн для гарантированной доставки.

#### Tariffs / Config Clients и User Servicexwxw
- **ConfigClient** — кэш с TTL=60s, auto-refresh.
- **TariffClient** — LRUCache с TTL (дефолт 10 минут, конфигурируемый), при протухании ошибка.
- **User Service (Auth & Profile)** — отдельный сервис, через который проходит аутентификация и авторизация (JWT). Offer & Pricing Service и другие бэкенды используют его API для получения сегмента/статуса пользователя.
- **Fallback greedy pricing** — если при вычислении стоимости Offer & Pricing Service не может получить информацию от User Service (таймаут/ошибка), он использует "жадный" тариф. Это локальная деградация без проброса проблемы в Gateway.

### Данные и хранилище

#### База данных (PostgreSQL)

#### Контроль свежести оффера
- Проверка `expires_at` и `tariff_version` при создании аренды.
- Если оффер протух — HTTP 409 и новый оффер.

#### Шардирование
- Логическое по `user_id` или `station_region`.
- Rental Service хранит mapping shard → connection.

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

#### Chaos
- Отключение users → greedy pricing.
- Отключение tariffs → ошибка.

### Развёртывание

- Docker и docker-compose.
- Prometheus + Grafana.
- Автоматические миграции БД.

## Фиксированные архитектурные решения

1. **Сетевые границы**
   - Внешние клиенты взаимодействуют только с **API Gateway**.
   - Все внутренние вызовы между сервисами идут по публичным contract-first API (HTTP/gRPC).

2. **User Service (Auth & Profile)**
   - Является **единственным источником истины по пользователям**.
   - Выдаёт JWT; остальные сервисы доверяют токену и клеймам.

3. **Greedy pricing**
   - Реализуется строго в **Offer & Pricing Service**.
   - Условие активации: таймаут или ошибка обращения к User Service при расчёте прайсинга.

4. **Tariffs / Config**
   - Tariffs и Config доступны только через соответствующие клиенты (адаптеры) с кэшем.
   - При протухании TTL для тарифов всегда возвращается ошибка; использование устаревших тарифов запрещено (тогда кидаем default).

5. **Stations / Payments**
   - Tracing-критичные зависимости для команд аренды.
   - При недоступности — операции старта аренды не выполняются.

---

## Хранилища по сервисам

### API Gateway
- **Хранилище:** нет бизнес-БД.
- **Состояние:** stateless.

### User Service (Auth & Profile)
- **Тип БД:** PostgreSQL.
- **Таблицы:**
  - `users(user_id, email, phone, password_hash, status, created_at)`
  - `user_profiles(user_id, name, extra_metadata_json)`
  - `user_segments(user_id, segment, updated_at)`
  - `refresh_tokens(token_id, user_id, expires_at, revoked)`
- **Репликация:**
  - 1 primary + 1..N read-replicas для чтения профилей и сегментов.

### Offer & Pricing Service
- **Тип БД:** PostgreSQL.
- **Таблицы:**
  - `offers(offer_id, user_id, station_id, tariff_snapshot_json, created_at, expires_at, status)`
  - `offer_audit(id, offer_id, event_type, ts, payload_json)`
- **Особенности:**
  - В `tariff_snapshot_json` фиксируется ставка/правила, по которым потом считается аренда.
  - `expires_at` используется для контроля свежести.
- **Репликация:**
  - 1 primary для записи, 1..N read-replicas для чтения офферов.
- **Шардирование:**
  - Логическое по `user_id`:
    - `shard = hash(user_id) mod N`.
    - Каждый шард — БД-инстанс.

### Rental Command Service
- **Тип БД:** PostgreSQL, логически отделён от Offer.
- **Таблицы:**
  - `rentals(rental_id, offer_id, user_id, station_id, started_at, finished_at, status)`
  - `rental_events(event_id, rental_id, ts, type, payload_json)`
  - `rental_cost_snapshots(rental_id, ts, cost_amount, details_json)` — агрегированные стоимости.
  - `outbox_payments(id, rental_id, operation, amount, status, payload_json, created_at)` — для интеграции с Payments.
- **Репликация:**
  - Primary для команд, реплики читаются Rental Query Service.
- **Шардирование:**
  - По `user_id`:

### Rental Query Service
- **Тип БД:** read-store.
- **Источник данных:** события из `rental_events` + состояния из `rentals`.
- **Таблицы/модели:**
  - `rental_view(rental_id, user_id, station_id, status, started_at, finished_at, current_cost, last_calculated_at)`
- **Репликация:**
  - Данные заполняются из primary/реплик Rental Command Service через поток событий.
- **Шардирование:**
  - Аналогичное по `user_id`.

### Stations Adapter
- **Хранилище:**
  - Нет собственной БД.
  - In-memory кэш метаданных станций с коротким TTL.

### Payments Adapter
- **Хранилище:**
  - Не имеет отдельной БД.
  - Использует таблицу `outbox_payments` в `rental-cmd` для гарантированной доставки.
  - Куда-то шлет и мы получаем ответ

---

## Use-case потоки

Ниже описаны ключевые сценарии целиком

### 1. Аутентификация и получение токена
1. Client → **User Service**: `POST /auth/login {email, password}`.
2. User Service валидирует пользователя и возвращает:
   - `access_token` (JWT с `sub=user_id`, `segment`, `roles`).
3. Client во всех последующих запросах передаёт `Authorization: Bearer <access_token>`.

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
   - При необходимости запрашивает User Service для уточнения сегмента.
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
   - Читает оффер из **Offer & Pricing Service API** только через API.
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
   - Валидирует, что `user_id` совпадает.
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
2. Gateway → **Rental Query Service**: `GET /internal/rentals/{rental_id}` с:
   - `user_id` из токена.
3. Rental Query Service:
   - Проверяет владение `rental.user_id == token.user_id`.
   - Если `status = ACTIVE`:
     - Использует `tariff_snapshot` и `started_at` для расчёта `current_cost` на момент запроса.
   - Если `status = FINISHED`:
     - Возвращает сохранённую конечную стоимость.
4. Ответ:
   - `rental_id, status, station_id, started_at, finished_at, current_cost, tariff_details`.

### 6. Работа с Config
- Все сервисы, которым нужен конфиг, обращаются к **ConfigClient**.
- ConfigClient хранит значение в кэше c TTL=60s.
- При истечении TTL запрашивает Config Service заново.

### 7. Работа с Tariffs
- Offer & Pricing Service обращается к **TariffClient**.
- TariffClient:
  - LRU-кэш по ключу (station_id, tariff_type, segment).
  - TTL (по умолчанию 10 минут, конфигом).
  - При истекшем TTL выполняет запрос к Tariffs Service.
  - Если запрос неуспешен → возвращает ошибку наверх; оффер не создаётся.

### 8. Fallback greedy pricing (User Service недоступен)
1. Offer & Pricing вызывает User Service для сегмента.
2. Если таймаут/ошибка:
   - Выбирает тариф с максимальной ставкой из доступных тарифов для данного station_id.
   - Формирует оффер на основе этого greedy тарифа.

---

