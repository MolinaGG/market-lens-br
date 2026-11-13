from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, research
from app.config import get_settings


def create_app(snapshot_path: Path | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.state.snapshot_path = snapshot_path or Path(settings.database_url.removeprefix("sqlite:///"))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(research.router, prefix="/api")
    return app


app = create_app()
