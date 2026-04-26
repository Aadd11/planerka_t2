# T2 Schedule Planner API

## Описание

- регистрация и логин пользователей;
- подтверждение пользователей;
- периоды сбора графиков по группам;
- сохранение и отправку расписаний;
- backend-валидацию норм рабочего времени;
- комментарии руководителя;
- почасовое покрытие;
- экспорт в Excel;
- демонстрационные данные.

## Возможности текущей версии
- роли: `employee`, `manager`, `admin`;
- привязка данных к группе через поле `alliance` в модели и термин “Группа” в продуктовой логике;
- мультиинтервальные рабочие дни;
- комментарии на день и на весь график;
- draft/submitted через `schedule_submissions`;
- правила валидации для `adult`, `minor_student`, `minor_not_student`;
- контроль доступа руководителя только в рамках своей группы.

## Стек
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- openpyxl
- pytest

## Структура
- [app.py](./app.py) — сборка FastAPI приложения и метаданные OpenAPI.
- [routes_auth.py](./routes_auth.py) — endpoint'ы аутентификации.
- [routes_schedule.py](./routes_schedule.py) — графики и валидация.
- [routes_manager.py](./routes_manager.py) — endpoint'ы руководителя.
- [routes_periods.py](./routes_periods.py) — периоды и статистика.
- [routes_admin.py](./routes_admin.py) — управление пользователями.
- [routes_export.py](./routes_export.py) — экспорт в Excel.
- [schedule_service.py](./schedule_service.py) — нормализация и логика валидации.
- [seed_demo.py](./seed_demo.py) — генерация демонстрационных данных.
- [tests/test_backend.py](./tests/test_backend.py) — backend-тесты.

## OpenAPI / Swagger
После запуска backend доступны:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- схема OpenAPI: `http://localhost:8000/openapi.json`

В Swagger уже добавлены:
- summaries и descriptions для ключевых маршрутов;
- примеры payload для register, login, validate, period create и manager comment;
- группировка endpoint'ов по тегам.

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

## Инструкция по деплою
Минимальный production-подобный сценарий для backend:

1. Подготовьте PostgreSQL и создайте базу.
2. Выставьте env:
   `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ORIGINS`.
3. Примените миграции:

```bash
alembic upgrade head
```

4. Запустите сервис через uvicorn/gunicorn:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

5. За reverse proxy:
- проксируйте `/docs`, `/redoc`, `/openapi.json` только если это допустимо для среды;
- ограничьте `CORS_ORIGINS`;
- храните `JWT_SECRET_KEY` вне репозитория.

## Docker
Текущая compose-конфигурация поднимает только backend-часть:
- `postgres`
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

Что покрыто:
- регистрация и логин;
- employee access control;
- manager group isolation;
- manager comments;
- запрет сотруднику менять manager comment;
- валидация графика;
- adult warning;
- minor weekly error;
- minor night work error;
- export.

## Основные endpoint'ы
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/verify`
- `GET /auth/me`
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
