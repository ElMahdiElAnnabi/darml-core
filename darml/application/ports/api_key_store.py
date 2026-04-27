from abc import ABC, abstractmethod

from darml.domain.api_key import APIKey


class APIKeyStorePort(ABC):
    """Lookup API keys by their secret. Implementations may go to env, file, DB."""

    @abstractmethod
    def find(self, key: str) -> APIKey | None: ...
