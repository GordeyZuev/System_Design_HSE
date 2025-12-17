# ADR-0002: Архитектура Data Warehouse для системы аренды пауэрбанков (Команда 7)

## Контекст

В рамках первого ДЗ была спроектирована и реализована микросервисная архитектура для системы аренды пауэрбанков, включающая:
- **User Service** — управление пользователями, аутентификация (In-memory storage)
- **Offer & Pricing Service** — создание и управление офферами (PostgreSQL, 2 шарда)
- **Rental Command Service** — управление арендами (PostgreSQL, 2 шарда)

Каждый сервис имеет собственную базу данных, что обеспечивает независимость и масштабируемость, но создаёт сложности для аналитики и построения отчётов.

**Проблемы текущей архитектуры для аналитики:**
- Данные распределены по нескольким базам и шардам
- Отсутствует единое место для аналитических запросов
- Тяжёлые аналитические запросы могут влиять на производительность OLTP-систем
- Нет исторических данных (User Service in-memory, Offer Service retention 7 дней)
- Невозможно эффективно строить агрегаты и витрины

**Бизнес-требования:**
- Дашборд с ключевыми метриками для мониторинга бизнеса
- Анализ поведения пользователей, популярности станций, динамики выручки
- Возможность строить отчёты без нагрузки на операционные БД
- Хранение исторических данных для трендов

---

## Решение: Построение классического DWH с многослойной архитектурой

### Архитектурный стиль

Выбрана **многослойная архитектура DWH** с разделением на 4 слоя:
1. **RAW (Staging)** — сырые данные из источников
2. **ODS (Operational Data Store)** — нормализованные оперативные данные
3. **DDS (Data Detail Store)** — детализированные данные в star/snowflake schema
4. **DataMart** — агрегированные витрины для дашбордов

### Общая архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                    ИСТОЧНИКИ ДАННЫХ                              │
├─────────────────────────────────────────────────────────────────┤
│  User Service     │  Offer Service    │  Rental Service          │
│  (In-Memory)      │  (PostgreSQL x2)  │  (PostgreSQL x2)         │
└──────┬────────────┴─────────┬─────────┴──────────┬───────────────┘
       │                      │                     │
       │  CDC/API             │  CDC/JDBC           │  CDC/JDBC
       │                      │                     │
       ▼                      ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AIRFLOW ETL ORCHESTRATION                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ DAG:     │  │ DAG:     │  │ DAG:     │  │ DAG:     │       │
│  │ Raw Load │→ │ ODS Load │→ │ DDS Load │→ │ Mart Load│       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└──────┬────────────┬──────────────┬──────────────┬───────────────┘
       │            │              │              │
       ▼            ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA WAREHOUSE (PostgreSQL)                   │
├─────────────────────────────────────────────────────────────────┤
│  RAW Layer       ODS Layer       DDS Layer       DataMart Layer  │
│  ┌──────────┐   ┌──────────┐    ┌──────────┐   ┌──────────┐   │
│  │raw_users │   │ods_users │    │dim_users │   │dm_metrics│   │
│  │raw_offers│→  │ods_offers│ →  │dim_offers│ → │dm_revenue│   │
│  │raw_      │   │ods_      │    │dim_      │   │dm_station│   │
│  │ rentals  │   │ rentals  │    │ stations │   │ _stats   │   │
│  │raw_      │   │          │    │fact_     │   │          │   │
│  │ events   │   │          │    │ rentals  │   │          │   │
│  └──────────┘   └──────────┘    └──────────┘   └──────────┘   │
└──────────────────────────────────────────┬──────────────────────┘
                                           │
                                           ▼
                                    ┌──────────────┐
                                    │  METABASE    │
                                    │  Dashboard   │
                                    └──────────────┘
```

---

## Технологический стек

### Выбранные технологии

| Компонент | Технология | Обоснование |
|-----------|-----------|-------------|
| **DWH Database** | PostgreSQL 15 | - Единая технология со стеком (проще поддержка)<br>- Поддержка JSON для гибкости<br>- Materialized Views для агрегатов<br>- Партиционирование по датам<br>- Бесплатное решение |
| **ETL Orchestration** | Apache Airflow 2.7+ | - Стандарт индустрии для ETL<br>- Богатый набор операторов (PostgresOperator, PythonOperator)<br>- Web UI для мониторинга<br>- Retry и error handling<br>- Интеграция с PostgreSQL |
| **Data Quality** | Great Expectations | - Валидация данных между слоями<br>- Автоматическая документация качества<br>- Интеграция с Airflow |
| **Visualization** | Metabase | - Простой и быстрый setup<br>- Интуитивный UI для бизнеса<br>- Нативная поддержка PostgreSQL<br>- Бесплатная open-source версия<br>- Авто-обновление дашбордов |
| **Monitoring** | Prometheus + Grafana | - Мониторинг Airflow DAGs<br>- Метрики ETL процессов<br>- Алерты при сбоях |

---

## Слои DWH: Детальное описание

### 1. RAW Layer (Staging)

**Назначение:** Сырые данные из источников "as-is", минимальная обработка

**Стратегия загрузки:** Full reload каждые 10 минут (для MVP), инкрементальная для production

**Таблицы:**

#### raw_users
```sql
CREATE TABLE raw.users (
    raw_id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    status VARCHAR(50),
    created_at TIMESTAMP,
    loaded_at TIMESTAMP DEFAULT NOW(),
    source_system VARCHAR(50) DEFAULT 'user_service'
);
CREATE INDEX idx_raw_users_loaded_at ON raw.users(loaded_at);
```

#### raw_offers
```sql
CREATE TABLE raw.offers (
    raw_id SERIAL PRIMARY KEY,
    offer_id UUID NOT NULL,
    user_id UUID NOT NULL,
    station_id VARCHAR(255) NOT NULL,
    tariff_snapshot JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL,
    tariff_version VARCHAR(50),
    shard_id INTEGER,
    loaded_at TIMESTAMP DEFAULT NOW(),
    source_system VARCHAR(50) DEFAULT 'offer_service'
) PARTITION BY RANGE (loaded_at);

CREATE INDEX idx_raw_offers_loaded_at ON raw.offers(loaded_at);
CREATE INDEX idx_raw_offers_offer_id ON raw.offers(offer_id);
```

#### raw_rentals
```sql
CREATE TABLE raw.rentals (
    raw_id SERIAL PRIMARY KEY,
    rental_id UUID NOT NULL,
    offer_id UUID NOT NULL,
    user_id UUID NOT NULL,
    station_id VARCHAR(255) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL,
    tariff_snapshot JSONB NOT NULL,
    tariff_version VARCHAR(50),
    final_cost NUMERIC(10, 2),
    shard_id INTEGER,
    loaded_at TIMESTAMP DEFAULT NOW(),
    source_system VARCHAR(50) DEFAULT 'rental_service'
) PARTITION BY RANGE (loaded_at);

CREATE INDEX idx_raw_rentals_loaded_at ON raw.rentals(loaded_at);
CREATE INDEX idx_raw_rentals_rental_id ON raw.rentals(rental_id);
```

#### raw_rental_events
```sql
CREATE TABLE raw.rental_events (
    raw_id SERIAL PRIMARY KEY,
    event_id UUID NOT NULL,
    rental_id UUID NOT NULL,
    ts TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB,
    loaded_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (ts);

CREATE INDEX idx_raw_rental_events_ts ON raw.rental_events(ts);
CREATE INDEX idx_raw_rental_events_rental_id ON raw.rental_events(rental_id);
```

#### raw_offer_audit
```sql
CREATE TABLE raw.offer_audit (
    raw_id SERIAL PRIMARY KEY,
    id UUID NOT NULL,
    offer_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    ts TIMESTAMP NOT NULL,
    payload_json JSONB,
    loaded_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (ts);

CREATE INDEX idx_raw_offer_audit_ts ON raw.offer_audit(ts);
```

**Retention:** 30 дней

**Партиционирование:** По `loaded_at` (дневные партиции)

---

### 2. ODS Layer (Operational Data Store)

**Назначение:** Нормализованные данные, дедупликация, базовая очистка

**Стратегия:** Инкрементальная загрузка на основе `loaded_at` из RAW

**Таблицы:**

#### ods_users
```sql
CREATE TABLE ods.users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255),
    phone VARCHAR(50),
    status VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    dw_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ods_users_updated_at ON ods.users(updated_at);
CREATE INDEX idx_ods_users_status ON ods.users(status);
```

#### ods_offers
```sql
CREATE TABLE ods.offers (
    offer_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    station_id VARCHAR(255) NOT NULL,
    tariff_snapshot JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL,
    tariff_version VARCHAR(50),
    tariff_rate_per_minute NUMERIC(10, 4), -- extracted from JSON
    tariff_currency VARCHAR(10), -- extracted from JSON
    updated_at TIMESTAMP DEFAULT NOW(),
    dw_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ods_offers_user_id ON ods.offers(user_id);
CREATE INDEX idx_ods_offers_station_id ON ods.offers(station_id);
CREATE INDEX idx_ods_offers_status ON ods.offers(status);
CREATE INDEX idx_ods_offers_created_at ON ods.offers(created_at);
```

#### ods_rentals
```sql
CREATE TABLE ods.rentals (
    rental_id UUID PRIMARY KEY,
    offer_id UUID NOT NULL,
    user_id UUID NOT NULL,
    station_id VARCHAR(255) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL,
    tariff_snapshot JSONB NOT NULL,
    tariff_version VARCHAR(50),
    final_cost NUMERIC(10, 2),
    duration_minutes INTEGER, -- calculated field
    updated_at TIMESTAMP DEFAULT NOW(),
    dw_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ods_rentals_user_id ON ods.rentals(user_id);
CREATE INDEX idx_ods_rentals_offer_id ON ods.rentals(offer_id);
CREATE INDEX idx_ods_rentals_station_id ON ods.rentals(station_id);
CREATE INDEX idx_ods_rentals_started_at ON ods.rentals(started_at);
CREATE INDEX idx_ods_rentals_status ON ods.rentals(status);
```

**Бизнес-правила ODS:**
- Дедупликация по PK
- Извлечение полей из JSON (tariff_snapshot)
- Расчёт производных полей (duration_minutes)
- Валидация типов данных
- Обработка NULL значений

**Retention:** 1 год

---

### 3. DDS Layer (Data Detail Store)

**Назначение:** Star Schema для эффективных аналитических запросов

**Модель данных:** Star Schema с центральной fact-таблицей и dimensions

#### Размерности (Dimensions)

##### dim_users
```sql
CREATE TABLE dds.dim_users (
    user_dwh_id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    status VARCHAR(50),
    user_created_at TIMESTAMP,
    -- SCD Type 2 fields
    valid_from TIMESTAMP NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMP DEFAULT '9999-12-31',
    is_current BOOLEAN DEFAULT TRUE,
    dw_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dim_users_user_id ON dds.dim_users(user_id);
CREATE INDEX idx_dim_users_is_current ON dds.dim_users(is_current);
CREATE INDEX idx_dim_users_status ON dds.dim_users(status) WHERE is_current = TRUE;
```

##### dim_stations
```sql
CREATE TABLE dds.dim_stations (
    station_dwh_id SERIAL PRIMARY KEY,
    station_id VARCHAR(255) UNIQUE NOT NULL,
    station_name VARCHAR(255), -- можно обогатить из внешнего справочника
    city VARCHAR(100),
    region VARCHAR(100),
    -- Для будущего обогащения
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    dw_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dim_stations_station_id ON dds.dim_stations(station_id);
CREATE INDEX idx_dim_stations_city ON dds.dim_stations(city);
```

##### dim_date
```sql
CREATE TABLE dds.dim_date (
    date_id INTEGER PRIMARY KEY, -- YYYYMMDD
    date_actual DATE NOT NULL UNIQUE,
    day_of_week INTEGER,
    day_name VARCHAR(10),
    day_of_month INTEGER,
    week_of_year INTEGER,
    month_num INTEGER,
    month_name VARCHAR(10),
    quarter INTEGER,
    year INTEGER,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN DEFAULT FALSE -- можно обогатить календарём праздников
);

CREATE INDEX idx_dim_date_date_actual ON dds.dim_date(date_actual);
CREATE INDEX idx_dim_date_year_month ON dds.dim_date(year, month_num);
```

##### dim_time
```sql
CREATE TABLE dds.dim_time (
    time_id INTEGER PRIMARY KEY, -- HHMMSS (e.g., 143000 for 14:30:00)
    time_actual TIME NOT NULL UNIQUE,
    hour INTEGER,
    minute INTEGER,
    hour_of_day VARCHAR(20), -- '00-06', '06-12', '12-18', '18-24'
    is_business_hours BOOLEAN -- 09:00-18:00
);

CREATE INDEX idx_dim_time_hour ON dds.dim_time(hour);
```

##### dim_tariff
```sql
CREATE TABLE dds.dim_tariff (
    tariff_dwh_id SERIAL PRIMARY KEY,
    tariff_version VARCHAR(50) NOT NULL,
    tariff_snapshot JSONB NOT NULL,
    rate_per_minute NUMERIC(10, 4),
    currency VARCHAR(10),
    tariff_type VARCHAR(50), -- 'standard', 'premium', 'promo'
    -- Для анализа
    valid_from TIMESTAMP,
    valid_to TIMESTAMP DEFAULT '9999-12-31',
    dw_loaded_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tariff_version, rate_per_minute)
);

CREATE INDEX idx_dim_tariff_version ON dds.dim_tariff(tariff_version);
CREATE INDEX idx_dim_tariff_type ON dds.dim_tariff(tariff_type);
```

#### Факты (Facts)

##### fact_rentals
```sql
CREATE TABLE dds.fact_rentals (
    rental_dwh_id SERIAL PRIMARY KEY,
    rental_id UUID UNIQUE NOT NULL,
    
    -- Foreign Keys to Dimensions
    user_dwh_id INTEGER REFERENCES dds.dim_users(user_dwh_id),
    station_dwh_id INTEGER REFERENCES dds.dim_stations(station_dwh_id),
    start_date_id INTEGER REFERENCES dds.dim_date(date_id),
    start_time_id INTEGER REFERENCES dds.dim_time(time_id),
    end_date_id INTEGER REFERENCES dds.dim_date(date_id),
    end_time_id INTEGER REFERENCES dds.dim_time(time_id),
    tariff_dwh_id INTEGER REFERENCES dds.dim_tariff(tariff_dwh_id),
    
    -- Degenerate dimensions
    offer_id UUID NOT NULL,
    
    -- Measures (Metrics)
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    final_cost NUMERIC(10, 2),
    status VARCHAR(50),
    
    -- Calculated metrics
    is_completed BOOLEAN GENERATED ALWAYS AS (status = 'FINISHED') STORED,
    is_cancelled BOOLEAN GENERATED ALWAYS AS (status = 'CANCELLED') STORED,
    
    -- Technical fields
    dw_loaded_at TIMESTAMP DEFAULT NOW(),
    dw_updated_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (start_date_id);

CREATE INDEX idx_fact_rentals_user ON dds.fact_rentals(user_dwh_id);
CREATE INDEX idx_fact_rentals_station ON dds.fact_rentals(station_dwh_id);
CREATE INDEX idx_fact_rentals_start_date ON dds.fact_rentals(start_date_id);
CREATE INDEX idx_fact_rentals_status ON dds.fact_rentals(status);
CREATE INDEX idx_fact_rentals_offer_id ON dds.fact_rentals(offer_id);

-- Партиции по месяцам (примеры)
CREATE TABLE dds.fact_rentals_202501 PARTITION OF dds.fact_rentals
    FOR VALUES FROM (20250101) TO (20250201);
CREATE TABLE dds.fact_rentals_202502 PARTITION OF dds.fact_rentals
    FOR VALUES FROM (20250201) TO (20250301);
-- ... создаются автоматически через ETL
```

##### fact_offers
```sql
CREATE TABLE dds.fact_offers (
    offer_dwh_id SERIAL PRIMARY KEY,
    offer_id UUID UNIQUE NOT NULL,
    
    -- Foreign Keys
    user_dwh_id INTEGER REFERENCES dds.dim_users(user_dwh_id),
    station_dwh_id INTEGER REFERENCES dds.dim_stations(station_dwh_id),
    created_date_id INTEGER REFERENCES dds.dim_date(date_id),
    created_time_id INTEGER REFERENCES dds.dim_time(time_id),
    tariff_dwh_id INTEGER REFERENCES dds.dim_tariff(tariff_dwh_id),
    
    -- Measures
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    status VARCHAR(50), -- ACTIVE, USED, EXPIRED
    
    -- Calculated
    ttl_seconds INTEGER, -- expires_at - created_at
    is_used BOOLEAN GENERATED ALWAYS AS (status = 'USED') STORED,
    is_expired_unused BOOLEAN GENERATED ALWAYS AS (status = 'EXPIRED') STORED,
    
    dw_loaded_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (created_date_id);

CREATE INDEX idx_fact_offers_user ON dds.fact_offers(user_dwh_id);
CREATE INDEX idx_fact_offers_station ON dds.fact_offers(station_dwh_id);
CREATE INDEX idx_fact_offers_created_date ON dds.fact_offers(created_date_id);
CREATE INDEX idx_fact_offers_status ON dds.fact_offers(status);
```

**ER-диаграмма DDS (Star Schema):**
```
                    ┌──────────────┐
                    │  dim_users   │
                    │──────────────│
                    │ user_dwh_id  │◄────┐
                    │ user_id      │     │
                    │ email        │     │
                    │ status       │     │
                    └──────────────┘     │
                                         │
     ┌──────────────┐                   │       ┌──────────────┐
     │ dim_stations │                   │       │  dim_date    │
     │──────────────│                   │       │──────────────│
     │station_dwh_id│◄──┐               │   ┌──►│ date_id      │
     │ station_id   │   │               │   │   │ date_actual  │
     │ city         │   │               │   │   │ day_of_week  │
     └──────────────┘   │               │   │   └──────────────┘
                        │               │   │
                        │   ┌───────────┴───┴───────────┐
                        │   │    fact_rentals           │
     ┌──────────────┐   │   │───────────────────────────│
     │  dim_time    │   │   │ rental_dwh_id (PK)        │
     │──────────────│   └───┤ user_dwh_id (FK)          │
     │ time_id      │◄──────┤ station_dwh_id (FK)       │
     │ hour         │       │ start_date_id (FK)        │
     └──────────────┘       │ start_time_id (FK)        │
                            │ end_date_id (FK)          │
     ┌──────────────┐       │ end_time_id (FK)          │
     │ dim_tariff   │       │ tariff_dwh_id (FK)        │
     │──────────────│       │───────────────────────────│
     │tariff_dwh_id │◄──────┤ duration_minutes          │
     │tariff_version│       │ final_cost                │
     │rate_per_min  │       │ status                    │
     └──────────────┘       └───────────────────────────┘
                                         │
                                         │  (Аналогично для fact_offers)
                                         ▼
                            ┌───────────────────────────┐
                            │    fact_offers            │
                            │───────────────────────────│
                            │ offer_dwh_id (PK)         │
                            │ user_dwh_id (FK)          │
                            │ station_dwh_id (FK)       │
                            │ created_date_id (FK)      │
                            │ tariff_dwh_id (FK)        │
                            │ status                    │
                            └───────────────────────────┘
```

**Retention DDS:** 3 года

---

### 4. DataMart Layer

**Назначение:** Предрасчитанные агрегаты для дашбордов

#### dm_daily_metrics
```sql
CREATE MATERIALIZED VIEW mart.dm_daily_metrics AS
SELECT 
    d.date_actual,
    d.year,
    d.month_num,
    d.day_of_week,
    d.is_weekend,
    
    -- Метрики по арендам
    COUNT(DISTINCT fr.rental_id) AS total_rentals,
    COUNT(DISTINCT CASE WHEN fr.is_completed THEN fr.rental_id END) AS completed_rentals,
    COUNT(DISTINCT CASE WHEN fr.is_cancelled THEN fr.rental_id END) AS cancelled_rentals,
    COUNT(DISTINCT fr.user_dwh_id) AS active_users,
    
    -- Метрики по выручке
    SUM(fr.final_cost) AS total_revenue,
    AVG(fr.final_cost) AS avg_rental_cost,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fr.final_cost) AS median_rental_cost,
    
    -- Метрики по длительности
    AVG(fr.duration_minutes) AS avg_duration_minutes,
    SUM(fr.duration_minutes) AS total_duration_minutes,
    
    -- Метрики по офферам
    COUNT(DISTINCT fo.offer_id) AS total_offers_created,
    COUNT(DISTINCT CASE WHEN fo.is_used THEN fo.offer_id END) AS offers_used,
    COUNT(DISTINCT CASE WHEN fo.is_expired_unused THEN fo.offer_id END) AS offers_expired,
    
    -- Конверсия
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN fo.is_used THEN fo.offer_id END) / 
        NULLIF(COUNT(DISTINCT fo.offer_id), 0), 
        2
    ) AS offer_to_rental_conversion_rate
    
FROM dds.dim_date d
LEFT JOIN dds.fact_rentals fr ON d.date_id = fr.start_date_id
LEFT JOIN dds.fact_offers fo ON d.date_id = fo.created_date_id
WHERE d.date_actual >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY d.date_actual, d.year, d.month_num, d.day_of_week, d.is_weekend
ORDER BY d.date_actual DESC;

CREATE UNIQUE INDEX idx_dm_daily_metrics_date ON mart.dm_daily_metrics(date_actual);
```

#### dm_station_stats
```sql
CREATE MATERIALIZED VIEW mart.dm_station_stats AS
SELECT 
    s.station_id,
    s.station_name,
    s.city,
    
    -- Период анализа (последние 30 дней)
    COUNT(DISTINCT fr.rental_id) AS total_rentals_30d,
    COUNT(DISTINCT fr.user_dwh_id) AS unique_users_30d,
    
    -- Выручка
    SUM(fr.final_cost) AS total_revenue_30d,
    AVG(fr.final_cost) AS avg_rental_cost,
    
    -- Использование
    AVG(fr.duration_minutes) AS avg_duration_minutes,
    SUM(fr.duration_minutes) AS total_usage_minutes_30d,
    
    -- Тренды
    COUNT(DISTINCT CASE 
        WHEN fr.start_date_id >= TO_CHAR(CURRENT_DATE - INTERVAL '7 days', 'YYYYMMDD')::INTEGER 
        THEN fr.rental_id 
    END) AS rentals_last_7d,
    
    -- Рейтинг
    RANK() OVER (ORDER BY COUNT(DISTINCT fr.rental_id) DESC) AS popularity_rank
    
FROM dds.dim_stations s
LEFT JOIN dds.fact_rentals fr ON s.station_dwh_id = fr.station_dwh_id
WHERE fr.start_date_id >= TO_CHAR(CURRENT_DATE - INTERVAL '30 days', 'YYYYMMDD')::INTEGER
GROUP BY s.station_id, s.station_name, s.city
ORDER BY total_rentals_30d DESC;

CREATE UNIQUE INDEX idx_dm_station_stats_station_id ON mart.dm_station_stats(station_id);
```

#### dm_user_cohorts
```sql
CREATE MATERIALIZED VIEW mart.dm_user_cohorts AS
SELECT 
    DATE_TRUNC('month', u.user_created_at) AS cohort_month,
    COUNT(DISTINCT u.user_dwh_id) AS cohort_size,
    
    -- Retention анализ
    COUNT(DISTINCT CASE 
        WHEN fr.start_date_id >= TO_CHAR(DATE_TRUNC('month', u.user_created_at), 'YYYYMMDD')::INTEGER
         AND fr.start_date_id < TO_CHAR(DATE_TRUNC('month', u.user_created_at) + INTERVAL '1 month', 'YYYYMMDD')::INTEGER
        THEN u.user_dwh_id 
    END) AS active_month_0,
    
    COUNT(DISTINCT CASE 
        WHEN fr.start_date_id >= TO_CHAR(DATE_TRUNC('month', u.user_created_at) + INTERVAL '1 month', 'YYYYMMDD')::INTEGER
         AND fr.start_date_id < TO_CHAR(DATE_TRUNC('month', u.user_created_at) + INTERVAL '2 month', 'YYYYMMDD')::INTEGER
        THEN u.user_dwh_id 
    END) AS active_month_1,
    
    -- Средние метрики когорты
    AVG(rental_counts.total_rentals) AS avg_rentals_per_user,
    AVG(rental_counts.total_spent) AS avg_revenue_per_user
    
FROM dds.dim_users u
LEFT JOIN (
    SELECT 
        user_dwh_id,
        COUNT(*) AS total_rentals,
        SUM(final_cost) AS total_spent
    FROM dds.fact_rentals
    WHERE is_completed = TRUE
    GROUP BY user_dwh_id
) rental_counts ON u.user_dwh_id = rental_counts.user_dwh_id
WHERE u.is_current = TRUE
  AND u.user_created_at >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', u.user_created_at)
ORDER BY cohort_month DESC;
```

#### dm_hourly_demand
```sql
CREATE MATERIALIZED VIEW mart.dm_hourly_demand AS
SELECT 
    t.hour,
    t.hour_of_day,
    d.is_weekend,
    
    COUNT(DISTINCT fr.rental_id) AS total_rentals,
    AVG(fr.final_cost) AS avg_cost,
    AVG(fr.duration_minutes) AS avg_duration
    
FROM dds.dim_time t
CROSS JOIN (SELECT DISTINCT is_weekend FROM dds.dim_date) d
LEFT JOIN dds.fact_rentals fr 
    ON t.time_id = fr.start_time_id
   AND d.is_weekend = (SELECT is_weekend FROM dds.dim_date WHERE date_id = fr.start_date_id)
WHERE fr.start_date_id >= TO_CHAR(CURRENT_DATE - INTERVAL '30 days', 'YYYYMMDD')::INTEGER
GROUP BY t.hour, t.hour_of_day, d.is_weekend
ORDER BY d.is_weekend, t.hour;
```

#### dm_revenue_breakdown
```sql
CREATE MATERIALIZED VIEW mart.dm_revenue_breakdown AS
SELECT 
    DATE_TRUNC('day', d.date_actual) AS date,
    tariff.tariff_type,
    s.city,
    
    COUNT(DISTINCT fr.rental_id) AS rentals_count,
    SUM(fr.final_cost) AS revenue,
    AVG(fr.final_cost) AS avg_revenue_per_rental,
    SUM(fr.duration_minutes) AS total_minutes
    
FROM dds.fact_rentals fr
JOIN dds.dim_date d ON fr.start_date_id = d.date_id
JOIN dds.dim_tariff tariff ON fr.tariff_dwh_id = tariff.tariff_dwh_id
JOIN dds.dim_stations s ON fr.station_dwh_id = s.station_dwh_id
WHERE d.date_actual >= CURRENT_DATE - INTERVAL '90 days'
  AND fr.is_completed = TRUE
GROUP BY DATE_TRUNC('day', d.date_actual), tariff.tariff_type, s.city
ORDER BY date DESC, revenue DESC;
```

**Refresh стратегия для Materialized Views:**
- `dm_daily_metrics` — обновление каждые 10 минут (REFRESH MATERIALIZED VIEW CONCURRENTLY)
- `dm_station_stats` — обновление раз в час
- `dm_user_cohorts` — обновление раз в день (ночью)
- `dm_hourly_demand` — обновление раз в час
- `dm_revenue_breakdown` — обновление каждые 10 минут

---

## ETL Процессы в Airflow

### Общая структура DAGs

```
DAG 1: raw_data_ingestion (каждые 10 минут)
├── extract_users_from_user_service → load_to_raw_users
├── extract_offers_shard_0 → load_to_raw_offers
├── extract_offers_shard_1 → load_to_raw_offers
├── extract_rentals_shard_0 → load_to_raw_rentals
├── extract_rentals_shard_1 → load_to_raw_rentals
└── extract_events → load_to_raw_events

DAG 2: ods_transformation (каждые 15 минут, после DAG 1)
├── transform_raw_to_ods_users
├── transform_raw_to_ods_offers (дедупликация, JSON parsing)
├── transform_raw_to_ods_rentals (расчёт duration_minutes)
└── data_quality_check (Great Expectations)

DAG 3: dds_star_schema_load (каждые 20 минут, после DAG 2)
├── load_dim_users (SCD Type 2)
├── load_dim_stations
├── load_dim_tariff
├── load_dim_date (pre-populated)
├── load_dim_time (pre-populated)
├── load_fact_offers
├── load_fact_rentals
└── data_quality_check_dds

DAG 4: datamart_refresh (каждые 30 минут, после DAG 3)
├── refresh_dm_daily_metrics
├── refresh_dm_station_stats
├── refresh_dm_user_cohorts
├── refresh_dm_hourly_demand
└── refresh_dm_revenue_breakdown

DAG 5: maintenance (раз в день, ночью)
├── partition_management (создание новых партиций)
├── analyze_tables (обновление статистики)
├── cleanup_old_raw_data (удаление RAW > 30 дней)
└── backup_metadata
```

### Пример DAG 1: Raw Data Ingestion

```python
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'dwh_team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'raw_data_ingestion',
    default_args=default_args,
    description='Extract data from operational DBs to RAW layer',
    schedule_interval='*/10 * * * *',  # Каждые 10 минут
    catchup=False,
    max_active_runs=1,
)

# Task: Extract users from User Service API
extract_users = PythonOperator(
    task_id='extract_users_from_user_service',
    python_callable=extract_users_via_api,
    dag=dag,
)

# Task: Load users to RAW
load_users = PostgresOperator(
    task_id='load_to_raw_users',
    postgres_conn_id='dwh_postgres',
    sql="""
        INSERT INTO raw.users (user_id, email, phone, status, created_at, loaded_at)
        SELECT 
            user_id, email, phone, status, created_at, NOW()
        FROM temp_users_staging
        ON CONFLICT DO NOTHING;
    """,
    dag=dag,
)

# Task: Extract offers from Offer Service Shard 0
extract_offers_shard_0 = PostgresOperator(
    task_id='extract_offers_shard_0',
    postgres_conn_id='offer_service_shard_0',
    sql="""
        SELECT offer_id, user_id, station_id, tariff_snapshot, 
               created_at, expires_at, status, tariff_version, 0 AS shard_id
        FROM offers
        WHERE created_at > (
            SELECT COALESCE(MAX(created_at), '1970-01-01'::timestamp) 
            FROM raw.offers WHERE shard_id = 0
        );
    """,
    dag=dag,
)

# ... аналогично для других источников

extract_users >> load_users
extract_offers_shard_0 >> load_offers
```

### Пример DAG 3: DDS Star Schema Load (ключевые трансформации)

```python
# Task: Load dim_users with SCD Type 2
load_dim_users = PostgresOperator(
    task_id='load_dim_users',
    postgres_conn_id='dwh_postgres',
    sql="""
        -- Закрыть старые версии при изменении
        UPDATE dds.dim_users du
        SET valid_to = NOW(), is_current = FALSE
        WHERE du.user_id IN (
            SELECT user_id FROM ods.users 
            WHERE updated_at > du.valid_from
            AND (email != du.email OR phone != du.phone OR status != du.status)
        ) AND du.is_current = TRUE;
        
        -- Вставить новые версии
        INSERT INTO dds.dim_users (user_id, email, phone, status, user_created_at, valid_from, is_current)
        SELECT user_id, email, phone, status, created_at, NOW(), TRUE
        FROM ods.users ou
        WHERE NOT EXISTS (
            SELECT 1 FROM dds.dim_users du 
            WHERE du.user_id = ou.user_id AND du.is_current = TRUE
        )
        OR EXISTS (
            SELECT 1 FROM dds.dim_users du
            WHERE du.user_id = ou.user_id AND du.is_current = TRUE
            AND (du.email != ou.email OR du.phone != ou.phone OR du.status != ou.status)
        );
    """,
    dag=dag,
)

# Task: Load fact_rentals
load_fact_rentals = PostgresOperator(
    task_id='load_fact_rentals',
    postgres_conn_id='dwh_postgres',
    sql="""
        INSERT INTO dds.fact_rentals (
            rental_id, user_dwh_id, station_dwh_id, 
            start_date_id, start_time_id, end_date_id, end_time_id, tariff_dwh_id,
            offer_id, started_at, finished_at, duration_minutes, final_cost, status
        )
        SELECT 
            r.rental_id,
            du.user_dwh_id,
            ds.station_dwh_id,
            TO_CHAR(r.started_at, 'YYYYMMDD')::INTEGER AS start_date_id,
            TO_CHAR(r.started_at, 'HH24MISS')::INTEGER AS start_time_id,
            TO_CHAR(r.finished_at, 'YYYYMMDD')::INTEGER AS end_date_id,
            TO_CHAR(r.finished_at, 'HH24MISS')::INTEGER AS end_time_id,
            dt.tariff_dwh_id,
            r.offer_id,
            r.started_at,
            r.finished_at,
            r.duration_minutes,
            r.final_cost,
            r.status
        FROM ods.rentals r
        JOIN dds.dim_users du ON r.user_id = du.user_id AND du.is_current = TRUE
        JOIN dds.dim_stations ds ON r.station_id = ds.station_id
        LEFT JOIN dds.dim_tariff dt ON r.tariff_version = dt.tariff_version
        WHERE NOT EXISTS (
            SELECT 1 FROM dds.fact_rentals fr WHERE fr.rental_id = r.rental_id
        )
        ON CONFLICT (rental_id) DO UPDATE SET
            finished_at = EXCLUDED.finished_at,
            end_date_id = EXCLUDED.end_date_id,
            end_time_id = EXCLUDED.end_time_id,
            duration_minutes = EXCLUDED.duration_minutes,
            final_cost = EXCLUDED.final_cost,
            status = EXCLUDED.status,
            dw_updated_at = NOW();
    """,
    dag=dag,
)
```

---

## Дашборд: 6 Основных Метрик Бизнеса

### Структура дашборда в Metabase

**Dashboard: "Powerbank Rental - Executive Overview"**

#### 1. Ключевые KPI (верхняя панель, обновление каждые 10 минут)

**Источник данных:** `mart.dm_daily_metrics`

**Метрика 1: Выручка за сегодня**
```sql
SELECT 
    SUM(total_revenue) AS today_revenue,
    SUM(total_revenue) - LAG(SUM(total_revenue)) OVER (ORDER BY date_actual) AS revenue_change
FROM mart.dm_daily_metrics
WHERE date_actual >= CURRENT_DATE - INTERVAL '1 day'
GROUP BY date_actual
ORDER BY date_actual DESC
LIMIT 1;
```
- **Визуализация:** Число (большой шрифт) + процент изменения vs вчера (зелёный/красный)
- **Алерт:** Если выручка < 80% от среднего за последние 7 дней → красный цвет

**Метрика 2: Количество активных аренд (сегодня)**
```sql
SELECT COUNT(DISTINCT fr.rental_id) AS active_rentals_today
FROM dds.fact_rentals fr
JOIN dds.dim_date d ON fr.start_date_id = d.date_id
WHERE d.date_actual = CURRENT_DATE
  AND fr.is_completed = TRUE;
```
- **Визуализация:** Число + trend sparkline (последние 7 дней)
- **Цель:** > 100 аренд/день (индикатор: зелёный если выполнено)

**Метрика 3: Конверсия оффер → аренда (последние 7 дней)**
```sql
SELECT 
    AVG(offer_to_rental_conversion_rate) AS avg_conversion_rate
FROM mart.dm_daily_metrics
WHERE date_actual >= CURRENT_DATE - INTERVAL '7 days';
```
- **Визуализация:** Процент + gauge chart (0-100%)
- **Цель:** > 70% (отлично), 50-70% (норма), < 50% (проблема)

#### 2. Динамика выручки (временной ряд)

**Источник:** `mart.dm_daily_metrics`

**Метрика 4: Выручка по дням (последние 30 дней)**
```sql
SELECT 
    date_actual,
    total_revenue,
    completed_rentals,
    avg_rental_cost
FROM mart.dm_daily_metrics
WHERE date_actual >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY date_actual;
```
- **Визуализация:** Line chart (2 оси: выручка слева, кол-во аренд справа)
- **Фильтры:** Период (7д/30д/90д), тип дня (все/будни/выходные)
- **Инсайт:** Видны пики выручки в выходные/праздники

#### 3. Топ-5 станций по выручке

**Источник:** `mart.dm_station_stats`

**Метрика 5: Лучшие станции (последние 30 дней)**
```sql
SELECT 
    station_name,
    city,
    total_revenue_30d,
    total_rentals_30d,
    avg_rental_cost,
    popularity_rank
FROM mart.dm_station_stats
ORDER BY total_revenue_30d DESC
LIMIT 5;
```
- **Визуализация:** Horizontal bar chart + таблица с детализацией
- **Drill-down:** Клик на станцию → детальная статистика станции
- **Использование:** Планирование размещения пауэрбанков

#### 4. Анализ спроса по часам и дням недели

**Источник:** `mart.dm_hourly_demand`

**Метрика 6: Тепловая карта спроса (час × день недели)**
```sql
SELECT 
    hour,
    is_weekend,
    total_rentals,
    avg_duration
FROM mart.dm_hourly_demand
ORDER BY is_weekend, hour;
```
- **Визуализация:** Heatmap (час дня по вертикали, будни/выходные по горизонтали)
- **Цветовая схема:** Тёмно-синий (низкий спрос) → Ярко-красный (высокий спрос)
- **Использование:** Динамическое ценообразование, планирование обслуживания

#### Дополнительные панели (второй экран дашборда)

**Панель 7: Когортный анализ**
```sql
SELECT 
    cohort_month,
    cohort_size,
    ROUND(100.0 * active_month_1 / NULLIF(active_month_0, 0), 2) AS retention_rate,
    avg_revenue_per_user
FROM mart.dm_user_cohorts
ORDER BY cohort_month DESC;
```
- **Визуализация:** Retention cohort table + line chart retention по месяцам

**Панель 8: Breakdown выручки (город × тип тарифа)**
```sql
SELECT 
    city,
    tariff_type,
    SUM(revenue) AS total_revenue,
    SUM(rentals_count) AS total_rentals
FROM mart.dm_revenue_breakdown
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY city, tariff_type
ORDER BY total_revenue DESC;
```
- **Визуализация:** Stacked bar chart (города по оси X, выручка по типам тарифов)

### Настройка автообновления в Metabase

- **KPI панель:** Автообновление каждые 10 минут
- **Графики:** Автообновление каждые 30 минут
- **Когорты:** Обновление раз в день (кэшируется)
- **Email отчёты:** Ежедневно в 9:00 для менеджмента

---

## Мониторинг и Качество Данных

### Data Quality Checks (Great Expectations)

**Проверки на уровне RAW → ODS:**
1. **Completeness:** Все PK из source присутствуют в RAW
2. **Timeliness:** Данные загружены не позднее 15 минут от source timestamp
3. **Schema validation:** Типы данных соответствуют ожидаемым

**Проверки на уровне ODS → DDS:**
1. **Referential integrity:** Все FK существуют в dimension tables
2. **Business rules:** 
   - `duration_minutes >= 0`
   - `final_cost >= 0`
   - `finished_at > started_at` (для завершённых аренд)
3. **Duplicates:** Отсутствие дубликатов по PK в fact tables

**Проверки на уровне DataMart:**
1. **Aggregation consistency:** Сумма daily metrics = сумма из fact tables
2. **No missing dates:** Все даты в периоде присутствуют в dm_daily_metrics

### Мониторинг ETL (Prometheus + Grafana)

**Метрики Airflow:**
- `airflow_dag_run_duration` — длительность выполнения DAG
- `airflow_dag_run_status` — статус последнего запуска (success/failed)
- `airflow_task_fail_count` — количество failed tasks за час

**Метрики DWH:**
- `dwh_table_row_count` — количество записей в каждой таблице (мониторинг роста)
- `dwh_table_size_bytes` — размер таблиц (для планирования storage)
- `dwh_query_duration_p99` — p99 latency запросов к DataMart

**Алерты:**
1. DAG не запустился вовремя (delay > 30 минут)
2. Task failed > 3 раз подряд
3. Отсутствие новых данных в RAW > 1 час
4. Размер таблицы вырос > 50% за день (аномалия)

---

## Масштабирование и Оптимизация

### Текущая конфигурация (MVP)

| Компонент | Ресурсы | Обоснование |
|-----------|---------|-------------|
| **DWH PostgreSQL** | 16 CPU, 64 GB RAM, 500 GB SSD | Достаточно для 100K пользователей, 3 года retention |
| **Airflow** | 4 CPU, 16 GB RAM | Параллельный запуск 10 задач |
| **Metabase** | 2 CPU, 8 GB RAM | Обслуживание до 50 одновременных пользователей |

### План масштабирования (1M пользователей)

**Проблема:** При росте до 1M users размер fact_rentals достигнет 7.2 TB за 3 года

**Решение 1: Вертикальное масштабирование PostgreSQL**
- До 64 CPU, 512 GB RAM, 10 TB SSD
- Партиционирование по месяцам (автоматическое создание партиций в DAG)
- Индексы BRIN на timestamp полях (compact для больших таблиц)

**Решение 2: Горизонтальное масштабирование (Citus или Greenplum)**
- Шардирование DDS по `user_dwh_id` (аналогично OLTP)
- Distributed joins для аналитических запросов
- Централизованный DataMart слой (предрасчитанные агрегаты малого размера)

**Решение 3: Переход на OLAP storage (ClickHouse/Apache Druid)**
- Колоночное хранение для аналитических запросов
- 10x компрессия vs PostgreSQL (7.2 TB → 700 GB)
- Sub-second запросы на больших данных
- Но: дополнительная сложность инфраструктуры

**Выбор для MVP:** PostgreSQL + партиционирование (простота, единая технология)

**Миграция на ClickHouse:** Когда fact_rentals > 2 TB или query latency > 5s

### Оптимизация запросов

**1. Materialized Views для DataMart**
- Предрасчитанные агрегаты снижают нагрузку на fact tables
- Refresh стратегия: CONCURRENTLY для отсутствия locks

**2. Индексная стратегия**
- **B-tree индексы:** На FK и часто используемые фильтры (station_id, status)
- **BRIN индексы:** На timestamp поля в больших fact tables (компактные)
- **Partial индексы:** `WHERE is_current = TRUE` для dim_users (SCD Type 2)

**3. Партиционирование**
- **fact_rentals, fact_offers:** По месяцам (date_id)
- **raw tables:** По дням (loaded_at)
- Автоматический архив старых партиций (pg_dump → S3)

**4. Query optimization**
- Избегать `SELECT *` в ETL (только нужные поля)
- EXPLAIN ANALYZE для медленных запросов дашборда
- Connection pooling в Metabase (pgBouncer)

---

## Безопасность и Governance

### Доступы к DWH

| Роль | Права | Пользователи |
|------|-------|--------------|
| **dwh_admin** | ALL на все схемы | DBA, DevOps |
| **etl_user** | READ на source DBs, WRITE на RAW/ODS/DDS/Mart | Airflow |
| **analyst** | READ на DDS и Mart | Data Analysts, BI разработчики |
| **dashboard_user** | READ только на Mart | Metabase, конечные пользователи |

**Запрещено:**
- Прямой доступ к RAW/ODS для аналитиков (только DDS/Mart)
- Запись в DDS/Mart вне ETL процессов
- Доступ к PII полям (email, phone) без явного разрешения

### Аудит и Логирование

**Логируемые события:**
1. Все DDL операции (CREATE/ALTER/DROP table)
2. Запуски/завершения DAG в Airflow
3. Failed tasks с stack trace
4. Data quality check failures
5. Доступ к PII данным (pg_audit)

**Retention логов:** 90 дней

### Резервное копирование

**Стратегия:**
- **Full backup DWH:** Раз в неделю (выходные, ночь)
- **Incremental backup:** Каждый день
- **Point-in-time recovery:** WAL archiving в S3 (retention 30 дней)
- **Backup source DBs:** Ответственность микросервисов (не DWH)

**Restore тесты:** Раз в месяц

---

## Рассмотренные альтернативы

### Альтернатива 1: Cloud DWH (Snowflake / BigQuery / Redshift)

**Плюсы:**
- Managed сервис (меньше операционной нагрузки)
- Автоматическое масштабирование storage/compute
- Separation of storage and compute
- Продвинутые функции (time travel, cloning в Snowflake)
- Высокая доступность из коробки

**Минусы:**
- **Высокая стоимость:** $200-500/месяц для учебного проекта
- Vendor lock-in
- Сложность локальной разработки
- Требуется VPN/network setup для доступа к source DBs
- Дополнительная сложность для студентов

**Сравнение:**

| Критерий | Cloud DWH | PostgreSQL (выбран) |
|----------|-----------|---------------------|
| Стоимость (MVP) | $200-500/мес | $0 (self-hosted) |
| Масштабирование | Автоматическое | Ручное (партиции, индексы) |
| Latency | Может быть выше (network) | Низкая (локально) |
| Операционная нагрузка | Низкая | Средняя (backup, tuning) |
| Локальная разработка | Сложная | Простая (docker-compose) |
| Обучение | Специфичное (Snowflake SQL) | Стандартное (PostgreSQL) |

**Вывод:** PostgreSQL выбран для MVP из-за нулевой стоимости и простоты setup. При росте до 1M users рассмотреть Snowflake.

---

### Альтернатива 2: ClickHouse как OLAP DWH

**Плюсы:**
- Колоночное хранение (10x компрессия)
- Скорость аналитических запросов (100x быстрее PostgreSQL на больших данных)
- Горизонтальное масштабирование через distributed tables
- Специализация для OLAP

**Минусы:**
- Дополнительная технология в стеке (сложность)
- Нет ACID транзакций (eventual consistency)
- Ограниченная поддержка UPDATE/DELETE (не подходит для ODS с дедупликацией)
- Меньше интеграций с BI tools vs PostgreSQL
- Сложнее для студентов (специфичный SQL диалект)

**Сравнение:**

| Критерий | ClickHouse | PostgreSQL (выбран) |
|----------|------------|---------------------|
| Скорость SELECT (fact tables > 1TB) | Очень высокая | Средняя |
| UPDATE/DELETE | Ограничено (async) | Полноценно |
| Транзакции | Нет | Есть (ACID) |
| Компрессия | 10x | 2-3x |
| Интеграция с Metabase | Да, но limited | Нативная |
| Кривая обучения | Высокая | Низкая |

**Вывод:** ClickHouse отложен до production phase. Для MVP размер данных (~100 GB за 3 года) не требует OLAP.

**Trigger для миграции:** fact_rentals > 2 TB или p99 query latency > 5s

---

### Альтернатива 3: Realtime ETL (Kafka + Stream Processing)

**Концепция:** Change Data Capture (Debezium) → Kafka → Flink/Spark Streaming → DWH

**Плюсы:**
- Реал-тайм обновление дашбордов (latency < 1 минуты)
- Масштабируемый ingestion (1000+ events/sec)
- Event-driven архитектура

**Минусы:**
- **Высокая сложность:** Kafka cluster, Debezium connectors, Flink jobs
- Требует опыта в stream processing
- Дороже операционно (больше компонентов для мониторинга)
- Для учебного проекта избыточно (batch ETL каждые 10 минут достаточно)

**Сравнение:**

| Критерий | Kafka + Flink | Airflow Batch ETL (выбран) |
|----------|---------------|----------------------------|
| Latency обновления дашборда | < 1 мин | 10-15 мин |
| Сложность архитектуры | Очень высокая | Средняя |
| Операционные затраты | Высокие | Низкие |
| Подходит для учебного проекта | Нет (overkill) | Да |
| Масштабируемость | Линейная (sharding) | До 10K events/sec |

**Вывод:** Batch ETL достаточно для бизнес-требований (метрики не требуют реал-тайм). Streaming рассмотреть для fraud detection в будущем.

---

### Альтернатива 4: ELT вместо ETL (dbt + Snowflake)

**Концепция:** Load raw data в DWH → трансформации в SQL (dbt models) → DataMart

**Плюсы:**
- Трансформации как код (версионирование, тесты в dbt)
- Separation of concerns (data engineers пишут dbt models)
- Incremental models для оптимизации
- Документация из кода (dbt docs)

**Минусы:**
- Требует Cloud DWH (Snowflake/BigQuery) для эффективности
- Для PostgreSQL ELT менее эффективен (нет separation of compute)
- dbt — дополнительный инструмент (кривая обучения)
- Для MVP ETL в Python проще и гибче

**Вывод:** dbt + ELT — отличный выбор для production с Cloud DWH. Для MVP с self-hosted PostgreSQL выбран классический ETL в Python/SQL через Airflow.

---

## Фиксированные архитектурные решения

### 1. Многослойная архитектура DWH (RAW → ODS → DDS → DataMart)

**Решение:** Строгое разделение на 4 слоя с запретом "перепрыгивания" слоёв

**Обоснование:**
- Воспроизводимость: можно пересчитать любой слой из предыдущего
- Изоляция ошибок: проблема в ODS не ломает RAW
- Аудит: понятно, где произошла трансформация данных

**Trade-off:** Увеличение latency (данные проходят 4 трансформации). Для MVP приемлемо (15-30 минут end-to-end).

---

### 2. Star Schema в DDS слое

**Решение:** Использовать star schema (dimensions + facts) вместо нормализованной модели или OBT (One Big Table)

**Обоснование:**
- Стандарт индустрии для OLAP
- Эффективные JOIN'ы для аналитических запросов
- Переиспользование dimensions (dim_users, dim_stations в разных fact tables)
- Удобство для BI инструментов (Metabase понимает FK relationships)

**Альтернатива (OBT):** Одна широкая таблица с денормализацией. Отклонена из-за дублирования данных и сложности обновления dimensions.

---

### 3. Materialized Views для DataMart слоя

**Решение:** DataMart — это materialized views поверх DDS, а не отдельные таблицы с ETL

**Обоснование:**
- Упрощает pipeline: не нужен отдельный ETL для Mart
- REFRESH MATERIALIZED VIEW проще, чем INSERT/UPDATE логика
- Гарантия консистентности: Mart = производная от DDS
- PostgreSQL CONCURRENTLY обновляет без блокировок

**Trade-off:** Refresh всей MV дороже инкрементального ETL. Для размеров MVP (< 1M записей в fact) приемлемо.

---

### 4. PostgreSQL для всех слоёв DWH

**Решение:** Единая СУБД (PostgreSQL) для RAW/ODS/DDS/Mart вместо микса технологий

**Обоснование:**
- Снижение операционной сложности (одна БД для администрирования)
- Единый язык запросов (PostgreSQL SQL)
- Эффективные трансформации внутри БД (без сетевых вызовов)
- Проще для команды (не нужно знать Spark/Flink)

**Trade-off:** Меньшая производительность на больших данных vs специализированные OLAP системы. Критичность: низкая для MVP.

---

### 5. Batch ETL через Airflow вместо Realtime Streaming

**Решение:** ETL каждые 10-30 минут через Airflow, а не realtime через Kafka

**Обоснование:**
- Бизнес-требования: дашборд не требует секундных обновлений
- Простота: Airflow DAG проще, чем Kafka + Flink
- Стоимость: Airflow дешевле операционно
- Воспроизводимость: легко перезапустить DAG для исправления данных

**SLA:** Данные в дашборде с задержкой до 30 минут от реального события. Приемлемо для executive dashboard.

---

### 6. Retention policies

**Решение:** Фиксированные retention по слоям

| Слой | Retention | Обоснование |
|------|-----------|-------------|
| RAW | 30 дней | Буфер для пересчёта ODS при ошибках |
| ODS | 1 год | Достаточно для исторических трансформаций |
| DDS | 3 года | Бизнес-требование для трендов |
| DataMart | 3 года | Производная от DDS |

**Архивация:** Партиции старше retention экспортируются в S3 Glacier (cold storage).

---

## Метрики успеха DWH

### Технические метрики

| Метрика | Целевое значение | Текущее (MVP) |
|---------|------------------|---------------|
| **ETL end-to-end latency** | < 30 минут | 25 минут |
| **DAG success rate** | > 99% | - (TBD) |
| **Query p99 latency (DataMart)** | < 2 секунды | - (TBD) |
| **Data freshness** | < 30 минут от source | 10 минут |
| **Storage size (DWH)** | < 500 GB | 50 GB (initial) |

### Бизнес-метрики

1. **Дашборд используется ежедневно** — > 5 просмотров/день от менеджмента
2. **Data-driven решения** — минимум 2 инсайта/неделю из дашборда (документируются)
3. **Снижение аналитических запросов к OLTP** — 0 тяжёлых запросов к production БД микросервисов
4. **Время на построение нового отчёта** — < 1 дня (благодаря готовым DDS/Mart)

---

## Roadmap и Future Enhancements

### Phase 1: MVP (Текущее ДЗ)
- ✅ RAW, ODS, DDS, DataMart слои
- ✅ 4 DAG в Airflow (ingestion, ODS, DDS, Mart refresh)
- ✅ 6 метрик в дашборде Metabase
- ✅ Документация таблиц

### Phase 2: Production Readiness (Следующий квартал)
- Great Expectations data quality checks
- Алерты в Grafana при сбоях ETL
- Incremental ETL вместо full reload
- Automated partition management
- CI/CD для Airflow DAGs

### Phase 3: Advanced Analytics (6 месяцев)
- Machine Learning модели (прогноз спроса, churn prediction)
- Feature Store на базе DDS
- Real-time dashboard (если бизнес потребует)
- Миграция на ClickHouse при росте данных

### Phase 4: Enterprise Features (1 год)
- Data Catalog (Apache Atlas / Amundsen)
- Data Lineage visualization
- Self-service BI для бизнес-пользователей
- Федеративные запросы к внешним источникам (Presto/Trino)

---

## Заключение

Спроектирована классическая многослойная архитектура DWH на базе PostgreSQL с оркестрацией ETL через Apache Airflow и визуализацией в Metabase. Архитектура обеспечивает:

**Изоляция от OLTP:** Аналитические запросы не влияют на production микросервисы  
**Масштабируемость:** Партиционирование и индексы поддерживают рост до 1M пользователей  
**Простота:** Единая технология (PostgreSQL) снижает операционную нагрузку  
**Гибкость:** Star schema позволяет быстро создавать новые витрины  
**Data Quality:** Слоистая архитектура обеспечивает аудит и воспроизводимость  

Выбранные решения оптимальны для учебного проекта с возможностью эволюции в production-grade систему при росте требований.
