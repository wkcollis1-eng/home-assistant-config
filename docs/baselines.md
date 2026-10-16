# BASELINES (reference only — do not modify without explicit instruction)

Moved verbatim from `H:/CLAUDE.md` on 2026-10-04 (P8 of that day's concise pass)
so it loads only when a baseline is needed. A file that cites "CLAUDE.md
BASELINES" means this file.

2026-10-10 (Bill: "we should re-baseline to the bdl data"): the four
HDD-dependent lines below moved from NOAA to ACIS Bradley 2025 [M,
HARTFORD-BRADLEY, 365 days, 0 missing, queried 2026-10-10]. This reverses
the 2026-09-16 no-rebase ruling. The live helpers and the `initial:` values in
`configuration.yaml` hold the same numbers; CHANGELOG [2026.10.10] has the
derivation.

2026-10-15 (Bill: "4. yes rebase"): the Navien 220.8 behind 566.2 CCF was
THERMS. As CCF it is 212.9 [D: 220.7775 x 0.9643], so 2025 space heat is
574.1 CCF [D: 787 - 212.9]. Heating efficiency 100.6 -> 102.0, UA 585 -> 593,
DHW/heating ratio 28.1/71.9% -> 27.1/72.9% [D]. The helpers and `initial:`
again hold the same numbers; CHANGELOG [2026.10.15] has the derivation.

```
Building UA:          593 BTU/hr-°F (the ua_12m formula on 2025: 574.1 CCF,
                      3.6 MMBTU fireplace, BDL HDD59 4,230 [D]; was 585 on
                      566.2 CCF until 2026-10-15, and 493 on NOAA HDD59 5,294)
Balance point:        59°F
HDD59/HDD65 ratio:    0.751 (BDL 2025 HDD59 4,230 / HDD65 5,629 [D]; was 0.844
                      = NOAA 5,294 / 6,270)
AFUE:                 0.95
BTU/CCF:              103,700
Heating efficiency:   102.0 CCF/1k HDD65 (Navien-corrected 2025: 574.1 CCF /
                      BDL 5,629 [D]; was 100.6 on 566.2 CCF until 2026-10-15,
                      and 90.3 on 6,270)
DHW ratio:            27.1% [D: 212.9/787 CCF; Navien 220.8 Thm x 0.9643]
                      (was 28.1%, which read the 220.8 therms as CCF)
Heating ratio:        72.9% [D: 574.1/787 CCF] (was 71.9% [D: 566/787])
Annual HDD65:         5,629 (2025, ACIS BDL [M]; was 6,270, a NOAA figure 641
                      above BDL for the same year); climate normal 5,873 (BDL NCEI 1991-2020 [M: sum of 365 ACIS BDL daily normals]; the 5,270 here until 2026-09-23 was a hard-coded dict's sum, not a BDL normal)
Annual electricity:   6,730 kWh
Baseline power:       200W (quiet house)
Annual gas:           787 CCF
Site EUI:             41.7 kBTU/ft²-yr
Therms→CCF:           ×0.9643
Electric rate:        $0.29/kWh
```
