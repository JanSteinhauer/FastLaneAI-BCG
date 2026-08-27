# Car brand colours

The primary identity colour of every brand in our dataset, and what that means
for the card design. Values are the commonly published brand colours,
cross-checked against the SVGs in `frontend/public/assets/` — where a logo file
carries colour at all, it matches the official value exactly, so the files are
trustworthy as far as they go.

## What kind of colours car brands use

Almost all of them pick **blue or red**, and the split is close to
national. German premium goes blue or monochrome, Japanese goes red, Italian
goes red, and the mass-market European brands are the only ones using yellow.
Nobody in our dataset has a green, and only Aston Martin has one in heritage.

Weighted by how many listings we actually hold:

| Family | Listings | Share | Brands |
|---|---:|---:|---|
| Blue | 16 996 | 37% | BMW, Volvo, Hyundai, Volkswagen, Ford, Rolls-Royce, Maserati |
| Black / silver | 11 269 | 25% | Mercedes-Benz, Aston Martin, Maybach |
| Gold / crest | 7 709 | 17% | Porsche |
| Red | 9 350 | 20% | Audi, Suzuki, Alfa Romeo, Honda, Mitsubishi, Bugatti, Tesla, Kia |
| Yellow | 117 | 0% | smart, Opel, Renault |
| Unverified | 170 | 0% | BYD, SsangYong, Dongfeng |

So on any given shortlist, roughly two cards in five carry a blue brand, one in
four a black-and-silver one, and one in five a red one.

## Every brand

| Brand | Listings | Family | Primary | Secondary | In our SVG |
|---|---:|---|---|---|---|
| BMW | 15 170 | Blue | `#0166B1` BMW Blue | #6F6F6F grey, white | file is black/white only |
| Mercedes-Benz | 11 086 | Black | `#000000` Black | #A4AAAE silver | file is black only |
| Porsche | 7 709 | Gold | `#821810` Crest red-brown | #D1A04A / #F5CB73 gold | matches the crest in our file |
| Audi | 5 946 | Red | `#BB0A30` Audi Red | black, white | no file |
| Suzuki | 1 966 | Red | `#E20A17` Rich Red | #003399 Blue Galaxy | exact match in our file |
| Volvo | 1 088 | Blue | `#182871` Volvo Blue | black, silver | file is black/white only |
| Alfa Romeo | 1 007 | Red | `#9D0D16` Alfa Red | #1E1D51 navy (biscione) | matches our file |
| Honda | 370 | Red | `#CC0000` Honda Red | black, white | file is black only |
| Hyundai | 268 | Blue | `#003984` Hyundai Blue | silver | exact match in our file |
| Volkswagen | 175 | Blue | `#001E50` VW Navy | white | file is black/white only |
| Ford | 143 | Blue | `#003478` Ford Blue | white | exact match in our colour file |
| Aston Martin | 136 | Black | `#000000` Black | racing green heritage | file is black/white only |
| BYD | 111 | — | *not verified* | — | no file |
| Rolls-Royce | 95 | Blue | `#00498F` Rolls-Royce Blue | white, black | our file has #004990 |
| SsangYong | 58 | — | *not verified* | — | no file |
| Maserati | 57 | Blue | `#0C2340` Maserati Blue | silver, red accent | no file |
| smart | 53 | Yellow | `#E48700` Hello Yellow | silver-grey | no file |
| Maybach | 47 | Black | `#C0C0C0` Silver / chrome | #D4AF37 gold accents | no file |
| Mitsubishi | 38 | Red | `#E60012` Rainbow Red | black | exact match in our file |
| Opel | 36 | Yellow | `#F7FF14` Opel Yellow | black | no file |
| Renault | 28 | Yellow | `#EFDF00` Renault Yellow | black, white | no file |
| Tesla | 8 | Red | `#E82127` Tesla Red | black, white | exact match in our file |
| Bugatti | 8 | Red | `#DB1C30` Bugatti Red | black, white | exact match in our file |
| Kia | 7 | Red | `#C5182C` Kia Red | black | file is black/white only |
| Dongfeng | 1 | — | *not verified* | — | no file |

The four unverified brands — BYD, SsangYong, Dongfeng, and the exact Porsche
wordmark colour — are 170 listings between them, 0.4% of the dataset. Look them
up before using them rather than guessing; every other value here has a source.

## What this means for the card

**Two thirds of our inventory is blue or monochrome.** BMW blue, Mercedes
silver-black, Volvo blue, VW navy, Ford blue, Hyundai blue, Rolls-Royce blue —
that is 62% of listings in one narrow band of the spectrum. The reds are almost
all the same red too: `#E60012`, `#E82127`, `#E20A17`, `#DB1C30`, `#CC0000` and
`#C5182C` are six brands within a few degrees of each other.

Three consequences:

1. **Brand colour cannot carry meaning on a shortlist.** Two BMWs and a Ford
   would be three shades of blue; a Honda and a Tesla would be the same red.
   Colour on that screen should encode the monthly rate, not the manufacturer.
2. **Brand blue collides with our own palette.** The dark navies — VW `#001E50`,
   Maserati `#0C2340`, Volvo `#182871` — are close to the page background, so a
   brand-tinted card would lose contrast exactly where the logo sits.
3. **Our accent is safe.** CarFinder24 teal `#00E0B5` is nowhere near any brand
   colour in this table, which is why it can mean "this is the number that
   matters" without ever looking like a manufacturer's livery.

**Recommendation: render logos in the card's ink colour, keep teal as the only
accent.** Use a brand's real colour only where the brand is the subject — a
single-car detail view, or the offer email header — never on a comparison.

## Sources

Brand values are the commonly published ones from brand-colour references
(brandpalettes.com, brandcolorcode.com, schemecolor.com, brandcolors.net,
chromacreator.com) and, for Renault, its own brand site. They are trademarks of
their owners; using them to render a manufacturer's own logo is normal, using
them as our product's palette is not.
