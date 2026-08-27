"""Hypothetical leasing business logic (no data or voice dependencies)."""

from cars_leasing.model import LeasingQuote, NotLeasable, compute_quote

__all__ = ["LeasingQuote", "NotLeasable", "compute_quote"]
