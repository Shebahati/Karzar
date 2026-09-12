"""Typed logistics / Postex provider exceptions. Messages must never include secrets."""

from __future__ import annotations


class LogisticsError(Exception):
    """Base domain error for Karzar logistics."""

    error_code: str = "SHIPPING_ERROR"
    retryable: bool = False

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        super().__init__(message)
        if error_code:
            self.error_code = error_code


class ShippingDataIncompleteError(LogisticsError):
    error_code = "SHIPPING_DATA_INCOMPLETE"

    def __init__(self, message: str, *, products: list[dict[str, object]]) -> None:
        super().__init__(message)
        self.products = products


class ShippingFreightRequiredError(LogisticsError):
    error_code = "SHIPPING_FREIGHT_REQUIRED"


class ShippingUnavailableError(LogisticsError):
    error_code = "SHIPPING_UNAVAILABLE"
    retryable = True


class ShippingQuoteExpiredError(LogisticsError):
    error_code = "SHIPPING_QUOTE_EXPIRED"


class ShippingDestinationInvalidError(LogisticsError):
    error_code = "SHIPPING_DESTINATION_INVALID"


class ShippingQuoteMismatchError(LogisticsError):
    error_code = "SHIPPING_QUOTE_MISMATCH"


class ShippingQuoteConsumedError(LogisticsError):
    error_code = "SHIPPING_QUOTE_CONSUMED"


class ShippingQuoteStaleError(LogisticsError):
    error_code = "SHIPPING_QUOTE_STALE"


class ShipmentNotFoundError(LogisticsError):
    error_code = "SHIPMENT_NOT_FOUND"


class ShipmentStateError(LogisticsError):
    error_code = "SHIPMENT_STATE_INVALID"


class ProviderCutoffError(LogisticsError):
    error_code = "SHIPPING_PROVIDER_CUTOFF"


class ProviderError(LogisticsError):
    """Mapped Postex HTTP failure."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "SHIPPING_PROVIDER_ERROR",
        http_status: int | None = None,
        provider_code: str | None = None,
        retryable: bool = False,
        ambiguous_write: bool = False,
    ) -> None:
        super().__init__(message, error_code=error_code)
        self.http_status = http_status
        self.provider_code = provider_code
        self.retryable = retryable
        self.ambiguous_write = ambiguous_write


class ProviderAuthenticationError(ProviderError):
    def __init__(self, message: str = "Postex authentication failed", **kwargs: object) -> None:
        super().__init__(message, error_code="SHIPPING_PROVIDER_AUTH", **kwargs)  # type: ignore[arg-type]


class ProviderValidationError(ProviderError):
    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, error_code="SHIPPING_PROVIDER_VALIDATION", **kwargs)  # type: ignore[arg-type]


class ProviderCurrencyError(ProviderError):
    """Quote response currency is present but not IRR (fail closed)."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, error_code="SHIPPING_PROVIDER_CURRENCY", **kwargs)  # type: ignore[arg-type]


class ProviderRateLimitError(ProviderError):
    def __init__(self, message: str = "Postex rate limited", **kwargs: object) -> None:
        kwargs.setdefault("retryable", True)
        super().__init__(message, error_code="SHIPPING_PROVIDER_RATE_LIMIT", **kwargs)  # type: ignore[arg-type]


class ProviderTransientError(ProviderError):
    def __init__(self, message: str, **kwargs: object) -> None:
        kwargs.setdefault("retryable", True)
        super().__init__(message, error_code="SHIPPING_PROVIDER_TRANSIENT", **kwargs)  # type: ignore[arg-type]


class ProviderTimeoutError(ProviderError):
    def __init__(self, message: str, *, ambiguous_write: bool = False, **kwargs: object) -> None:
        super().__init__(
            message,
            error_code="SHIPPING_PROVIDER_TIMEOUT",
            retryable=not ambiguous_write,
            ambiguous_write=ambiguous_write,
            **kwargs,  # type: ignore[arg-type]
        )


class ProviderAmbiguousWriteError(ProviderTimeoutError):
    """Mutating request may have reached Postex; do not retry create blindly."""

    def __init__(self, message: str, **kwargs: object) -> None:
        kwargs.setdefault("ambiguous_write", True)
        super().__init__(message, **kwargs)  # type: ignore[arg-type]


class ProviderNotFoundError(ProviderError):
    def __init__(self, message: str = "Postex resource not found", **kwargs: object) -> None:
        super().__init__(message, error_code="SHIPPING_PROVIDER_NOT_FOUND", **kwargs)  # type: ignore[arg-type]


class ProviderConflictError(ProviderError):
    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, error_code="SHIPPING_PROVIDER_CONFLICT", **kwargs)  # type: ignore[arg-type]
