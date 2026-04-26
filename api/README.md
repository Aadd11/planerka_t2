# T2 Schedule Planner API

## Описание

Backend API для сервиса планирования графиков сотрудников. Система покрывает:

- регистрацию, вход и подтверждение пользователей;
- периоды сбора графиков по группам;
- сохранение, отправку и проверку расписаний;
- комментарии руководителя и контроль статусов отправки;
- почасовое покрытие по группе;
- экспорт расписаний в Excel;
- демонстрационные данные для показа и тестирования.

## Возможности текущей версии

- роли: `employee`, `manager`, `admin`;
- привязка данных к группе через поле `alliance` в модели и термин “Группа” в продуктовой логике;
- мультиинтервальные рабочие дни;
- комментарии на день и на весь график;
- статусы `draft` и `submitted` через `schedule_submissions`;
- правила валидации для `adult`, `minor_student`, `minor_not_student`;
- контроль доступа руководителя только в рамках своей группы;
- health endpoint'ы `/health`, `/live`, `/ready`;
- stateless Excel-экспорт без записи временных файлов в контейнер;
- миграции через Alembic и отдельный migration job для production.

## Технический стек

- `FastAPI` — REST API, OpenAPI/Swagger, dependency injection;
- `SQLAlchemy` — ORM и работа с транзакциями;
- `PostgreSQL` — основная production-база данных;
- `Alembic` — миграции схемы и bootstrap базы;
- `Pydantic` — схемы запросов/ответов и валидация данных;
- `python-jose` + JWT — аутентификация и роли;
- `bcrypt/passlib` — хеширование паролей;
- `openpyxl` — экспорт графиков в Excel;
- `pytest` + `httpx`/`TestClient` — HTTP-уровневые backend-тесты;
- `Docker` + `Docker Compose` — локальный запуск и production-конфигурации;
- `Nginx` — reverse proxy для production-стека.

## Ключевые особенности проекта

- Ролевая модель: сотрудник, руководитель, администратор.
- Валидация графиков вынесена в backend и не зависит от frontend-логики.
- Поддерживаются несколько рабочих интервалов в пределах одного дня.
- Данные и доступы изолированы по группам.
- Есть demo-ready сценарий с seed-данными и Swagger UI.
- Подготовлен production-путь с миграциями, readiness/liveness и запуском нескольких API-реплик за proxy.

## Структура

- [app.py](./app.py) — сборка FastAPI приложения и метаданные OpenAPI.
- [routes_auth.py](./routes_auth.py) — endpoint'ы аутентификации.
- [routes_schedule.py](./routes_schedule.py) — графики и валидация.
- [routes_manager.py](./routes_manager.py) — endpoint'ы руководителя.
- [routes_periods.py](./routes_periods.py) — периоды и статистика.
- [routes_admin.py](./routes_admin.py) — управление пользователями.
- [routes_export.py](./routes_export.py) — экспорт в Excel.
- [routes_templates.py](./routes_templates.py) — шаблоны графиков пользователя.
- [schedule_service.py](./schedule_service.py) — нормализация и логика валидации.
- [seed_demo.py](./seed_demo.py) — генерация демонстрационных данных.
- [alembic](./alembic) — миграции базы данных.
- [tests/test_backend.py](./tests/test_backend.py) — backend-тесты.

## OpenAPI / Swagger

После запуска backend доступны:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- схема OpenAPI: `http://localhost:8000/openapi.json`

### Важный момент по входу
`POST /auth/login` принимает оба формата:

1. `application/json`

```json
{
  "email": "manager@t2.demo",
  "password": "password123"
}
```

2. `application/x-www-form-urlencoded`

```text
username=manager@t2.demo
password=password123
```

Это сделано специально, чтобы вход работал и из Swagger/UI-клиентов, и из обычных frontend/backend клиентов без 400/422 из-за несовпадения формата.

## Локальный запуск

1. Создайте и активируйте виртуальное окружение.
2. Установите зависимости:

```bash
./.venv/bin/python -m pip install -r requirements.txt
```

3. Подготовьте `.env` на основе [.env.example](./.env.example).
4. Поднимите PostgreSQL.
5. Запустите backend:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Деплой

Подробная production-инструкция вынесена в отдельный файл:

- [DEPLOY.md](./DEPLOY.md)

## Docker

По умолчанию корневой `docker-compose.yml` поднимает локальный dev-стек:

- `postgres`
- `migrate`
- `backend`

Запуск из корня репозитория:

```bash
cd ~/development/planerka_t2
cp .env.example .env
docker compose up --build -d
```

Backend будет доступен на `http://localhost:8000`.
Swagger: `http://localhost:8000/docs`

Проверенный smoke-сценарий:

```bash
docker compose exec backend python seed_demo.py
```

После этого можно логиниться demo-аккаунтами и открывать Swagger.

Для production используются отдельные файлы:

- `docker-compose.prod.yml`
- `deploy/nginx.prod.conf`

## Демонстрационные данные

После запуска backend:

```bash
python seed_demo.py
```

Или в Docker:

```bash
docker compose exec backend python seed_demo.py
```

Создаются демо-аккаунты:
- `admin@t2.demo / password123`
- `manager@t2.demo / password123`
- `employee1@t2.demo / password123`
- `employee2@t2.demo / password123`
- `newbie@t2.demo / password123`

## Тесты

Запуск:

```bash
./.venv/bin/python -m pytest tests/test_backend.py
```

Или через Docker:

```bash
docker compose exec backend python -m pytest tests/test_backend.py
```

Сейчас проверяется HTTP-уровень основных API-сценариев, включая auth, периоды, графики, manager/admin access и export.

## Основные endpoint'ы

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/verify`
- `GET /auth/me`
- `GET /health`
- `GET /live`
- `GET /ready`
- `GET /periods/current`
- `POST /periods`
- `POST /periods/{period_id}/close`
- `GET /periods/current/stats`
- `GET /periods/current/submissions`
- `GET /periods/history`
- `GET /schedules/me`
- `PUT /schedules/me`
- `POST /schedules/me/submit`
- `POST /schedules/validate`
- `GET /schedules/by-user/{user_id}`
- `GET /manager/schedules`
- `GET /manager/comments`
- `POST /manager/comments`
- `GET /manager/coverage`
- `GET /export/schedule`
- `GET /templates`
- `POST /templates`
- `DELETE /templates/{template_id}`
