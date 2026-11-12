from fastapi import APIRouter

from app.config import get_settings
from app.domain.universe import UNIVERSE

router = APIRouter(tags=["sistema"])


@router.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "horizon_pregoes": settings.forecast_horizon_pregoes,
        "ativos": [asset.code for asset in UNIVERSE],
        "integracoes": {
            "apify": bool(settings.apify_api_token),
            "groq": bool(settings.groq_api_key),
        },
    }
