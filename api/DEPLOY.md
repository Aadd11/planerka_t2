# Deploy Guide

## Summary
Current backend is ready for simple VPS deployment with:
- Docker Compose
- PostgreSQL in Docker
- FastAPI backend in Docker
- Swagger on `/docs`

Security changes included:
- `JWT_SECRET_KEY` is now validated for production-like environments
- verification tokens are stored hashed
- basic security headers are added to responses

## VPS Requirements
- Ubuntu 22.04+ or similar Linux VPS
- Docker
- Docker Compose plugin
- Domain name recommended
- Reverse proxy recommended for HTTPS

## 1. Install Docker
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Reconnect to the server after adding your user to the `docker` group.

## 2. Upload Project
```bash
git clone <your-repo-url> ~/planerka_t2
cd ~/planerka_t2
```

## 3. Prepare Environment
```bash
cp .env.example .env
```

Edit `.env` and set at minimum:
- `JWT_SECRET_KEY` to a long random value, at least 32 characters
- `APP_ENV=production`
- `CORS_ORIGINS` to your real frontend or allowed origins

Example:
```env
POSTGRES_DB=t2_schedule
POSTGRES_USER=postgres
POSTGRES_PASSWORD=strong-db-password
DATABASE_URL=postgresql+psycopg://postgres:strong-db-password@postgres:5432/t2_schedule
JWT_SECRET_KEY=replace_with_a_long_random_secret_at_least_32_chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=https://api.example.com,https://app.example.com
EXPORT_DIR=/tmp
APP_ENV=production
```

## 4. Start Services
```bash
docker compose up --build -d
```

Check status:
```bash
docker compose ps
docker compose logs backend --tail=100
```

## 5. Load Demo Data
```bash
docker compose exec backend python seed_demo.py
```

Demo accounts:
- `admin@t2.demo / password123`
- `manager@t2.demo / password123`
- `employee1@t2.demo / password123`

## 6. Smoke Check
Open:
- `http://<VPS_IP>:8000/health`
- `http://<VPS_IP>:8000/docs`

Or from server:
```bash
curl http://127.0.0.1:8000/health
```

## 7. Recommended Nginx Setup
Put Nginx in front of FastAPI and terminate TLS there.

Minimal reverse proxy:
```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then issue TLS with Let's Encrypt.

## 8. Production Notes
- Do not keep default `JWT_SECRET_KEY`
- Do not expose PostgreSQL publicly if not needed
- Restrict `CORS_ORIGINS`
- Back up PostgreSQL volume
- Consider disabling public `/docs` in strict production environments
- Prefer running behind HTTPS only

## 9. Update Deployment
```bash
git pull
docker compose up --build -d
```
