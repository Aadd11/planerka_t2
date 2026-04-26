# planerka_t2

Backend documentation for the current API version is available in [api/README.md](./api/README.md).

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

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python seed_demo.py
```

Docker also builds the frontend service on `http://localhost:8080`; set `VITE_API_BASE_URL` in `.env` to point it at a different backend.
