"""The leasing agreement as a PDF — the third and heaviest closing option.

Most customers only want the offer in their inbox. Some ask for the contract
itself, and for them this renders a *draft* agreement: every term that was
agreed on the phone, in writing, with the signature blocks that a real
leasing agreement has, and an unambiguous DRAFT watermark across the front.

It is deliberately not executable. Nothing here creates an obligation: the
document says so in its title, in a box on page one, and again above the
signature lines. A voice agent must not be able to produce a binding contract
by being talked into it — see docs/SECURITY.md.

    uv run python -m cars_mailer.agreement > /tmp/agreement.pdf
"""

from __future__ import annotations

import datetime
import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from cars_leasing.model import (
    EXTRA_KM_VALUE,
    MAX_END_MILEAGE_KM,
    LeasingQuote,
)

BRAND = colors.HexColor("#00E0B5")
INK = colors.HexColor("#0F1720")
MUTED = colors.HexColor("#5B6B7A")
RULE = colors.HexColor("#E3E8EC")

DRAFT_NOTICE = (
    "This document is a <b>draft</b>. It records the terms discussed with the "
    "CarFinder24 advisor so they can be checked in writing. It is not a "
    "concluded contract, it creates no obligation for either side, and it takes "
    "effect only if the selling dealer confirms availability and a credit check "
    "is passed. Nothing has been signed."
)


def _eur(value: float | None) -> str:
    if value is None:
        return "—"
    return f"€{value:,.2f}".replace(",", " ")


def _km(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.0f} km".replace(",", " ")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=19, leading=23, textColor=INK,
            alignment=0, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontSize=9.5, leading=13, textColor=MUTED,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=11, leading=14, textColor=INK,
            spaceBefore=13, spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontSize=9, leading=13, textColor=INK,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"], fontSize=7.8, leading=11, textColor=MUTED,
        ),
        "draft": ParagraphStyle(
            "draft", parent=base["Normal"], fontSize=9, leading=13, textColor=INK,
            alignment=TA_CENTER,
        ),
    }


def _facts_table(rows: list[tuple[str, str]], strong: set[str] = frozenset()) -> Table:
    """A two-column label/value block — the shape the whole document is made of."""
    styles = _styles()
    data = [
        [
            Paragraph(label, styles["small"]),
            Paragraph(
                f"<b>{value}</b>" if label in strong else value, styles["body"]
            ),
        ]
        for label, value in rows
    ]
    table = Table(data, colWidths=[62 * mm, 103 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
            ]
        )
    )
    return table


def _watermark(canvas: Any, doc: Any) -> None:
    """DRAFT across the page, so a printed copy cannot be mistaken for a contract."""
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 92)
    canvas.setFillColor(colors.HexColor("#0F1720"))
    canvas.setFillAlpha(0.06)
    canvas.translate(A4[0] / 2, A4[1] / 2)
    canvas.rotate(38)
    canvas.drawCentredString(0, 0, "DRAFT")
    canvas.restoreState()

    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        20 * mm, 12 * mm, "CarFinder24 · draft leasing agreement · not a concluded contract"
    )
    canvas.drawRightString(190 * mm, 12 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def agreement_pdf(
    *,
    car: dict[str, Any],
    quote: LeasingQuote,
    reference: str,
    customer_name: str = "",
) -> bytes:
    """Render the draft agreement. `car` is a `car_details` result."""
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=f"CarFinder24 draft leasing agreement {reference}",
        author="CarFinder24",
        subject=car.get("title", ""),
    )
    today = datetime.datetime.now(tz=datetime.UTC).strftime("%d %B %Y")
    end_km = (car.get("mileage_km") or 0) + quote.annual_km * quote.term_months // 12

    story: list[Any] = [
        Paragraph("Leasing agreement — draft", styles["title"]),
        Paragraph(
            f"Mileage-based lease · private customer<br/>"
            f"Reference {reference} · drawn up {today}",
            styles["subtitle"],
        ),
        Spacer(1, 9),
        _notice_box(DRAFT_NOTICE),
        Paragraph("1 · Parties", styles["h2"]),
        _facts_table(
            [
                ("Lessor", "CarFinder24 Leasing (on behalf of the selling dealer)"),
                ("Selling dealer", str(car.get("seller") or "—")),
                ("Location", str(car.get("city") or "—")),
                ("Lessee", customer_name or "— (to be completed)"),
            ]
        ),
        Paragraph("2 · Vehicle", styles["h2"]),
        _facts_table(
            [
                ("Vehicle", str(car.get("title") or "—")),
                ("First registration", str(car.get("year") or "—")),
                ("Odometer at handover", _km(car.get("mileage_km"))),
                ("Fuel / transmission",
                 f"{car.get('fuel') or '—'} · {car.get('transmission') or '—'}"),
                ("Power", f"{car['power_hp']} hp" if car.get("power_hp") else "—"),
                ("Colour", str(car.get("body_color") or "—")),
                ("Listing reference", str(car.get("ref") or "—")),
                ("Listing price", _eur(car.get("price_eur"))),
            ],
            strong={"Vehicle", "Listing price"},
        ),
        Paragraph("3 · Financial terms", styles["h2"]),
        _facts_table(
            [
                ("Contract type", "Mileage-based lease, private customer"),
                ("Term", f"{quote.term_months} months"),
                ("Mileage allowance", f"{_km(quote.annual_km)} per year"),
                ("Down payment", _eur(quote.down_payment)),
                ("Monthly rate, gross incl. VAT", _eur(quote.monthly_rate)),
                ("— of which depreciation", _eur(quote.monthly_depreciation)),
                ("— of which finance charge", _eur(quote.monthly_finance)),
                ("Nominal annual rate", f"{quote.apr * 100:.2f} %"),
                ("Projected residual value at end of term", _eur(quote.residual_value)),
                ("Total payments over the term", _eur(quote.total_cost)),
                ("Excess mileage", f"€{EXTRA_KM_VALUE:.2f} per kilometre"),
                ("Projected odometer at return", _km(end_km)),
            ],
            strong={"Monthly rate, gross incl. VAT", "Total payments over the term"},
        ),
        Paragraph("4 · What is included", styles["h2"]),
        Paragraph(
            "Included: registration of the leasing contract, the mileage allowance "
            "stated above, and return of the vehicle at the end of the term in a "
            "condition consistent with normal wear.<br/>"
            "<b>Not included:</b> insurance, road tax, fuel or charging, maintenance "
            "and servicing, and tyres. The vehicle remains the property of the lessor "
            "for the whole term.",
            styles["body"],
        ),
        Paragraph("5 · End of term", styles["h2"]),
        Paragraph(
            f"The vehicle is returned to the selling dealer. Kilometres above the "
            f"allowance are settled at {EXTRA_KM_VALUE:.2f} € each; kilometres below it "
            f"are credited at the same rate. A return odometer above "
            f"{_km(MAX_END_MILEAGE_KM)} may affect the settlement. Damage beyond "
            "normal wear is assessed separately.",
            styles["body"],
        ),
        Paragraph("6 · How the rate was calculated", styles["h2"]),
        Paragraph(
            "The monthly rate is the value the vehicle is projected to lose over the "
            "term, divided by the number of months, plus a finance charge of "
            f"{quote.apr * 100:.2f} % a year on the capital bound in the vehicle. There "
            "is no arrangement fee and no administration fee. The full derivation is "
            "available on request and was read out during the call.",
            styles["body"],
        ),
        Spacer(1, 14),
        KeepTogether(
            [
                Paragraph("7 · Signatures", styles["h2"]),
                Paragraph(
                    "<b>Unsigned draft.</b> A signature below has no effect until the "
                    "selling dealer has confirmed availability and the credit check "
                    "has been completed.",
                    styles["small"],
                ),
                Spacer(1, 16),
                _signature_row(customer_name),
            ]
        ),
        Spacer(1, 14),
        Paragraph(
            "Prepared by the CarFinder24 voice advisor from a snapshot of public "
            "listings. Figures are indicative and not a credit agreement within the "
            "meaning of §§ 491 ff. BGB. Availability and final terms are confirmed by "
            f"the selling dealer. Reference {reference}.",
            styles["small"],
        ),
    ]
    doc.build(story, onFirstPage=_watermark, onLaterPages=_watermark)
    return buffer.getvalue()


def _notice_box(text: str) -> Table:
    styles = _styles()
    table = Table([[Paragraph(text, styles["draft"])]], colWidths=[165 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, BRAND),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2FBF9")),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
            ]
        )
    )
    return table


def _signature_row(customer_name: str) -> Table:
    styles = _styles()
    cell = [
        [
            Paragraph("Place, date · Lessee" + (f" ({customer_name})" if customer_name else ""),
                      styles["small"]),
            "",
            Paragraph("Place, date · CarFinder24 Leasing", styles["small"]),
        ]
    ]
    table = Table(cell, colWidths=[75 * mm, 15 * mm, 75 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (0, 0), 0.6, INK),
                ("LINEABOVE", (2, 0), (2, 0), 0.6, INK),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def agreement_filename(reference: str) -> str:
    return f"CarFinder24-draft-leasing-agreement-{reference}.pdf"


def _demo_pdf() -> bytes:
    """Render a sample agreement without touching the database or the network."""
    from cars_leasing.model import compute_quote
    from cars_mailer.offer import offer_reference

    quote = compute_quote(
        price=24_900, registration_year=2021, mileage_km=64_000, seller_type="Dealer",
        term_months=36, annual_km=15_000, down_payment=2_000, fuel_category="Diesel",
    )
    car = {
        "ref": "a1b2c3d4", "title": "BMW 320d Touring M Sport", "year": 2021,
        "mileage_km": 64_000, "fuel": "Diesel", "transmission": "Automatic",
        "power_hp": 190, "price_eur": 24_900, "city": "München",
        "seller": "Autohaus Beispiel GmbH", "body_color": "Black",
    }
    return agreement_pdf(
        car=car, quote=quote, reference=offer_reference("demo", 36, 15_000, 2_000),
        customer_name="Jan Beispiel",
    )


if __name__ == "__main__":
    import sys

    sys.stdout.buffer.write(_demo_pdf())
