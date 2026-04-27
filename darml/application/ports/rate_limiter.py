from abc import ABC, abstractmethod

from darml.domain.api_key import APIKey


class RateLimiterPort(ABC):
    """Per-key daily counter. Implementations: in-memory, Redis, DB."""

    @abstractmethod
    def consume(self, api_key: APIKey) -> tuple[bool, int]:
        """Try to take 1 unit of quota for today.

        Returns (allowed, remaining). For unlimited tiers: (True, -1).
        """
