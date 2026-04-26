# planerka_t2

## Документация

## Frontend

The T2 branded web client lives in [`web/`](./web). It is a React + TypeScript + Vite app.

```bash
cd web
pnpm install
cp .env.example .env
pnpm dev
```

Default API endpoint:

```env
VITE_API_BASE_URL=http://144.31.181.170:8000
```

If the frontend is served from a new VPS/domain, add that origin to backend `CORS_ORIGINS`, for example:

```env
CORS_ORIGINS=http://localhost:5173,http://localhost:8080,https://your-frontend-domain.example
```

Quick start:
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
