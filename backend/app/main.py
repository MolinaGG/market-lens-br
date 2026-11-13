from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import company, health, local, research
from app.config import get_settings


def create_app(snapshot_path: Path | None = None, local_import_enabled: bool | None = None, local_equity_path: Path | None = None, news_path: Path | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.state.snapshot_path = snapshot_path or Path(settings.database_url.removeprefix("sqlite:///"))
    app.state.local_equity_path = local_equity_path or Path(settings.local_equity_database_url.removeprefix("sqlite:///"))
    app.state.news_path = news_path or Path(settings.company_news_database_url.removeprefix("sqlite:///"))
    app.state.local_import_enabled = settings.local_import_enabled if local_import_enabled is None else local_import_enabled
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(research.router, prefix="/api")
    app.include_router(local.router, prefix="/api")
    app.include_router(company.router, prefix="/api")
    return app


app = create_app()
