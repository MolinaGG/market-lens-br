from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida de variáveis de ambiente ou do arquivo .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "market-lens-br"
    database_url: str = "sqlite:///./data/market_lens.db"

    # Integrações: chaves ficam só no ambiente, nunca no código.
    apify_api_token: str | None = None
    groq_api_key: str | None = None

    # Cache: "none" por padrão; "redis" quando a camada estiver ativa.
    cache_backend: str = "none"
    redis_url: str | None = None

    forecast_horizon_pregoes: int = 14


@lru_cache
def get_settings() -> Settings:
    return Settings()
