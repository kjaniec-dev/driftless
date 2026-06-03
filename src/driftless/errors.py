class DriftlessError(Exception):
    """Base error for expected, user-facing failures."""


class PortfolioFileError(DriftlessError):
    """File missing or unreadable (usage error, exit code 2)."""


class PortfolioValidationError(DriftlessError):
    """Invalid content: bad JSON, schema, or business rules (exit code 1)."""
