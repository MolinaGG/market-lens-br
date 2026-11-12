"""Cliente do Apify para coleta de notícias. Implementação pendente."""


class ApifyNewsCollector:
    def __init__(self, api_token: str | None) -> None:
        self._api_token = api_token

    def is_configured(self) -> bool:
        return bool(self._api_token)
