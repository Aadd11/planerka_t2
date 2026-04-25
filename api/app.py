from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import Base, engine
from routes_admin import router as admin_router
from routes_auth import router as auth_router
from routes_export import router as export_router
from routes_manager import router as manager_router
from routes_periods import router as periods_router
from routes_schedule import router as schedule_router
from routes_templates import router as templates_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="T2 Schedule Planner API",
        description="REST API for T2 Schedule Planner demo product",
        version="2.0.0",
    )

    Base.metadata.create_all(bind=engine)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    def health_check():
        return {"status": "ok", "env": settings.APP_ENV}

    app.include_router(auth_router)
    app.include_router(schedule_router)
    app.include_router(periods_router)
    app.include_router(manager_router)
    app.include_router(admin_router)
    app.include_router(export_router)
    app.include_router(templates_router)
    return app


app = create_app()
