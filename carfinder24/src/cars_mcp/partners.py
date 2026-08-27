"""Premium partner dealers — the dealers CarFinder24 has an agreement with.

Partners are shown first. That is a commercial rule, not a quality claim, so it
is implemented where it can be inspected and tested rather than suggested to a
language model, and it is *bounded*: partners are surfaced first **within** the
cars that already match what the customer asked for. A partner car never gets
into the shortlist by being a partner car, and the ranking key the customer
chose (cheapest per month, lowest mileage, …) still decides the order among
partners and among everyone else.

The snapshot is public AutoScout24 data and carries no partner flag, so the
programme is *derived* from it, deterministically: a dealer qualifies on public
reputation and a real presence in the snapshot. Same data, same partner list,
every run. Swap `PARTNER_DDL` for a real contract table when there is one — the
rest of the code only asks `is_partner`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# -- who qualifies -----------------------------------------------------------
MIN_RATING = 4.5  # average public rating across the dealer's listings
MIN_REVIEWS = 25  # enough reviews that the rating means something
MIN_LISTINGS = 5  # a real inventory, not a one-car seller

PARTNER_TABLE = "partner_dealers"

#: Built once per connection, next to the leasing macros.
PARTNER_DDL = f"""
CREATE OR REPLACE TABLE {PARTNER_TABLE} AS
  SELECT seller_company_name AS dealer,
         count(*) AS listings,
         round(avg(ratings_average), 2) AS rating,
         max(ratings_count) AS reviews
  FROM ads
  WHERE seller_type = 'Dealer' AND seller_company_name IS NOT NULL
  GROUP BY 1
  HAVING avg(ratings_average) >= {MIN_RATING}
     AND max(ratings_count) >= {MIN_REVIEWS}
     AND count(*) >= {MIN_LISTINGS}
"""

#: SQL expression, true for a listing sold by a partner. Usable in SELECT,
#: WHERE and ORDER BY alike.
IS_PARTNER = (
    f"(seller_type = 'Dealer' AND seller_company_name IN "
    f"(SELECT dealer FROM {PARTNER_TABLE}))"
)

BADGE = "CarFinder24 partner dealer"

#: What the advisor may say about the badge — the honest version, and the only
#: version, because the model is told never to embellish it.
DISCLOSURE = (
    "Partner dealers have an agreement with CarFinder24, so we show their cars "
    "first among the ones that match you. It does not change the price or the "
    "leasing rate, and it is not a quality rating."
)


def partner_stats(query: Callable[..., list[dict[str, Any]]]) -> dict[str, Any]:
    """How large the partner network is — for logging and for the demo."""
    (row,) = query(
        f"SELECT count(*) AS dealers, coalesce(sum(listings), 0) AS listings "
        f"FROM {PARTNER_TABLE}"
    )
    return {
        "dealers": int(row["dealers"]),
        "listings": int(row["listings"]),
        "criteria": {
            "min_rating": MIN_RATING,
            "min_reviews": MIN_REVIEWS,
            "min_listings": MIN_LISTINGS,
        },
    }
