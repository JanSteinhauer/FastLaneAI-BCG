"""Minimal email sending via Amazon SES.

Configuration comes from the environment / .env:

    AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY  IAM user scoped to ses:SendEmail
    AWS_REGION       region of the verified SES identity (e.g. eu-central-1)
    EMAIL_RECIPIENT  fixed destination address (the demo visitor's inbox)

The sender is fixed below: it is the SES-verified identity the IAM policy is
scoped to, so it is not configurable. SES enforces the limits server-side
anyway: in sandbox mode this app can only send from verified identities to
verified recipients, regardless of what the code asks for.

Attachments (the draft leasing agreement) switch the call to SES's raw MIME
mode; everything else about the send is unchanged, including the fixed
recipient.
"""

from __future__ import annotations

import os
from email.message import EmailMessage

import boto3
from botocore.exceptions import BotoCoreError, ClientError

SENDER = "typists.raptor.8s@icloud.com"

_REQUIRED_VARS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_REGION",
    "EMAIL_RECIPIENT",
)


class EmailNotConfigured(RuntimeError):
    """Raised when the required environment variables are missing."""


def _config() -> dict[str, str]:
    values = {name: os.getenv(name, "") for name in _REQUIRED_VARS}
    if missing := [name for name, value in values.items() if not value]:
        raise EmailNotConfigured(
            f"Email is not configured — missing in .env: {', '.join(missing)}"
        )
    return values


#: (filename, bytes, mime type) — what send_email() accepts as an attachment.
Attachment = tuple[str, bytes, str]

MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024  # SES caps the whole message at 10 MB


def send_email(
    subject: str,
    body_html: str,
    attachments: list[Attachment] | None = None,
) -> str:
    """Send an HTML email to the configured recipient; returns its address.

    Raises EmailNotConfigured when env vars are missing, RuntimeError when
    SES rejects the request or cannot be reached.
    """
    cfg = _config()
    # Explicit credentials: the agent machine may carry ambient AWS profiles
    # for other projects — this client must only ever use the scoped key.
    client = boto3.client(
        "sesv2",
        region_name=cfg["AWS_REGION"],
        aws_access_key_id=cfg["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=cfg["AWS_SECRET_ACCESS_KEY"],
    )
    if attachments:
        content = {"Raw": {"Data": _raw_message(
            subject, body_html, cfg["EMAIL_RECIPIENT"], attachments
        )}}
    else:
        content = {
            "Simple": {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": body_html, "Charset": "UTF-8"}},
            }
        }
    try:
        client.send_email(
            FromEmailAddress=SENDER,
            Destination={"ToAddresses": [cfg["EMAIL_RECIPIENT"]]},
            Content=content,
        )
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"SES send failed: {e}") from e
    return cfg["EMAIL_RECIPIENT"]


def _raw_message(
    subject: str, body_html: str, recipient: str, attachments: list[Attachment]
) -> bytes:
    """A MIME message with attachments, for SES's raw send path."""
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SENDER
    message["To"] = recipient
    message.set_content(
        "Your CarFinder24 offer is attached. Please open this message in an "
        "email client that displays HTML."
    )
    message.add_alternative(body_html, subtype="html")
    for filename, payload, mime in attachments:
        if len(payload) > MAX_ATTACHMENT_BYTES:
            raise RuntimeError(f"attachment {filename} is too large to send")
        maintype, _, subtype = mime.partition("/")
        message.add_attachment(
            payload, maintype=maintype, subtype=subtype or "octet-stream",
            filename=filename,
        )
    return message.as_bytes()
