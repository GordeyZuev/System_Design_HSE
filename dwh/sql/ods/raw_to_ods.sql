
INSERT INTO ods.users (
    user_id,
    email,
    phone,
    status,
    created_at,
    updated_at,
    is_deleted,
    dw_loaded_at
)
SELECT
    u.user_id,
    u.email,
    u.phone,
    u.status,
    u.created_at,
    now(),
    FALSE,
    now()
FROM raw.users u
WHERE u.loaded_at >
      COALESCE(
          (SELECT max(dw_loaded_at) FROM ods.users),
          '1900-01-01'
      )
ON CONFLICT (user_id) DO UPDATE
SET
    email = EXCLUDED.email,
    phone = EXCLUDED.phone,
    status = EXCLUDED.status,
    updated_at = now(),
    dw_loaded_at = now();


INSERT INTO ods.offers (
    offer_id,
    user_id,
    station_id,
    tariff_snapshot,
    created_at,
    expires_at,
    status,
    tariff_version,
    tariff_rate_per_minute,
    tariff_currency,
    updated_at,
    dw_loaded_at
)
SELECT
    o.offer_id,
    o.user_id,
    o.station_id,
    o.tariff_snapshot,
    o.created_at,
    o.expires_at,
    o.status,
    o.tariff_version,
    (o.tariff_snapshot->>'rate_per_minute')::numeric,
    o.tariff_snapshot->>'currency',
    now(),
    now()
FROM raw.offers o
WHERE o.loaded_at >
      COALESCE(
          (SELECT max(dw_loaded_at) FROM ods.offers),
          '1900-01-01'
      )
ON CONFLICT (offer_id) DO UPDATE
SET
    status = EXCLUDED.status,
    tariff_rate_per_minute = EXCLUDED.tariff_rate_per_minute,
    tariff_currency = EXCLUDED.tariff_currency,
    updated_at = now(),
    dw_loaded_at = now();


INSERT INTO ods.rentals (
    rental_id,
    offer_id,
    user_id,
    station_id,
    started_at,
    finished_at,
    status,
    tariff_snapshot,
    tariff_version,
    final_cost,
    duration_minutes,
    updated_at,
    dw_loaded_at
)
SELECT
    r.rental_id,
    r.offer_id,
    r.user_id,
    r.station_id,
    r.started_at,
    r.finished_at,
    r.status,
    r.tariff_snapshot,
    r.tariff_version,
    r.final_cost,
    CASE
        WHEN r.finished_at IS NOT NULL
        THEN (EXTRACT(EPOCH FROM (r.finished_at - r.started_at)) / 60)::int
        ELSE NULL
    END,
    now(),
    now()
FROM raw.rentals r
WHERE r.loaded_at >
      COALESCE(
          (SELECT max(dw_loaded_at) FROM ods.rentals),
          '1900-01-01'
      )
ON CONFLICT (rental_id) DO UPDATE
SET
    status = EXCLUDED.status,
    finished_at = EXCLUDED.finished_at,
    final_cost = EXCLUDED.final_cost,
    duration_minutes = EXCLUDED.duration_minutes,
    updated_at = now(),
    dw_loaded_at = now();
