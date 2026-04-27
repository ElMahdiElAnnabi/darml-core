from abc import ABC, abstractmethod


class EmailDeliveryPort(ABC):
    """Send transactional email. Implementations: Resend, Postmark, SES, stderr."""

    @abstractmethod
    def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> bool:
        """Returns True on accepted-for-delivery; False on hard failure.

        Soft failures (provider 5xx, network) MUST be retried by the caller;
        the port does not own retry logic so callers can pick their policy.

        text_body is the plain-text alternative (improves spam scoring +
        accessibility). Optional — adapters that can't carry both formats
        may ignore it.
        """
