# Car brands in the dataset

Every make in `data/autoscout24_de.parquet` — **25 brands** across **45 528 listings** (AutoScout24 Germany, snapshot 2025-11-08).

This matters for the demo. The snapshot is **premium-heavy**: BMW, Mercedes,
Porsche and Audi make up most of it, while Volkswagen — the best-selling brand
in Germany — has 175 listings. Ask the advisor for a Golf and it can offer a
handful of cars; ask for a 3 Series and it has thousands.

Columns: **Listings** in the snapshot · **Leasable** at 36 months / 15 000 km ·
**≤ €300** how many of those come in under €300 a month · **From** the cheapest
monthly rate · **Median rate** the middle monthly rate for that brand.

| Brand | Listings | Leasable | ≤ €300 | Models | Median price | From | Median rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| BMW | 15 170 | 7 764 | 1 347 | 99 | €28 460 | €122 | €463 |
| Mercedes-Benz | 11 086 | 10 990 | 1 | 116 | €57 490 | €289 | €841 |
| Porsche | 7 709 | 4 407 | 0 | 18 | €87 950 | €405 | €1 609 |
| Audi | 5 946 | 5 347 | 339 | 48 | €65 490 | €208 | €992 |
| Suzuki | 1 966 | 1 453 | 680 | 19 | €18 990 | €87 | €310 |
| Volvo | 1 088 | 308 | 88 | 20 | €17 490 | €159 | €336 |
| Alfa Romeo | 1 007 | 698 | 42 | 17 | €31 500 | €162 | €508 |
| Honda | 370 | 0 | 0 | 8 | €11 325 | — | — |
| Hyundai | 268 | 27 | 0 | 14 | €8 790 | €1 336 | €1 369 |
| Volkswagen | 173 | 36 | 27 | 34 | €9 799 | €155 | €250 |
| Ford | 143 | 45 | 32 | 27 | €10 488 | €96 | €188 |
| Aston Martin | 131 | 66 | 0 | 14 | €136 941 | €1 268 | €2 427 |
| BYD | 73 | 72 | 1 | 9 | €34 490 | €286 | €559 |
| Rolls-Royce | 73 | 34 | 0 | 12 | €308 000 | €2 753 | €5 622 |
| SsangYong | 55 | 39 | 7 | 7 | €24 990 | €154 | €406 |
| Maserati | 55 | 27 | 0 | 13 | €46 990 | €384 | €902 |
| smart | 53 | 27 | 12 | 6 | €10 070 | €104 | €489 |
| Maybach | 40 | 8 | 0 | 2 | €110 894 | €1 355 | €2 582 |
| Mitsubishi | 37 | 26 | 21 | 7 | €14 999 | €85 | €202 |
| Opel | 35 | 17 | 11 | 16 | €11 990 | €130 | €227 |
| Renault | 26 | 10 | 6 | 12 | €10 823 | €124 | €228 |
| Tesla | 8 | 7 | 3 | 2 | €23 125 | €260 | €354 |
| Bugatti | 8 | 4 | 0 | 3 | €3 927 000 | €49 568 | €78 420 |
| Kia | 7 | 6 | 3 | 5 | €24 850 | €230 | €341 |
| Dongfeng | 1 | 0 | 0 | 0 | €9 000 | — | — |

## What to say on stage

**Safe** — hundreds of leasable cars under €300 a month, so a reasonable
request always lands:

- **BMW** (1 347 under €300), **Audi** (339 under €300), **Suzuki** (680 under €300)

**Thin ice** — under 400 listings in total. The advisor will find something or
honestly say it cannot, but the shortlist will be short:

- Honda (370), Hyundai (268), Volkswagen (173), Ford (143), Aston Martin (131), BYD (73), Rolls-Royce (73), SsangYong (55), Maserati (55), smart (53), Maybach (40), Mitsubishi (37), Opel (35), Renault (26), Tesla (8), Bugatti (8), Kia (7), Dongfeng (1)

**If someone asks whether the snapshot is representative:** it is a
premium-skewed slice of AutoScout24, so the share of inventory under €300 a
month is *understated* here. On a representative sample the affordability
argument gets stronger, not weaker.

## Two surprises in the table, both verified

**Honda: 370 listings, zero leasable.** The median Honda here is a 2014 with
103,000 km. Over a 36-month term it would be fifteen years old at return, past
the ten-year limit in the leasing model — so every single one is declined. Ask
the advisor for a Honda and it will correctly tell you it has nothing. That is
the eligibility model working, but it is not something to discover on stage.

**Hyundai: median price €8,790, cheapest rate €1,336 a month.** The cheap
Hyundais are 2014 i20s with 250,000–330,000 km, excluded on age and mileage.
What survives is brand-new IONIQ 9s at €78,790. So the brand looks cheap in the
price column and absurd in the rate column, and both are right.

The general rule these two illustrate: **the price column describes the
snapshot, the rate columns describe what you can actually lease.** They diverge
wherever a brand's cheap stock is old and worn out.

## Models per brand

The eight most common models for each brand, with listing counts.

**BMW** — X3 (1 163), 320 (1 151), X5 (1 150), X1 (936), 530 (831), 520 (814), 118 (631), 318 (544)

**Mercedes-Benz** — A 200 (609), GLA 200 (562), CLA 200 (538), GLC 220 (514), GLB 200 (488), GLE 450 (485), GLC 200 (468), GLC 300 (455)

**Porsche** — Cayenne (1 937), 992 (1 194), Macan (1 114), Panamera (714), Taycan (552), 991 (449), 911 (435), Boxster (420)

**Audi** — A6 (980), Q5 (659), A5 (456), Q7 (413), Q8 (360), RS3 (323), A4 (298), Q3 (290)

**Suzuki** — Swift (582), Vitara (465), S-Cross (176), SX4 S-Cross (129), Ignis (125), Jimny (125), None (70), Swace (63)

**Volvo** — XC60 (206), V60 (139), XC90 (131), XC40 (109), V40 (95), V70 (92), V90 (53), V50 (49)

**Alfa Romeo** — Stelvio (273), Giulia (214), Tonale (166), Junior (112), Giulietta (73), MiTo (33), 159 (33), 147 (18)

**Honda** — Civic (130), CR-V (92), Jazz (90), HR-V (26), Accord (19), Insight (7), CR-Z (5), FR-V (1)

**Hyundai** — i20 (49), iX35 (49), i10 (41), i30 (30), IONIQ 9 (25), SANTA FE (23), iX20 (22), i40 (15)

**Volkswagen** — Golf (41), Tiguan (25), Polo (20), Touran (15), Sharan (7), Caddy (6), Taigo (5), Passat (5)

**Ford** — Focus (27), Fiesta (21), Kuga (12), EcoSport (9), S-Max (8), Mondeo (8), Galaxy (6), Transit Custom (5)

**Aston Martin** — V8 (28), DBX (18), DB11 (14), Vanquish (12), Vantage (11), DB12 (10), DBS (9), DB9 (9)

**BYD** — Seal (31), Seal U (26), Atto 3 (16), Dolphin (13), Sealion 7 (9), Atto 2 (6), Dolphin Surf (5), Tang (2)

**Rolls-Royce** — Cullinan (26), Ghost (20), Spectre (9), Wraith (8), Phantom (7), Silver Shadow (7), Corniche (5), Dawn (3)

**SsangYong** — Rexton (20), Korando (12), Tivoli (12), Torres (7), Musso (5), Rodius (1), Actyon (1)

**Maserati** — Ghibli (16), Levante (9), GranTurismo (8), MC20 (6), Grecale (4), 4200 (3), GranCabrio (2), Spyder (2)

**smart** — forTwo (30), forFour (9), #1 (7), #3 (4), #5 (2), roadster (1)

**Maybach** — None (24), 57 (21), 62 (2)

**Mitsubishi** — Eclipse Cross (12), Space Star (11), ASX (5), Outlander (5), L200 (2), Colt (2), Pajero (1)

**Opel** — Mokka (6), Astra (5), Zafira (4), Frontera (3), Corsa (3), Meriva (2), Antara (2), Insignia (2)

**Renault** — Megane (9), Captur (4), Clio (3), Austral (3), Scenic (2), Wind (1), Twingo (1), Koleos (1)

**Tesla** — Model 3 (6), Model Y (2)

**Bugatti** — Chiron (5), Divo (1), None (1), Veyron (1)

**Kia** — Sportage (2), Ceed / cee'd (2), Stinger (1), e-Niro (1), Niro (1)

**Dongfeng** — None (1)

## Regenerating this

```bash
uv run python -c "
from cars_mcp.server import get_db
for r in get_db().query('SELECT make, count(*) n FROM ads GROUP BY 1 ORDER BY n DESC'):
    print(r)"
```
