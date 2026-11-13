from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida de variáveis de ambiente ou do arquivo .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "market-lens-br"
    database_url: str = "sqlite:///./data/market_lens.db"
    local_equity_database_url: str = "sqlite:///./data/local_equity.db"
    company_news_database_url: str = "sqlite:///./data/company_news.db"
    local_import_enabled: bool = False

    # Integrações: chaves ficam só no ambiente, nunca no código.
    apify_api_token: str | None = None
    groq_api_key: str | None = None

    # Cache: "none" por padrão; "redis" quando a camada estiver ativa.
    cache_backend: str = "none"
    redis_url: str | None = None

    forecast_horizon_pregoes: int = 14

    # Origens permitidas no CORS, separadas por vírgula. Ex.: https://seu-site.vercel.app
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
