# ofgem-curate-response — supporting analysis

Independent analysis behind several evidence-sourced claims in two public submissions on UK data-centre
grid connections: a response to Ofgem's "Curate — Demand Connections Reform" consultation (2026), and
written evidence to the House of Commons Data Centres APPG's inaugural inquiry. Both were submitted
independently, in a personal capacity, not on behalf of any developer, DNO, vendor, or other stakeholder.

This repository exists so specific figures in those submissions can be checked against the code and data
that produced them, rather than taken on trust.

## What's here

**TNUoS tariff-band modelling** (`scripts/tnuos_full_bands.py`, `scripts/build_charts.py`)
Models where a real 40MW+ site (DataVita's DV1 facility) and a smaller 5MW site sit within NESO's
published transmission-charging bands, and the capacity cut each would need to reach the band below —
the "TNUoS Dead Zone" mechanism cited in the submissions. Band thresholds and rates are read directly from
NESO's own published tariff tables (`scripts/Public_2026-27_TNUoS_Tariff_Report_Tables_V1.xlsx`, sheet
"TB"), not estimated. `build_charts.py` produces the two figures in `figures/`.

**UK Power Networks utilisation analysis** (`analyze_ukpn.py`, `analyze_ukpn_trend.py`)
Analyses UK Power Networks' own published "Data Centre Demand Profiles" open dataset (96 sites,
half-hourly readings, Jan 2023–May 2026) for actual utilisation against secured/contracted grid capacity,
and for how the site population has changed over time. The scripts' outputs are the CSV files below.

**Derived outputs** (included so results can be inspected without re-running anything):
`ukpn_site_summary.csv`, `ukpn_monthly_by_voltage.csv`, `ukpn_active_sites_by_month.csv`,
`ukpn_new_entrant_ramp.csv`, `ukpn_site_span.csv`, `ukpn_utilisation_chart.png`.

**Third-party open data included for convenience**: `ukpn-data-centres-by-local-authority.csv` — UK Power
Networks' own "Data Centres by Local Authority" open dataset (operational/pipeline capacity by local
authority), reproduced here only because it's small; it is UKPN's data, not the author's.

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

Code (the `.py` and `.js` files, where present) is released under the MIT licence — see `LICENSE`. Written
material (this README) and the third-party data files retain no separate licence claim from the author;
the NESO tariff tables and UK Power Networks open data remain those organisations' own published data.
