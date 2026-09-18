# ofgem-curate-response — supporting analysis

Independent analysis and writing on UK data-centre grid connections, water use and infrastructure
constraints. The core of it is evidence behind two public submissions: a response to Ofgem's "Curate —
Demand Connections Reform" consultation (2026), and written evidence to the House of Commons Data Centres
APPG's inaugural inquiry. All work here was produced independently, in a personal capacity, not on behalf
of any developer, DNO, vendor, or other stakeholder.

This repository exists so specific figures in the submissions and articles below can be checked against
the code, data and sources that produced them, rather than taken on trust.

## What's here

**TNUoS tariff-band modelling** (`scripts/tnuos_full_bands.py`, `scripts/build_charts.py`)
Models where a real 40MW+ site (DataVita's DV1 facility) and a smaller 5MW site sit within NESO's
published transmission-charging bands, and the capacity cut each would need to reach the band below —
the "TNUoS Dead Zone" mechanism cited in the submissions. Band thresholds and rates are read directly from
NESO's own published tariff tables (`scripts/Public_2026-27_TNUoS_Tariff_Report_Tables_V1.xlsx`, sheet
"TB"), not estimated. `build_charts.py` produces the two figures in `figures/`.

**UK Power Networks utilisation analysis** (`analyze_ukpn.py`, `analyze_ukpn_trend.py`,
`analyze_ukpn_bimodality.py`)
Analyses UK Power Networks' own published "Data Centre Demand Profiles" open dataset (96 sites,
half-hourly readings, Jan 2023–May 2026) for actual utilisation against secured/contracted grid capacity,
how the site population has changed over time, and whether the site-level utilisation distribution shows
signs of two hidden subpopulations rather than one blended one (see "AI compute vs cloud compute" below).
The scripts' outputs are the CSV files and chart below.

**Derived outputs** (included so results can be inspected without re-running anything):
`ukpn_site_summary.csv`, `ukpn_monthly_by_voltage.csv`, `ukpn_active_sites_by_month.csv`,
`ukpn_new_entrant_ramp.csv`, `ukpn_site_span.csv`, `ukpn_utilisation_chart.png`,
`ukpn_bimodality_check.png`.

**Third-party open data included for convenience**: `ukpn-data-centres-by-local-authority.csv` — UK Power
Networks' own "Data Centres by Local Authority" open dataset (operational/pipeline capacity by local
authority), reproduced here only because it's small; it is UKPN's data, not the author's.

## Data dictionary

All utilisation figures below are `hh_utilisation_ratio` as published in UKPN's own raw dataset (half-hourly
draw as a proportion of secured/contracted capacity) — not a ratio computed here against a separate capacity
figure. Each file is small enough to open directly in Excel.

**`ukpn_site_summary.csv`** — one row per site, aggregated across the full dataset period (Jan 2023–May 2026):
- `anonymised_data_centre_name` — UKPN's own anonymised site identifier
- `voltage` — connection tier: Extra-High Voltage Import / High Voltage Import / Low Voltage Import
- `dc_type` — Enterprise / Co-located, as classified by UKPN
- `mean_util` — mean of `hh_utilisation_ratio` across all half-hourly readings for that site
- `median_util` — median of the same
- `p95_util` — 95th percentile (a peak proxy less sensitive to a single outlier reading than `max_util`)
- `max_util` — the single highest half-hourly reading over the whole period
- `n_readings` — count of half-hourly readings used

**`ukpn_monthly_by_voltage.csv`** — one row per calendar month:
- `month` — YYYY-MM
- `Extra-High Voltage Import` / `High Voltage Import` / `Low Voltage Import` — mean `hh_utilisation_ratio`
  across all readings that month for sites in that tier

**`ukpn_active_sites_by_month.csv`** — one row per calendar month:
- `month` — YYYY-MM
- `active_site_count` — number of distinct sites reporting at least one reading that month

**`ukpn_new_entrant_ramp.csv`** — one row per month-since-connection, for sites whose first reporting month is
more than 3 months after the dataset's own start (i.e. genuine new entrants, not sites already present when
the dataset begins — 3 sites qualify; treat this file as indicative only given that sample size):
- `site_month_idx` — months since the site's first appearance (0 = first month observed)
- `mean` / `median` — `hh_utilisation_ratio` across all qualifying sites' readings in that relative month
- `count` — number of half-hourly readings behind that row (months with ≤500 readings are already excluded)

**`ukpn_site_span.csv`** — one row per site:
- `anonymised_data_centre_name`, `voltage` — as above
- `first_month` / `last_month` — first and last calendar month the site appears in the dataset

**`ukpn_utilisation_chart.png`** — rendered chart, not tabular; no dictionary entry needed.

**`ukpn-data-centres-by-local-authority.csv`** — UKPN's own published columns, reproduced verbatim:
`Local Authority District Name`, `County and Unitary Authority Name`, `Operational Data Centre Capacity (MVA)`,
`Pipeline Data Centre Capacity (MVA)`.

## AI compute vs cloud compute: an open question

This dataset's only site classification fields are voltage tier (Extra-High/High/Low Voltage Import) and
connection type (Enterprise/Co-located). There is no field distinguishing general-purpose "cloud compute"
data centres from AI-compute facilities, and that distinction matters: the two are likely to have very
different grid demand profiles (steady baseload vs. bursty, rapidly scaling draw), and the headline
utilisation figures elsewhere in this README are an average across whatever mix of the two actually exists
in the underlying 96 sites.

`analyze_ukpn_bimodality.py` tests whether the site-level utilisation distribution shows signs of two
hidden subpopulations — i.e. whether it's genuinely bimodal — using Hartigan's dip test and Gaussian
mixture models. It isn't: the distribution is a single, strongly right-skewed shape (dip test p = 0.58
for mean utilisation, p = 0.70 for median; skewness ≈ 2.0–2.3), and even a forced two-way split doesn't
line up with either voltage tier or connection type (`ukpn_bimodality_check.png`; full output in the
script itself). In short, this dataset as published cannot resolve the AI-vs-cloud-compute question in
either direction — it can rule out a clean two-population split, but it can't tell us what's actually
driving the shape it does show.

The same pass surfaced a separate, genuine data-quality finding worth flagging on its own: six sites show
a maximum half-hourly reading above 100% of secured capacity, and one (Data Centre #67, High Voltage
Import, Co-located) averages 124.7% utilisation across all 58,222 readings in its full three-year window —
either a real, sustained capacity exceedance or a stale/incorrect secured-capacity figure on UKPN's side.

A linked flag for on-site generation (G99) applications is one possible future proxy for AI-specific
builds, since a number of them pair their grid demand connection with on-site backup generation (gas
turbines, fuel cells) to get around connection-queue delays — but it isn't in the current dataset, and
whether UKPN could even supply it without breaching the same confidentiality constraint that already
blocks connection-date disclosure is an open question.

## Submissions

`submissions/` holds the actual documents this analysis fed into:

- `ofgem-curate-response-submitted.docx` — the Ofgem Curate consultation response as sent (2 September
  2026). The respondent-details telephone number has been redacted; name and email are left as submitted.
- `neso-letter.md` — follow-up letter to NESO's Future Energy Scenarios team on two findings outside
  Ofgem's remit (demand-forecast growth assumptions, cooling/climate uncertainty).
- `ai-energy-council-letter.md` — follow-up letter to the AI Energy Council secretariat on the same
  cross-regulatory coordination gap. Both letters are reproduced as drafted, with the sign-off left as
  "[Your Name]" rather than the author's personal signature as actually sent.
- `appg-data-centres-submission.docx` — written evidence to the House of Commons Data Centres APPG's
  inaugural inquiry, as sent (15 September 2026), with acknowledged receipt.

## Articles

`articles/` holds standalone written pieces that don't map to a specific submission question but draw on
the same evidence-first approach:

- `sealed-loops-dont-make-water-disappear.md` — on AI data centre water use: why a sealed chip-level
  cooling loop doesn't settle a site's water footprint, the WUE gap between dry and evaporative rejection,
  and the UK drought/water-stress context data centres are being sited into. Every figure is sourced with a
  full citation list.

## What's not here

The raw UK Power Networks "Data Centre Demand Profiles" dataset itself (~600MB, ~5.4 million rows) is not
included — it's too large for a normal git repository and this repo makes no claim over UKPN's own data.
To reproduce `analyze_ukpn.py` / `analyze_ukpn_trend.py` from scratch, download that dataset from UK Power
Networks' open data portal and place it at the repo root as `ukpn-data-centre-demand-profiles.csv`; the
scripts expect it there. The derived CSVs above are that pipeline's already-computed output, so you don't
need the raw file just to see the results.

A few code comments reference "evidence_map.md" — an extensive private verification log kept alongside
this project (every figure cross-checked against a primary source before use). It isn't included here; the
comments are left in as a provenance trail for the author's own records, not as a dependency — nothing in
this repo needs that file to run.

## Licence

Code (the `.py` and `.js` files, where present) is released under the MIT licence — see `LICENSE`.

The derived data files and chart — `ukpn_site_summary.csv`, `ukpn_monthly_by_voltage.csv`,
`ukpn_active_sites_by_month.csv`, `ukpn_new_entrant_ramp.csv`, `ukpn_site_span.csv` and
`ukpn_utilisation_chart.png` — are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
You're free to use, share and adapt them, including commercially, provided you credit the source, e.g.
"Andy Moran / Heaviside Analytics, analysis of UK Power Networks' Data Centre Demand Profiles open dataset."

Written material (this README) retains no separate licence claim from the author. Third-party data files
(`ukpn-data-centres-by-local-authority.csv`, the NESO tariff tables) remain those organisations' own
published data, under their own terms.
