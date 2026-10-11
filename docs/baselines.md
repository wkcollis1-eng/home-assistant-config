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

```
Building UA:          585 BTU/hr-°F (the ua_12m formula on 2025: 566.2 CCF,
                      3.6 MMBTU fireplace, BDL HDD59 4,230 [D]; was 493 on
                      NOAA HDD59 5,294)
Balance point:        59°F
HDD59/HDD65 ratio:    0.751 (BDL 2025 HDD59 4,230 / HDD65 5,629 [D]; was 0.844
                      = NOAA 5,294 / 6,270)
AFUE:                 0.95
BTU/CCF:              103,700
Heating efficiency:   100.6 CCF/1k HDD65 (Navien-corrected 2025: 566.2 CCF /
                      BDL 5,629 [D]; was 90.3 on 6,270)
DHW ratio:            28.1% (220.8/787 CCF Navien-metered)
Heating ratio:        71.9% (566/787 CCF)
Annual HDD65:         5,629 (2025, ACIS BDL [M]; was 6,270, a NOAA figure 641
                      above BDL for the same year); climate normal 5,873 (BDL NCEI 1991-2020 [M: sum of 365 ACIS BDL daily normals]; the 5,270 here until 2026-09-23 was a hard-coded dict's sum, not a BDL normal)
Annual electricity:   6,730 kWh
Baseline power:       200W (quiet house)
Annual gas:           787 CCF
Site EUI:             41.7 kBTU/ft²-yr
Therms→CCF:           ×0.9643
Electric rate:        $0.29/kWh
```
