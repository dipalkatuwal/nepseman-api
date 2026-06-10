class NepseError(Exception):
    """Base exception for all nepse-client errors."""


class NepseAuthError(NepseError):
    """Raised when authentication with nepalstock.com fails."""


class NepseRequestError(NepseError):
    """Raised on HTTP errors or unexpected response shapes."""


class NepseSymbolError(NepseError):
    """Raised when a ticker symbol cannot be resolved."""
