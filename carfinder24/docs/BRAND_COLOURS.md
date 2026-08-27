# Brand logos: what colour is actually in the files

Read straight out of the 39 SVGs in `frontend/public/assets/` — every `fill`,
`stroke` and gradient `stop-color` they declare. Black and white are treated as
neutral and excluded, so "monochrome" below means the file contains no brand
colour at all.

## The short version

The set is not a coherent icon system. It is three different things:

1. **Photoreal crests** — Porsche, Cadillac, Chevrolet, Fiat, Alfa Romeo: dozens
   of gradients, traced from renderings. Porsche alone is **5.5 MB**.
2. **Flat, single-colour marks** — Hyundai, Suzuki, Ford, Rolls-Royce, Tesla,
   Mitsubishi. These are the useful ones.
3. **Pure black-and-white silhouettes** — BMW, Mercedes-Benz, Volvo, Honda,
   Volkswagen, Kia, Aston Martin. No brand colour to read.

Our two biggest brands, BMW and Mercedes-Benz — 58% of all listings between
them — are in group 3. So a shortlist cannot be brand-coloured from these files
even in principle.

## Brands in our dataset

| Brand | Listings | Logo | Size | Colours in the file |
|---|---:|---|---:|---|
| BMW | 15 170 | `black-white-bmw-logo_svgstack_com_33121787825166.svg` | 3 kB | *monochrome* |
| Mercedes-Benz | 11 086 | `mercedes-benz-logo_svgstack_com_33461787824578.svg` | 1 kB | *monochrome* |
| Porsche | 7 709 | `porsche-logo_svgstack_com_33531787824583.svg` | **5.4 MB** | `#821810` `#f5cb73` `#d1a04a` `#8c5c1b` `#fff8e8` |
| Audi | 5 946 | **missing** | — | — |
| Suzuki | 1 966 | `suzuki-logo_svgstack_com_33601787825204.svg` | 2 kB | `#003399` `#e20a17` |
| Volvo | 1 088 | `volvo-logo_svgstack_com_33691787825218.svg` | 2 kB | *monochrome* |
| Alfa Romeo | 1 007 | `alfa-romeo-logo_svgstack_com_33711787825171.svg` | 21 kB | `#fff38d` `#9d0d16` `#1e1d51` `#53eeef` `#2f7fbe` |
| Honda | 370 | `black-white-honda-logo_svgstack_com_33291787825276.svg` | 6 kB | *monochrome* |
| Hyundai | 268 | `hyundai-logo_svgstack_com_33301787824626.svg` | 2 kB | `#003984` |
| Volkswagen | 175 | **missing** | — | — |
| Ford | 143 | `black-white-ford-logo_svgstack_com_33281787825209.svg` | 7 kB | *monochrome* |
| Ford | 143 | `ford-logo_svgstack_com_33271787824570.svg` | 8 kB | `#003478` |
| Aston Martin | 136 | `aston-martin-logo_svgstack_com_33101787824661.svg` | 17 kB | *monochrome* |
| BYD | 111 | **missing** | — | — |
| Rolls-Royce | 95 | `rolls-royce-logo_svgstack_com_33551787825197.svg` | 9 kB | `#004990` |
| SsangYong | 58 | **missing** | — | — |
| Maserati | 57 | **missing** | — | — |
| smart | 53 | **missing** | — | — |
| Maybach | 47 | **missing** | — | — |
| Mitsubishi | 38 | `mitsubishi-logo_svgstack_com_33481787825237.svg` | 0 kB | `#e60012` |
| Opel | 36 | **missing** | — | — |
| Renault | 28 | **missing** | — | — |
| Bugatti | 8 | `bugatti-logo_svgstack_com_33151787825182.svg` | 19 kB | `#db1c30` |
| Tesla | 8 | `tesla-logo_svgstack_com_33621787825190.svg` | 1 kB | `#e82127` |
| Kia | 7 | `free-kia-logo_svgstack_com_33341787824603.svg` | 2 kB | *monochrome* |
| Dongfeng | 1 | **missing** | — | — |

## Brands with a logo but no listings

Dead weight, but harmless — keep them if the dataset ever widens:

bentley (mono), cadillac (#232e30, #9cb3cf), chevrolet (#002334, #7f5f39), citroen (#6e6e6e), cupra (mono), ferrari (#fff200, #ed1c24), fiat (#6d0115, #d3d1d2), isuzu (#e60012), jeep (mono), lamborghini (#f7de9f, #f9ce5c), landrover (mono), lexus (mono), man (mono), mazda (mono), mclaren (mono), minicooper (mono), nissan (mono), peugeot (mono), subaru (mono), togg (mono), toyota (mono), wolkswagen (mono)

## Three problems to fix before these ship

**1. Porsche is 5.5 MB.** One logo is 92% of the whole assets folder, for 17% of
the listings. It is a traced rendering with 1,626 white fills and 3 gradients —
displayed at 24 px on a card. A shortlist showing three Porsches would push
16 MB at the browser. Replace it with the flat wordmark or a simplified crest
before the demo; nothing else in the folder comes close to this.

**2. Ford ships twice, in two styles.** `ford-logo_…33271787824570.svg` is the
blue oval (`#003478`), `black-white-ford-logo_…33281787825209.svg` is the
silhouette. Pick one and delete the other, or the card renders whichever the
lookup happens to find.

**3. The filenames cannot be derived from the data.** Nothing turns
`make = "BMW"` into `black-white-bmw-logo_svgstack_com_33121787825166.svg`.
Rename them to the slugified make — `bmw.svg`, `mercedes-benz.svg`,
`alfa-romeo.svg` — and the lookup becomes one line. Note the current
`wolkswagen-logo_…svg` is misspelled, so it would miss even after renaming.

## What we would actually use them for

**Recommendation: don't tint the cards by brand.** Render every logo in the
card's ink colour and keep our own teal as the only accent.

Three reasons, and they come out of the table above:

- Twelve of our twenty-five brands have no colour in the file, and the two
  biggest are among them. Half the shortlist would be tinted and half not.
- The brands that *do* have colour mostly have the same colour: `#e60012`,
  `#e82127`, `#e20a17`, `#db1c30` are four near-identical reds. Tinting by brand
  would not even distinguish the brands.
- A shortlist is a comparison. Three cards in three brand colours read as three
  different products; three cards in one palette read as three options, which is
  what they are. Colour on that screen should mean *the monthly rate*, not the
  manufacturer.

If a brand tint is wanted anyway, take it from the file where one exists and
fall back to the card's ink colour otherwise — never guess a brand's colour from
memory, and never let a missing logo leave a blank where a card expects a mark.

## Regenerating this

```bash
uv run python - <<'PY'
import re, pathlib, collections
for f in sorted(pathlib.Path("frontend/public/assets").glob("*.svg")):
    s = f.read_text(errors="replace")
    c = collections.Counter(m.lower() for m in re.findall(
        r'(?:fill|stroke|stop-color)\s*[:=]\s*"?\s*(#[0-9a-fA-F]{3,8})', s))
    print(f.name, f.stat().st_size // 1024, "kB", c.most_common(5))
PY
```
