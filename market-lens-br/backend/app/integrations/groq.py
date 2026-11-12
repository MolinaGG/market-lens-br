"""Cliente do Groq para interpretação estruturada. Implementação pendente."""


class GroqInterpreter:
    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def is_configured(self) -> bool:
        return bool(self._api_key)
