# Запуск контейнеров
```bash
docker compose \
  --env-file .env.test \
  -f docker-compose.test.yml \
  up --build
```

# Проверка БД
```bash
psql -h localhost -p 5440 -U postgres -d offer_test
psql -h localhost -p 5441 -U postgres -d rental_cmd_test
```

