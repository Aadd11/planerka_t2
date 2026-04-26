# planerka_t2

## Документация

- [api/README.md](./api/README.md) — основная документация по backend API
- [API.md](./API.md) — подробное описание endpoint'ов
- [api/DEPLOY.md](./api/DEPLOY.md) — инструкция по деплою и запуску production-стека

Быстрый старт:

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python seed_demo.py
```

Файлы для деплоя и контейнеризации:

- `docker-compose.prod.yml` — production-конфигурация со службами `api`, `migrate` и `reverse-proxy`
- `docker-compose.dev.yml` — отдельная конфигурация для локальной разработки
- `deploy/nginx.prod.conf` — конфигурация Nginx для production reverse proxy
