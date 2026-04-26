# Deploy Guide

## Summary

This branch adds a production-oriented container layout:

- dedicated `migrate` job
- stateless `api` runtime
- reverse proxy in front of the API
- `/live` and `/ready` probes
- production compose separated from local dev compose
- support for running multiple `api` containers behind one reverse proxy

## Local Development

Use the default compose file or the explicit dev file:

```bash
docker compose up --build -d
```

or

```bash
docker compose -f docker-compose.dev.yml up --build -d
```

## Production Deployment

Production compose expects an external PostgreSQL instance and an immutable app image.

### 0. Assumptions

- repository path on server: `~/planerka_t2`
- Docker and Compose plugin are already installed
- PostgreSQL is reachable from containers
- your image is already built and published, or you use a locally available tag

### 1. Clone repository

```bash
git clone <your-repo-url> ~/planerka_t2
cd ~/planerka_t2
git checkout dev_aadd_prod
```

### 2. Prepare production env file

Create `.env.prod` in repo root:

```bash
cat > .env.prod <<'EOF'
DATABASE_URL=postgresql+psycopg://user:password@db-host:5432/t2_schedule
JWT_SECRET_KEY=replace_with_a_long_random_secret_at_least_32_chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=https://api.example.com,https://app.example.com
APP_ENV=production
LOG_LEVEL=info
WEB_CONCURRENCY=2
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
API_IMAGE=registry.example.com/planerka_t2/api:2026-04-26
EOF
```

### Required env

```env
DATABASE_URL=postgresql+psycopg://user:password@db-host:5432/t2_schedule
JWT_SECRET_KEY=replace_with_a_long_random_secret_at_least_32_chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=https://api.example.com,https://app.example.com
APP_ENV=production
LOG_LEVEL=info
WEB_CONCURRENCY=2
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
API_IMAGE=registry.example.com/planerka_t2/api:2026-04-26
```

### 3. Pull image if needed

```bash
docker pull registry.example.com/planerka_t2/api:2026-04-26
```

If you use another tag, replace it in both the command and `.env.prod`.

### 4. Run migration job only

This is the safest first step before bringing traffic online:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm migrate
```

### 5. Start reverse proxy and API

Start the stack with at least two API containers:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --scale api=2 reverse-proxy api
```

### 6. Check container status

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

You should see:

- one completed `migrate`
- two running `api` containers
- one running `reverse-proxy`

### 7. Check logs

Migration logs:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs migrate --tail=100
```

Proxy logs:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs reverse-proxy --tail=100
```

API logs:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs api --tail=100
```

### 8. Verify liveness and readiness through the proxy

From the host:

```bash
curl -i http://127.0.0.1/live
curl -i http://127.0.0.1/ready
curl -i http://127.0.0.1/health
```

Expected:

- `/live` returns `200`
- `/ready` returns `200` only if DB is reachable
- response headers include `X-Upstream-Addr`

### 9. Verify that the proxy sees multiple API containers

Check Docker DNS from inside the proxy container:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec reverse-proxy getent hosts api
```

You should see more than one IP when `api` is scaled to 2 or more replicas.

### 10. Verify request distribution across API replicas

Run several requests and inspect `X-Upstream-Addr`:

```bash
for i in 1 2 3 4 5 6 7 8; do
  curl -s -D - http://127.0.0.1/ready -o /dev/null | grep X-Upstream-Addr
done
```

If the proxy is resolving multiple backend containers correctly, you should observe at least two backend addresses over repeated requests.

### 11. Stop or restart the production stack

Stop:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml down
```

Restart:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --scale api=2 reverse-proxy api
```

### 12. Roll out a new image version

Update the tag in `.env.prod`, then:

```bash
docker pull registry.example.com/planerka_t2/api:<new-tag>
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm migrate
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --scale api=2 reverse-proxy api
```

### 13. Local production-like verification with the existing local Postgres

If you want to test the prod compose locally against the already running host PostgreSQL port `5432`, create:

```bash
cat > .env.prod.local <<'EOF'
DATABASE_URL=postgresql+psycopg://postgres:qxnN3eYqomMBDXF9OupKTQzKZczVhvxs4vPvSZZ3oU8@host.docker.internal:5432/t2_schedule
JWT_SECRET_KEY=replace_with_a_long_random_secret_at_least_32_chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost,http://127.0.0.1
APP_ENV=production
LOG_LEVEL=info
WEB_CONCURRENCY=2
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
API_IMAGE=planerka_t2-backend:latest
EOF
```

Then run:

```bash
docker compose --env-file .env.prod.local -f docker-compose.prod.yml run --rm migrate
docker compose --env-file .env.prod.local -f docker-compose.prod.yml up -d --scale api=2 reverse-proxy api
docker compose --env-file .env.prod.local -f docker-compose.prod.yml ps
```

And verify:

```bash
curl -i http://127.0.0.1/live
curl -i http://127.0.0.1/ready
for i in 1 2 3 4 5 6 7 8; do
  curl -s -D - http://127.0.0.1/ready -o /dev/null | grep X-Upstream-Addr
done
```

## Stack layout

- `migrate` runs Alembic `upgrade head`
- `api` serves FastAPI with multiple workers
- `reverse-proxy` terminates incoming HTTP traffic and forwards to scaled API containers

## Health Endpoints

- `GET /health` - generic health information
- `GET /live` - process liveness
- `GET /ready` - readiness with DB connectivity check

## Notes

- runtime schema creation was removed from app startup
- Excel export no longer writes to container-local temporary files
- for real horizontal scaling, keep PostgreSQL outside the compose lifecycle
- the production compose is designed to be scaled with:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --scale api=2 reverse-proxy api
```

- `deploy.replicas` is not used as the scaling mechanism because plain Docker Compose ignores Swarm-style replica management; `--scale api=2` is the effective command
