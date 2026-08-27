"""Email sending via Amazon SES (no data or voice dependencies)."""

from cars_mailer.mailer import SENDER, EmailNotConfigured, send_email

__all__ = ["SENDER", "EmailNotConfigured", "send_email"]
