# planerka_t2

Backend documentation for the current API version is available in [api/README.md](./api/README.md).

Quick start:

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python seed_demo.py
```

Production-oriented deployment files:

- `docker-compose.prod.yml` - immutable production stack with `api`, `migrate`, `reverse-proxy`
- `docker-compose.dev.yml` - local development stack
- `deploy/nginx.prod.conf` - reverse proxy config
