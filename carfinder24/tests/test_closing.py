"""How a conversation ends: nothing, an email, or an email with the draft PDF.

No test here sends anything — `send_email` is replaced with a recorder, which
is also the point of two of them: an invalid request must be refused *before*
the mailer is ever reached.
"""

from __future__ import annotations

import time

import pytest

from cars_leasing.model import compute_quote
from cars_mailer import mailer
from cars_mailer.agreement import agreement_filename, agreement_pdf
from cars_mailer.offer import offer_reference
from cars_mcp import server
from cars_mcp.server import car_details, search_cars


@pytest.fixture
def outbox(monkeypatch):
    """Replace the mailer with a recorder; nothing leaves the machine."""
    sent: list[dict] = []

    def fake_send(subject: str, body_html: str, attachments=None) -> str:
        sent.append({"subject": subject, "html": body_html, "attachments": attachments or []})
        return "demo@example.com"

    monkeypatch.setattr(server, "send_email", fake_send)
    server._sent.clear()  # the per-run dedupe cache
    return sent


@pytest.fixture(scope="module")
def ref() -> str:
    return search_cars(max_monthly_rate=400, limit=1)["cars"][0]["ref"]


# --- the default: an offer, no contract -------------------------------------


def test_the_plain_offer_carries_no_attachment(outbox, ref) -> None:
    result = server.email_offer(ref, 36, 15_000)
    assert result["sent"] is True
    assert result["attachment"] is None
    assert outbox[0]["attachments"] == []
    assert "@" in result["recipient"] and "demo@example.com" not in result["recipient"]


def test_the_agreement_is_attached_only_when_it_was_asked_for(outbox, ref) -> None:
    result = server.email_offer(ref, 36, 15_000, include_agreement=True)
    assert result["sent"] is True
    (filename, payload, mime) = outbox[0]["attachments"][0]
    assert filename == result["attachment"] == agreement_filename(result["reference"])
    assert mime == "application/pdf"
    assert payload.startswith(b"%PDF-")
    assert "draft" in result["contains"]


def test_the_same_offer_is_not_emailed_twice_in_a_row(outbox, ref) -> None:
    assert server.email_offer(ref, 36, 15_000)["sent"] is True
    second = server.email_offer(ref, 36, 15_000)
    assert second["sent"] is False
    assert len(outbox) == 1


def test_the_session_email_quota_is_enforced(outbox, ref) -> None:
    """A coaxed agent cannot turn one session into a mail firehose."""
    now = time.monotonic()
    server._sent[:] = [(f"filler-{i}", now) for i in range(server._MAX_EMAILS_PER_RUN)]
    refused = server.email_offer(ref, 36, 15_000)
    assert refused["sent"] is False
    assert "quota" in refused["reason"]
    assert outbox == []


# --- nothing is sent on an impossible request -------------------------------


def test_impossible_terms_are_refused_before_the_mailer_is_reached(outbox, ref) -> None:
    result = server.email_offer(ref, term_months=30, annual_km=40_000)
    assert result["sent"] is False
    assert result["options"]["term_months"] == [12, 24, 36, 48]
    assert outbox == []


def test_a_declined_car_sends_nothing(outbox, ref) -> None:
    result = server.email_offer(ref, 36, 15_000, down_payment=10_000_000)
    assert result["sent"] is False
    assert outbox == []


# --- the document itself ----------------------------------------------------


@pytest.fixture(scope="module")
def draft(ref):
    quote = compute_quote(
        price=24_900, registration_year=2021, mileage_km=64_000, seller_type="Dealer",
        term_months=36, annual_km=15_000, down_payment=2_000, fuel_category="Diesel",
    )
    reference = offer_reference("test", 36, 15_000, 2_000)
    return agreement_pdf(car=car_details(ref), quote=quote, reference=reference,
                         customer_name="Jan Beispiel")


def test_the_agreement_is_a_pdf(draft) -> None:
    assert draft.startswith(b"%PDF-")
    assert len(draft) > 2_000


def test_the_agreement_says_draft_on_its_face(draft) -> None:
    """A voice agent must not be able to produce a document that looks binding."""
    page = _page_text(draft)
    assert "DRAFT" in page  # the watermark
    assert "draft" in page  # the title
    assert "not a concluded contract" in page
    assert "Unsigned draft" in page  # above the signature lines


def test_the_agreement_states_the_terms_that_were_quoted(draft) -> None:
    page = _page_text(draft)
    assert "36 months" in page
    assert "15 000 km per year" in page
    assert "Mileage-based lease" in page


def test_the_filename_cannot_be_mistaken_for_a_signed_contract() -> None:
    assert "draft" in agreement_filename("CF24-ABC123")


def test_an_attachment_survives_the_trip_through_mime(draft) -> None:
    raw = mailer._raw_message(
        "Your offer", "<b>offer</b>", "demo@example.com",
        [("agreement.pdf", draft, "application/pdf")],
    )
    assert b"application/pdf" in raw
    assert b'filename="agreement.pdf"' in raw
    assert b"<b>offer</b>" in raw


def test_an_oversized_attachment_is_refused() -> None:
    with pytest.raises(RuntimeError, match="too large"):
        mailer._raw_message(
            "Your offer", "<b>offer</b>", "demo@example.com",
            [("huge.pdf", b"x" * (mailer.MAX_ATTACHMENT_BYTES + 1), "application/pdf")],
        )


def _page_text(pdf: bytes) -> str:
    """The words actually printed on the page, out of the compressed streams.

    Checking `b"DRAFT" in pdf` would pass on an empty document — reportlab
    compresses page content, so the only honest assertion is on the decoded
    stream.
    """
    import base64
    import re
    import zlib

    decoded = []
    for stream in re.findall(rb"stream\r?\n(.*?)endstream", pdf, re.DOTALL):
        try:
            raw = zlib.decompress(base64.a85decode(stream.strip(), adobe=True))
        except (ValueError, zlib.error):  # not a compressed text stream
            continue
        decoded.append(raw.decode("latin-1"))
    # Text is emitted as (chunk) Tj / TJ arrays; the parenthesised runs are enough.
    runs = re.findall(r"\(((?:[^()\\]|\\.)*)\)", "\n".join(decoded))
    return " ".join(run.replace("\\(", "(").replace("\\)", ")") for run in runs)
