"""
Tests the "temporal volatility, not static population" hypothesis directly,
rather than assuming it: does any individual site show a large, step-like
change in utilisation over time (e.g. consistent with winning/losing a
compute tenant), even though analyze_ukpn_bimodality.py found no clean
two-population split when sites are averaged over their whole history?

This operates on the RAW half-hourly dataset (not ukpn_site_summary.csv,
which collapses each site to a single mean/median and so cannot show
within-site change over time by construction).

Method, per site:
  1. Resample half-hourly readings to a monthly mean utilisation series.
  2. Require a minimum number of months of data (else short/patchy sites
     produce meaningless "swings").
  3. Run PELT change-point detection (ruptures, RBF cost) on the monthly
     series to find the single best split point.
  4. Compute the before/after mean utilisation at that split, and the size
     of the jump.
  5. Flag sites with (a) a detected change point and (b) a jump large
     enough to plausibly represent a real regime change (threshold: >=0.15
     absolute utilisation-ratio shift, i.e. >=15 percentage points) rather
     than gradual drift or noise.
  6. Exclude sites already flagged by analyze_ukpn_bimodality.py as having
     max_util > 100% of secured capacity (ukpn_site_summary.csv) — an
     apparent data-quality problem (stale/incorrect secured-capacity
     figure), not a real workload change. Two of these (Data Centre #67,
     #37) were the two largest "jumps" in an earlier unfiltered pass, and
     including them would misattribute a data artefact as evidence of a
     tenant/workload swing.
  7. Classify each large jump as "went_dark" (drops to near-zero and stays
     there), "appeared" (rises from near-zero), or "active_shift" (moves
     between two non-zero levels while remaining in service). Only the
     last of these is actually consistent with "the same site changed
     workload/tenant" — the first two look like a site leaving or entering
     the dataset, not a regime change within one continuously-operating
     site. Collapsing all three into "a jump" overstates how much of this
     supports the tenant/workload-swap hypothesis specifically.

This is a descriptive/exploratory pass, not a confirmatory test — with 96
sites and no pre-registered threshold, some "detected" jumps will be
false positives. The output is a ranked list and a chart so the finding
can be inspected site-by-site, not a single summary statistic to quote
on its own.

Requires: ukpn-data-centre-demand-profiles.csv (UKPN's raw published
dataset, not derived) and ukpn_site_summary.csv (for the max_util data-
quality flag, produced by analyze_ukpn.py).
"""

import os
import numpy as np
import pandas as pd
import ruptures as rpt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.chdir(os.path.dirname(os.path.abspath(__file__)))

MIN_MONTHS = 12          # ignore sites with too little history to judge
JUMP_THRESHOLD = 0.15    # absolute utilisation-ratio shift to call "large"

site_summary = pd.read_csv("ukpn_site_summary.csv")
quality_flagged = set(
    site_summary.loc[site_summary["max_util"] > 1.0, "anonymised_data_centre_name"]
)
print(f"Excluding {len(quality_flagged)} data-quality-flagged sites (max_util > 100%): "
      f"{sorted(quality_flagged)}")

df = pd.read_csv("ukpn-data-centre-demand-profiles.csv")
df = df[~df["anonymised_data_centre_name"].isin(quality_flagged)]
df["local_timestamp"] = pd.to_datetime(df["local_timestamp"], utc=True)
df["month"] = df["local_timestamp"].dt.to_period("M")

meta = df.drop_duplicates("anonymised_data_centre_name").set_index("anonymised_data_centre_name")[
    ["cleansed_voltage_level", "dc_type"]
]

monthly = (
    df.groupby(["anonymised_data_centre_name", "month"])["hh_utilisation_ratio"]
    .mean()
    .reset_index()
)

records = []
series_store = {}

for site, g in monthly.groupby("anonymised_data_centre_name"):
    g = g.sort_values("month")
    y = g["hh_utilisation_ratio"].values
    if len(y) < MIN_MONTHS:
        continue

    series_store[site] = g.set_index("month")["hh_utilisation_ratio"]

    algo = rpt.Pelt(model="rbf").fit(y)
    try:
        bkps = algo.predict(pen=3)
    except Exception:
        bkps = [len(y)]
    bkps = [b for b in bkps if b < len(y)]  # drop trailing endpoint

    if not bkps:
        records.append({
            "site": site, "n_months": len(y), "changepoint_detected": False,
            "split_month_idx": None, "before_mean": np.nan, "after_mean": np.nan,
            "jump": 0.0,
        })
        continue

    # Use the split with the largest before/after mean difference if
    # PELT found more than one.
    best = max(bkps, key=lambda b: abs(y[:b].mean() - y[b:].mean()))
    before, after = y[:best].mean(), y[best:].mean()
    records.append({
        "site": site, "n_months": len(y), "changepoint_detected": True,
        "split_month_idx": best, "before_mean": before, "after_mean": after,
        "jump": after - before,
    })

res = pd.DataFrame(records).set_index("site").join(meta)
res["abs_jump"] = res["jump"].abs()

# A large |jump| conflates three different things, and only one of them is
# actually "a site changing regime while remaining in service": a site can
# also simply go dark (stop drawing power near-permanently) or appear from
# near-zero (a new tenant), and PELT's single-breakpoint model doesn't
# distinguish these from a genuine two-plateau shift. Classify explicitly
# rather than let "large jump" imply a workload swap by default.
NEAR_ZERO = 0.02
res["pattern"] = "small_or_no_change"
large_mask = res["abs_jump"] >= JUMP_THRESHOLD
res.loc[large_mask, "pattern"] = "active_shift"  # default for large jumps
res.loc[large_mask & (res["after_mean"] < NEAR_ZERO), "pattern"] = "went_dark"
res.loc[large_mask & (res["before_mean"] < NEAR_ZERO), "pattern"] = "appeared"

res = res.sort_values("abs_jump", ascending=False)
res.to_csv("ukpn_site_volatility_clean.csv")

print(f"Sites analysed (>= {MIN_MONTHS} months of data): {len(res)}")
print(f"Sites with a detected change point: {res['changepoint_detected'].sum()}")
large = res[res["abs_jump"] >= JUMP_THRESHOLD]
print(f"Sites with a jump >= {JUMP_THRESHOLD:.0%} utilisation-ratio: {len(large)}")
print()
print("=== Breakdown by pattern (large-jump sites only) ===")
print(large["pattern"].value_counts())
print("  went_dark: drops to near-zero and stays there (site exit, not a workload swap)")
print("  appeared: rises from near-zero (new tenant, not a workload swap)")
print("  active_shift: shifts between two non-zero levels while staying in service")
print("                (the only pattern actually consistent with a same-site tenant/")
print("                 workload change) — inspect the chart before trusting even")
print("                 these: PELT fits a single step, so a smooth ramp can also")
print("                 get flagged here as if it were a step.")
print()
print("=== Top 15 largest detected jumps ===")
print(large.head(15)[["n_months", "split_month_idx", "before_mean", "after_mean", "jump",
                       "pattern", "cleansed_voltage_level", "dc_type"]].to_string())

print()
print("=== Distribution of |jump| across all analysed sites ===")
print(res["abs_jump"].describe())

# Cross-tab: does a large jump associate with voltage tier or dc_type?
print()
print("=== Large-jump sites vs dc_type ===")
print(pd.crosstab(res["abs_jump"] >= JUMP_THRESHOLD, res["dc_type"]))
print()
print("=== Large-jump sites vs voltage tier ===")
print(pd.crosstab(res["abs_jump"] >= JUMP_THRESHOLD, res["cleansed_voltage_level"]))

# Chart: the 6 largest-jump sites' monthly utilisation series, with the
# detected split marked, so the "step change" claim can be eyeballed
# directly rather than taken on the summary stat alone.
top6 = large.head(6).index.tolist()
fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=False)
for ax, site in zip(axes.ravel(), top6):
    s = series_store[site]
    ax.plot(range(len(s)), s.values, marker="o", ms=3, lw=1, color="#4C72B0")
    split = res.loc[site, "split_month_idx"]
    if pd.notna(split):
        ax.axvline(int(split), color="#C44E52", ls="--", lw=1.5)
    ax.set_title(f"{site}  (jump={res.loc[site, 'jump']:.2f})", fontsize=9)
    ax.set_ylim(0, max(1.0, s.max() * 1.1))
for ax in axes.ravel()[len(top6):]:
    ax.axis("off")
fig.suptitle("Largest detected utilisation step-changes (monthly mean, raw half-hourly data)")
fig.tight_layout()
fig.savefig("ukpn_site_volatility_top_jumps_clean.png", dpi=150)
print("\nSaved: ukpn_site_volatility_clean.csv, ukpn_site_volatility_top_jumps_clean.png")
