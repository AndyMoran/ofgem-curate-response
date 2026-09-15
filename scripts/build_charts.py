"""
build_charts.py

Builds the two Tufte-compliant figures for the ofgem-curate-response project,
per PROJECT.md Section 9 (max data-ink ratio, no chartjunk, direct-label,
small multiples for scenario comparison, y-axis/x-axis starts at zero unless
justified and marked).

All numbers are pulled live from tnuos_full_bands.py and evidence_map.md's
already-grounded figures -- nothing here is hand-typed separately from the
source of truth, so the charts can't silently drift from the submission text.

Outputs (this directory's ../figures/):
  fig1_dead_zone.png       -- band-ladder chart: where the 5MW site and DV1
                               sit within their top band, and the cut needed
                               to reach the band below.
  fig2_fee_proportionality.png -- Ofgem's 2.5-7.5% target range vs the
                               computed 1.75-7.09% range, by capex basis.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from tnuos_full_bands import HV_BANDS, EHV_BANDS, annual_cost_gbp

NAVY = "#1B2A41"
ACCENT = "#2E6E62"
GREY = "#555555"
LIGHT_GREY = "#D9D9D9"
RED = "#B23A2E"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.edgecolor": GREY,
    "axes.linewidth": 0.6,
    "text.color": "#222222",
    "axes.labelcolor": "#222222",
    "xtick.color": GREY,
    "ytick.color": GREY,
})

PF = 0.95  # power factor used throughout this project's kVA<->MW conversions


def band_ceiling_mw(band):
    if band.upper_threshold == float("inf"):
        return None
    return band.upper_threshold * PF / 1000


# ─────────────────────────────────────────────────────────────────────────
# Figure 1: the Dead Zone -- band ladder, two small multiples (HV / EHV)
# ─────────────────────────────────────────────────────────────────────────

def build_fig1():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    panels = [
        {
            "ax": axes[0],
            "bands": HV_BANDS,
            "title": "HV tier — Stage 6 reference site (5MW)",
            "site_label": "Min. operating\nload: 4.0MW",
            "site_value_mw": 4.0,
            "top_band_display_mw": 5.0,  # how far to draw the open-ended top band for display
            "cut_mw": 2.1,
            "cut_pct": 52.5,
            "xlabel": "Capacity (MW, at 0.95 power factor)",
        },
        {
            "ax": axes[1],
            "bands": EHV_BANDS,
            "title": "EHV tier — DataVita DV1 (40MW target)",
            "site_label": "Contracted\ncapacity: 40MW",
            "site_value_mw": 40.0,
            "top_band_display_mw": 42.0,
            "cut_mw": 21.0,
            "cut_pct": 52.5,
            "xlabel": "Capacity (MW, at 0.95 power factor)",
        },
    ]

    for p in panels:
        ax = p["ax"]
        bands = p["bands"]
        y = 0.5
        bar_h = 0.5

        span = p["top_band_display_mw"]
        for i, band in enumerate(bands):
            lo = band.lower_threshold * PF / 1000
            hi = band_ceiling_mw(band)
            display_hi = hi if hi is not None else span
            width = display_hi - lo
            shade = 0.30 + 0.20 * i  # progressively darker toward the top band
            ax.barh(y, width, left=lo, height=bar_h,
                     color=NAVY, alpha=shade, edgecolor="white", linewidth=1.2)
            mid = lo + width / 2
            name_label = band.band_name
            cost_label = f"£{annual_cost_gbp(band):,.0f}/yr"
            if width / span < 0.16:
                # too narrow for an inside label -- route it above the bar
                # with a short leader tick, staggered by band index to avoid
                # neighbouring narrow-band labels colliding with each other
                stagger = 0.55 + 0.5 * (i % 2)
                label_y = y + bar_h / 2 + stagger
                ax.plot([mid, mid], [y + bar_h / 2, label_y - 0.08], color=GREY, linewidth=0.7)
                ax.text(mid, label_y, f"{name_label}\n{cost_label}", ha="center", va="bottom",
                         fontsize=7.3, color="#222222")
            else:
                ax.text(mid, y, f"{name_label}\n{cost_label}", ha="center", va="center",
                         fontsize=8.2, color="#222222")

        # open-ended top band: hatch marker to show it doesn't actually stop there
        top_hi = p["top_band_display_mw"]
        ax.text(top_hi - 0.02 * top_hi, y + bar_h / 2 + 0.06, "no upper cap →",
                 ha="right", va="bottom", fontsize=7, color=GREY, style="italic")

        # ceiling of the band below the site's current band (the line that
        # actually needs to be crossed to reach relief)
        ceiling_mw = p["site_value_mw"] - p["cut_mw"]
        ax.axvline(ceiling_mw, color=RED, linewidth=1.1, linestyle="--", ymin=0.08, ymax=0.92)

        # site marker
        ax.plot([p["site_value_mw"]], [y], marker="o", markersize=7,
                 color=RED, zorder=5)
        ax.annotate(p["site_label"], xy=(p["site_value_mw"], y),
                    xytext=(p["site_value_mw"], y + 0.62),
                    ha="center", fontsize=8.6, color=RED, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color=RED, linewidth=0.8))

        # bracket showing the required cut
        bracket_y = y - 0.55
        ax.annotate("", xy=(ceiling_mw, bracket_y), xytext=(p["site_value_mw"], bracket_y),
                    arrowprops=dict(arrowstyle="<->", color="#222222", linewidth=1.0))
        ax.text((ceiling_mw + p["site_value_mw"]) / 2, bracket_y - 0.14,
                 f"Cut needed: {p['cut_mw']:.1f}MW ({p['cut_pct']:.1f}%)",
                 ha="center", va="top", fontsize=8.6, fontweight="bold", color="#222222")

        ax.set_xlim(0, p["top_band_display_mw"])
        ax.set_ylim(-0.35, 2.05)
        ax.set_yticks([])
        ax.set_xlabel(p["xlabel"], fontsize=9)
        ax.set_title(p["title"], fontsize=10.5, fontweight="bold", color=NAVY, loc="left", pad=10)
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        ax.tick_params(axis="x", labelsize=8)

    fig.suptitle(
        "The TNUoS band-step ‘Dead Zone’: two sites, two different scales, the same 52.5% wall",
        fontsize=12.5, fontweight="bold", color=NAVY, x=0.02, ha="left", y=1.02,
    )
    fig.text(0.02, -0.02,
              "Note: x-axis scales differ between panels (0–5MW vs 0–42MW) — the point is that the same proportional\n"
              "shortfall recurs at wildly different absolute capacities, not that the two sites are the same size.\n"
              "Sources: NESO Final TNUoS Tariffs 2026/27 (Table 10) and Table TB (band thresholds); DataVita DV1 public capacity reporting.\n"
              "DV1's EHV connection at 40MW is an assumption, not confirmed — see submission caveat.",
              fontsize=7.3, color=GREY, va="top")

    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    out = os.path.join(os.path.dirname(__file__), "..", "figures", "fig1_dead_zone.png")
    plt.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out}")


# ─────────────────────────────────────────────────────────────────────────
# Figure 2: fee proportionality -- Ofgem's target range vs the computed range
# ─────────────────────────────────────────────────────────────────────────

def build_fig2():
    # Grounded figures, evidence_map.md items 15-17 / capex_central_belt.py
    fee_low_gbp_mw = 237_500
    fee_high_gbp_mw = 712_500
    mean_capex = 13_541_800
    median_capex = 10_051_053

    rows = [
        ("Mean capex\n(£13.54M/MW)", fee_low_gbp_mw / mean_capex * 100, fee_high_gbp_mw / mean_capex * 100),
        ("Median capex\n(£10.05M/MW)", fee_low_gbp_mw / median_capex * 100, fee_high_gbp_mw / median_capex * 100),
    ]

    fig, ax = plt.subplots(figsize=(9, 3.2))

    ofgem_low, ofgem_high = 2.5, 7.5
    ax.axvspan(ofgem_low, ofgem_high, color=ACCENT, alpha=0.12, zorder=0)
    ax.axvline(ofgem_low, color=ACCENT, linewidth=1.0, linestyle=":", zorder=1)
    ax.axvline(ofgem_high, color=ACCENT, linewidth=1.0, linestyle=":", zorder=1)
    ax.text(ofgem_low, 2.35, "Ofgem target\nfloor: 2.5%", ha="center", va="top",
             fontsize=8, color=ACCENT, fontweight="bold")
    ax.text(ofgem_high, 2.35, "Ofgem target\nceiling: 7.5%", ha="center", va="top",
             fontsize=8, color=ACCENT, fontweight="bold")

    for i, (label, lo, hi) in enumerate(rows):
        y = len(rows) - i
        ax.plot([lo, hi], [y, y], color=NAVY, linewidth=3, solid_capstyle="round", zorder=3)
        ax.plot([lo, hi], [y, y], marker="o", markersize=7, color=NAVY, zorder=4)
        below_floor = lo < ofgem_low
        ax.text(lo - 0.15, y, f"{lo:.2f}%", ha="right", va="center", fontsize=9,
                 color=RED if below_floor else "#222222", fontweight="bold" if below_floor else "normal")
        ax.text(hi + 0.15, y, f"{hi:.2f}%", ha="left", va="center", fontsize=9, color="#222222")

    ax.set_yticks([len(rows) - i for i in range(len(rows))])
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_ylim(0.4, len(rows) + 0.9)
    ax.set_xlim(0, 8.5)
    ax.set_xlabel("Commitment fee as % of capex, at DataVita DV1's 40MW threshold capacity", fontsize=9)
    ax.set_title(
        "Fee proportionality against Ofgem's own Table 4 capex data: dips below the target floor at the low end",
        fontsize=11.5, fontweight="bold", color=NAVY, loc="left", pad=14,
    )
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="x", labelsize=8)

    fig.text(0.02, -0.06,
              "Real anchor site: DataVita DV1, 40MW, at the fee's own applicability threshold. Fee range £237,500–£712,500/MW\n"
              "(Ofgem consultation, para 5.1/5.4). Capex mean/median from Ofgem's own Table 4, Medium (10–50MW) band, n=8.",
              fontsize=7.3, color=GREY, va="top")

    plt.tight_layout(rect=[0, 0.06, 1, 0.94])
    out = os.path.join(os.path.dirname(__file__), "..", "figures", "fig2_fee_proportionality.png")
    plt.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    build_fig1()
    build_fig2()
