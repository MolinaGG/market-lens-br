"""Interface de cache. Redis entra como implementação opcional."""

from typing import Protocol


class Cache(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...


class NullCache:
    """Cache desativado: nunca guarda nada."""

    def get(self, key: str) -> str | None:
        return None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        return None
