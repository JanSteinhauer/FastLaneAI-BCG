"""The offer email: car summary + leasing agreement, as self-contained HTML.

Kept separate from `mailer.py` (which only knows how to send) so the document
can be rendered and eyeballed without sending anything:

    uv run python -m cars_mailer.offer > /tmp/offer.html

Everything the customer is promised on the phone appears here in writing: the
car, the condition facts, every number behind the rate, and what the agreement
covers. Inline styles only — email clients ignore stylesheets.
"""

from __future__ import annotations

import hashlib
import datetime
from typing import Any

from cars_leasing.model import (
    EXTRA_KM_VALUE,
    LeasingQuote,
    MAX_END_MILEAGE_KM,
)

BRAND = "#00E0B5"
INK = "#0f1720"
MUTED = "#5b6b7a"


def offer_reference(car_id: str, term_months: int, annual_km: int, down_payment: int) -> str:
    """Stable, human-readable reference — same deal, same reference."""
    digest = hashlib.sha1(
        f"{car_id}|{term_months}|{annual_km}|{down_payment}".encode()
    ).hexdigest()[:6].upper()
    return f"CF24-{digest}"


def _eur(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f} €".replace(",", " ")


def _row(label: str, value: str, strong: bool = False) -> str:
    weight = "600" if strong else "400"
    return (
        f'<tr><td style="padding:7px 0;color:{MUTED};font-size:14px">{label}</td>'
        f'<td style="padding:7px 0;text-align:right;color:{INK};font-size:14px;'
        f'font-weight:{weight}">{value}</td></tr>'
    )


def offer_email_html(
    *,
    car: dict[str, Any],
    quote: LeasingQuote,
    reference: str,
    customer_name: str = "",
) -> str:
    """Render the offer. `car` is a `car_details` result, `quote` the authoritative quote."""
    greeting = f"Hallo {customer_name}," if customer_name else "Hallo,"
    today = datetime.date.today().strftime("%d.%m.%Y")
    spec = " · ".join(
        str(x)
        for x in (
            car.get("year"),
            f"{car['mileage_km']:,} km".replace(",", " ") if car.get("mileage_km") else None,
            car.get("fuel"),
            car.get("transmission"),
            f"{car['power_hp']} hp" if car.get("power_hp") else None,
        )
        if x
    )
    condition = " · ".join(
        x
        for x in (
            "accident-free" if car.get("had_accident") is False else None,
            "full service history" if car.get("full_service_history") else None,
            f"{car['previous_owners']} previous owner(s)"
            if car.get("previous_owners") is not None
            else None,
            "non-smoking" if car.get("non_smoking") else None,
        )
        if x
    )
    equipment = ", ".join(e for e in (car.get("equipment") or []) if e)
    end_km = car.get("mileage_km", 0) + quote.annual_km * quote.term_months // 12

    return f"""\
<div style="margin:0;padding:24px 12px;background:#f4f6f8;font-family:-apple-system,
     'Segoe UI',Roboto,Helvetica,Arial,sans-serif">
 <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:14px;
      overflow:hidden;border:1px solid #e3e8ec">

  <div style="padding:22px 28px;background:{INK};color:#fff">
   <div style="font-size:19px;font-weight:700;letter-spacing:-.3px">CarFinder24</div>
   <div style="font-size:13px;color:{BRAND};margin-top:3px">
     Your leasing offer · {reference} · {today}</div>
  </div>

  <div style="padding:26px 28px">
   <p style="margin:0 0 16px;color:{INK};font-size:15px">{greeting}</p>
   <p style="margin:0 0 22px;color:{MUTED};font-size:14px;line-height:1.55">
     thank you for talking to CarFinder24. Here is the car we discussed and the
     leasing agreement we put together for it.</p>

   <div style="border:1px solid #e3e8ec;border-radius:10px;padding:18px 20px;margin-bottom:22px">
    <div style="font-size:17px;font-weight:700;color:{INK}">{car.get('title', '')}</div>
    <div style="font-size:13px;color:{MUTED};margin-top:5px">{spec}</div>
    <div style="font-size:13px;color:{MUTED};margin-top:3px">
      {car.get('city', '')}{' · ' + car['seller'] if car.get('seller') else ''}</div>
    {f'<div style="font-size:13px;color:{INK};margin-top:11px">{condition}</div>' if condition else ''}
    {f'<div style="font-size:12.5px;color:{MUTED};margin-top:7px">{equipment}</div>' if equipment else ''}
    <div style="margin-top:14px;padding-top:13px;border-top:1px solid #eef1f4;
         font-size:14px;color:{MUTED}">
      Listing price <span style="color:{INK};font-weight:600">{_eur(car.get('price_eur'))}</span></div>
   </div>

   <div style="background:{INK};border-radius:10px;padding:20px 22px;color:#fff;margin-bottom:22px">
    <div style="font-size:13px;color:{BRAND};text-transform:uppercase;letter-spacing:.7px">
      Your monthly rate</div>
    <div style="font-size:34px;font-weight:700;margin-top:5px;letter-spacing:-1px">
      {_eur(quote.monthly_rate)}<span style="font-size:15px;font-weight:400;
      color:#9fb0bd"> / month</span></div>
   </div>

   <div style="font-size:15px;font-weight:700;color:{INK};margin-bottom:6px">
     Leasing agreement</div>
   <table style="width:100%;border-collapse:collapse;margin-bottom:22px">
    {_row("Contract type", "Kilometerleasing, private customer")}
    {_row("Term", f"{quote.term_months} months")}
    {_row("Mileage allowance", f"{quote.annual_km:,} km / year".replace(",", chr(8239)))}
    {_row("Down payment", _eur(quote.down_payment))}
    {_row("Monthly rate (gross, incl. VAT)", _eur(quote.monthly_rate), strong=True)}
    {_row("— of which depreciation", _eur(quote.monthly_depreciation))}
    {_row("— of which finance charge", _eur(quote.monthly_finance))}
    {_row("Nominal annual rate", f"{quote.apr * 100:.2f} %")}
    {_row("Projected residual value at end of term", _eur(quote.residual_value))}
    {_row("Total payments over the term", _eur(quote.total_cost), strong=True)}
    {_row("Excess mileage", f"{EXTRA_KM_VALUE:.2f} € per extra km")}
    {_row("Odometer at end of term (projected)", f"{end_km:,} km".replace(",", chr(8239)))}
   </table>

   <div style="border-left:3px solid {BRAND};padding:2px 0 2px 13px;margin-bottom:22px">
    <div style="font-size:13px;color:{MUTED};line-height:1.55">
     Included: registration of the leasing contract, the mileage allowance above,
     and return of the vehicle at the end of the term in a condition consistent
     with normal wear. Not included: insurance, road tax, fuel or charging,
     maintenance, and tyres. The vehicle remains the property of the lessor.
     Return mileage above {MAX_END_MILEAGE_KM:,} km may affect the settlement.
    </div>
   </div>

   <p style="margin:0 0 6px;color:{MUTED};font-size:12.5px;line-height:1.55">
    This is a non-binding indicative offer generated by the CarFinder24 voice
    advisor from a snapshot of public listings. It is not a credit agreement and
    contains no acceptance of a contract. Availability and final terms are
    confirmed by the selling dealer, subject to a credit check.
   </p>
   <p style="margin:0;color:{MUTED};font-size:12.5px">Reference {reference}</p>
  </div>
 </div>
</div>
""".replace("{:,}", "")


def _demo_html() -> str:
    """Render a sample offer without touching the database or the network."""
    from cars_leasing.model import compute_quote

    quote = compute_quote(
        price=24_900, registration_year=2021, mileage_km=64_000,
        seller_type="Dealer", term_months=36, annual_km=15_000, down_payment=2_000,
        fuel_category="Diesel",
    )
    car = {
        "title": "BMW 320d Touring M Sport", "year": 2021, "mileage_km": 64_000,
        "fuel": "Diesel", "transmission": "Automatic", "power_hp": 190,
        "price_eur": 24_900, "city": "München", "seller": "Autohaus Beispiel GmbH",
        "had_accident": False, "full_service_history": True, "previous_owners": 1,
        "non_smoking": True,
        "equipment": ["Navigation system", "Heated seats", "LED headlights", "Parking sensors"],
    }
    return offer_email_html(car=car, quote=quote, reference=offer_reference("demo", 36, 15_000, 2_000),
                            customer_name="Jan")


if __name__ == "__main__":
    print(_demo_html())
