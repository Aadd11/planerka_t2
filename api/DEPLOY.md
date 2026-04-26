# Руководство по деплою

## Стек

Production-стек состоит из трёх ролей:

- `migrate` — однократный запуск миграций Alembic
- `api` — один или несколько контейнеров FastAPI
- `reverse-proxy` — Nginx перед API

Ключевые свойства текущей схемы:

- приложение не создаёт таблицы при старте
- экспорт не пишет временные файлы в файловую систему контейнера
- API можно запускать в нескольких экземплярах за одним proxy

## Зависимости

- Linux-сервер с установленными Docker и Docker Compose plugin
- внешний PostgreSQL, доступный из контейнеров
- Docker image приложения, уже загруженный в registry или доступный локально

## 1. Клонирование репозитория

```bash
git clone <your-repo-url> ~/planerka_t2
cd ~/planerka_t2
git checkout dev_aadd_prod
```

## 2. Подготовка production env-файла

Создайте файл `.env.prod` в корне проекта:

```bash
cat > .env.prod <<'EOF'
# Полный URL подключения к PostgreSQL.
DATABASE_URL=postgresql+psycopg://user:password@db-host:5432/t2_schedule

# Секретный ключ для подписи JWT. Должен быть длинным и случайным.
JWT_SECRET_KEY=replace_with_a_long_random_secret_at_least_32_chars

# Алгоритм подписи JWT.
JWT_ALGORITHM=HS256

# Время жизни access token в минутах.
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Разрешённые домены для CORS через запятую.
CORS_ORIGINS=https://api.example.com,https://app.example.com

# Режим приложения. Для production должен быть production.
APP_ENV=production

# Уровень логирования.
LOG_LEVEL=info

# Количество worker-процессов внутри одного API-контейнера.
WEB_CONCURRENCY=2

# Размер пула соединений с БД на контейнер.
DB_POOL_SIZE=10

# Сколько дополнительных соединений можно открыть сверх пула.
DB_MAX_OVERFLOW=20

# Сколько секунд ждать свободное соединение из пула.
DB_POOL_TIMEOUT=30

# Через сколько секунд переоткрывать соединения к БД.
DB_POOL_RECYCLE=1800

# Docker image приложения с конкретным тегом.
API_IMAGE=registry.example.com/planerka_t2/api:2026-04-26
EOF
```

## 3. Загрузка image

Если image лежит в registry:

```bash
docker pull registry.example.com/planerka_t2/api:2026-04-26
```

Если используете другой тег, замените его и в команде, и в `.env.prod`.

## 4. Запуск миграций

Сначала прогоните только миграции:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm migrate
```

Что должно произойти:

- контейнер `migrate` стартует
- дождётся доступности БД
- применит Alembic миграции
- завершится без ошибки

## 5. Запуск production-стека

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --scale api=2 reverse-proxy api
```

## 6. Проверка контейнеров

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

Ожидаемое состояние:

- `migrate` завершён успешно
- два контейнера `api` работают
- один контейнер `reverse-proxy` работает

## 7. Проверка логов

Миграции:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs migrate --tail=100
```

API:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs api --tail=100
```

Proxy:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs reverse-proxy --tail=100
```

## 8. Проверка health endpoint'ов

С сервера:

```bash
curl -i http://127.0.0.1/live
curl -i http://127.0.0.1/ready
curl -i http://127.0.0.1/health
```

Что означает ответ:

- `/live` — процесс приложения жив
- `/ready` — приложение готово принимать трафик и видит БД
- `/health` — общий технический endpoint

## 9. Проверка, что proxy работает с двумя API-репликами

Сначала проверьте, что Docker DNS знает сервис `api`:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec reverse-proxy getent hosts api
```

Затем несколько раз вызовите `/ready` и посмотрите заголовок `X-Upstream-Addr`:

```bash
for i in 1 2 3 4 5 6 7 8; do
  curl -s -D - http://127.0.0.1/ready -o /dev/null | grep X-Upstream-Addr
done
```

Если всё работает корректно, в выводе будут встречаться как минимум два разных backend-адреса.

## 10. Перезапуск стека

Остановка:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml down
```

Повторный запуск:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --scale api=2 reverse-proxy api
```

## 11. Выкатка новой версии

1. Обновите `API_IMAGE` в `.env.prod`
2. Подтяните новый image
3. Снова прогоните миграции
4. Перезапустите API и proxy

Команды:

```bash
docker pull registry.example.com/planerka_t2/api:<new-tag>
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm migrate
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --scale api=2 reverse-proxy api
```

## 12. Локальная production-проверка

Если нужно локально протестировать production compose против PostgreSQL, который уже слушает на хосте `5432`, создайте `.env.prod.local`:

```bash
cat > .env.prod.local <<'EOF'
# Подключение из контейнера к PostgreSQL на хосте.
DATABASE_URL=postgresql+psycopg://postgres:password@host.docker.internal:5432/t2_schedule

# JWT secret для локальной production-проверки.
JWT_SECRET_KEY=replace_with_a_long_random_secret_at_least_32_chars

# Алгоритм подписи JWT.
JWT_ALGORITHM=HS256

# Время жизни access token.
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS для локальной проверки.
CORS_ORIGINS=http://localhost,http://127.0.0.1

# Запускаем в production-режиме.
APP_ENV=production

# Уровень логирования.
LOG_LEVEL=info

# Количество worker-процессов на контейнер.
WEB_CONCURRENCY=2

# Параметры пула соединений.
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# Локальный image, уже собранный через docker compose build.
API_IMAGE=planerka_t2-backend:latest
EOF
```

Порядок команд:

```bash
docker compose --env-file .env.prod.local -f docker-compose.prod.yml run --rm migrate
docker compose --env-file .env.prod.local -f docker-compose.prod.yml up -d --scale api=2 reverse-proxy api
docker compose --env-file .env.prod.local -f docker-compose.prod.yml ps
curl -i http://127.0.0.1/live
curl -i http://127.0.0.1/ready
for i in 1 2 3 4 5 6 7 8; do
  curl -s -D - http://127.0.0.1/ready -o /dev/null | grep X-Upstream-Addr
done
```