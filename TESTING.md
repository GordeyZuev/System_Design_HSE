# Запуск тестов

```bash
# Запустить все тесты
docker-compose -f docker-compose.test.yml up --build

# Очистка
docker-compose -f docker-compose.test.yml down --rmi all
```