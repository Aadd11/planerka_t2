from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from config import settings
from db import check_db_connection
from routes_admin import router as admin_router
from routes_auth import router as auth_router
from routes_export import router as export_router
from routes_manager import router as manager_router
from routes_periods import router as periods_router
from routes_schedule import router as schedule_router
from routes_templates import router as templates_router


def create_app() -> FastAPI:
    settings.validate_security()
    app = FastAPI(
        title="T2 Schedule Planner API",
        description=(
            "Backend API для T2 Schedule Planner. "
            "Поддерживает регистрацию и логин, периоды сбора, "
            "расписания сотрудников, backend-валидацию норм рабочего времени, "
            "комментарии руководителя, coverage и экспорт."
        ),
        version="2.1.0",
        contact={"name": "T2 Schedule Planner Hackathon Team"},
        openapi_tags=[
            {"name": "auth", "description": "Регистрация, логин, верификация и профиль текущего пользователя."},
            {"name": "schedules", "description": "Черновики, отправка и проверка графиков сотрудников."},
            {"name": "periods", "description": "Управление периодами сбора графиков и статистикой по ним."},
            {"name": "manager", "description": "Инструменты руководителя: матрица, комментарии, coverage."},
            {"name": "admin", "description": "Управление пользователями, ролями и группами."},
            {"name": "export", "description": "Экспорт графиков в Excel."},
            {"name": "templates", "description": "Шаблоны повторяющихся графиков сотрудника."},
            {"name": "system", "description": "Технические служебные маршруты."},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        if settings.is_production_like:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.get("/health", tags=["system"])
    def health_check():
        return {"status": "ok", "env": settings.APP_ENV}

    @app.get("/live", tags=["system"])
    def live_check():
        return {"status": "alive"}

    @app.get("/ready", tags=["system"])
    def ready_check():
        if not check_db_connection():
            return Response(
                content='{"status":"not_ready","database":"unreachable"}',
                status_code=503,
                media_type="application/json",
            )
        return {"status": "ready", "database": "ok"}

    app.include_router(auth_router)
    app.include_router(schedule_router)
    app.include_router(periods_router)
    app.include_router(manager_router)
    app.include_router(admin_router)
    app.include_router(export_router)
    app.include_router(templates_router)
    return app


app = create_app()
