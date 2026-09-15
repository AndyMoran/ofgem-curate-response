"""
tnuos_full_bands.py

Extends Stage 6's tnuos_central_belt.py (HV bands only) with the full LV/HV/EHV
band set, sourced directly from NESO's own published Table TB — the exact
spreadsheet ("Public 2026-27 TNUoS Tariff Report Tables_V1.xlsx", sheet "TB")
Andy supplied on 13 Aug 2026 after the download-via-agent route was blocked by
the sandbox's network allowlist. Every threshold and rate below is read
straight from that sheet, not estimated or reconstructed from secondary
sources (two earlier web-search attempts at these thresholds returned mutually
inconsistent numbers and were explicitly discarded rather than used).

Purpose: answer the specific open question raised in the evidence map --
does a real 40MW+ site (DataVita DV1, the site already used for the fee-
proportionality check) face the same TNUoS band-step "Dead Zone" that Stage
6 found for the 5MW inference site? tnuos_central_belt.py's assign_band()
can't answer this: it only defines HV1-4, with HV4's upper bound coded as
infinite, so it would silently misfile a 40MW+ site into HV4. This module
fixes that.

T-Demand bands, note: NESO's Table TB bands T-Demand1-4 by ANNUAL
CONSUMPTION (MWh/year), not capacity (kVA) -- a completely different metric
from LV/HV/EHV. This explains the "counterintuitive" cost jump the 13 Aug
feedback flagged between EHV4 (capacity-banded, £5,698/day) and T-Demand1
(consumption-banded, £1,402/day): they were never on the same axis. Site
counts in Table TB (30/21/16/5 for T-Demand1-4, vs thousands for EHV) confirm
these are a small population of directly transmission-connected sites
billed on volume, not the same population a capacity-connected data centre
sits in. A capacity-connected data centre in the tens-of-MW range belongs in
the EHV bands, not T-Demand -- confirmed by where DV1 actually lands below.
"""

from dataclasses import dataclass

# ─────────────────────────────────────────────────────────────────────────
# Source: NESO "Public 2026-27 TNUoS Tariff Report Tables_V1.xlsx", sheet
# "TB" ("Table B - Non-locational banded charges"), supplied by Andy 13 Aug
# 2026. Thresholds and 26/27 Final TDR Charge (£/site/day) read directly
# from the sheet, not re-derived.
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class Band:
    tier: str
    band_name: str
    lower_threshold: float  # kVA for LV/HV/EHV; MWh/yr for T-Demand
    upper_threshold: float
    gbp_per_site_per_day: float
    unit: str = "kVA"
    source: str = "NESO Table TB, sheet TB, Public 2026-27 TNUoS Tariff Report Tables_V1.xlsx"
    evidence_status: str = "GROUNDED"


HV_BANDS = [
    Band("HV", "HV1", 0, 500, 31.839048),
    Band("HV", "HV2", 500, 1_100, 117.152788),
    Band("HV", "HV3", 1_100, 2_000, 185.418505),
    Band("HV", "HV4", 2_000, float("inf"), 528.912335),
]

EHV_BANDS = [
    Band("EHV", "EHV1", 0, 3_500, 325.476550),
    Band("EHV", "EHV2", 3_500, 11_000, 1_159.381475),
    Band("EHV", "EHV3", 11_000, 20_000, 2_512.930533),
    Band("EHV", "EHV4", 20_000, float("inf"), 5_698.386405),
]

T_DEMAND_BANDS = [
    Band("T-Demand", "T-Demand1", 0, 25_131, 1_401.949529, unit="MWh/yr"),
    Band("T-Demand", "T-Demand2", 25_131, 64_451, 2_931.228837, unit="MWh/yr"),
    Band("T-Demand", "T-Demand3", 64_451, 163_880, 7_586.413858, unit="MWh/yr"),
    Band("T-Demand", "T-Demand4", 163_880, float("inf"), 20_829.236682, unit="MWh/yr"),
]

ALL_CAPACITY_BANDS = HV_BANDS + EHV_BANDS  # kept for iteration/printing only -- NOT for band lookup, see below

# BUG FOUND AND FIXED DURING TESTING (worth stating plainly, same discipline as
# the rest of this project): a first version of assign_band() searched
# HV_BANDS + EHV_BANDS as one merged, kVA-ordered list. Because HV4's upper
# threshold is coded as infinite (correctly, per Table TB -- HV4 really has no
# capacity ceiling *within the HV tier*), a 40MW/42,105kVA site matched HV4
# and returned before EHV bands were ever checked. That's wrong: HV and EHV
# are different VOLTAGE connection tiers, not a single continuous kVA ladder.
# A site's tier is set by which voltage it actually connects at; the kVA bands
# only sub-divide *within* that tier. Table TB itself lists them as separate
# sections for exactly this reason. Fixed below by requiring the voltage tier
# as an explicit input rather than inferring it from kVA alone.

TIER_BANDS = {"HV": HV_BANDS, "EHV": EHV_BANDS}


def annual_cost_gbp(band: Band) -> float:
    return band.gbp_per_site_per_day * 365


def assign_band(capacity_mw: float, voltage_tier: str, power_factor: float = 0.95) -> Band:
    """
    Assigns a site to its real TNUoS band WITHIN a given voltage tier ("HV"
    or "EHV"), using NESO's actual Table TB thresholds. voltage_tier must be
    supplied -- it is not something kVA alone can determine (see note above).
    """
    if voltage_tier not in TIER_BANDS:
        raise ValueError(f"voltage_tier must be one of {list(TIER_BANDS)}, got {voltage_tier!r}")
    capacity_kva = capacity_mw * 1000 / power_factor
    for band in TIER_BANDS[voltage_tier]:
        if band.lower_threshold < capacity_kva <= band.upper_threshold:
            return band
    raise ValueError(f"{capacity_kva:.0f} kVA does not fall within any defined {voltage_tier} band.")


def feasible_band_step(current_band: Band, site_min_load_mw: float, power_factor: float = 0.95) -> dict:
    """
    Same logic as Stage 6's tnuos_central_belt.feasible_band_step(), applied
    within current_band's own voltage tier only -- stepping down changes
    capacity band, not voltage connection, so cross-tier steps (EHV -> HV)
    aren't a real option and are excluded here.
    """
    same_tier_bands = TIER_BANDS[current_band.tier]
    lower_bands = [b for b in same_tier_bands if b.upper_threshold < current_band.upper_threshold]
    results = []
    for band in lower_bands:
        ceiling_mw = band.upper_threshold * power_factor / 1000 if band.upper_threshold != float("inf") else float("inf")
        reachable = site_min_load_mw <= ceiling_mw
        results.append({
            "band": band.band_name,
            "ceiling_mw": round(ceiling_mw, 2),
            "ceiling_kva": band.upper_threshold,
            "reachable": reachable,
            "shortfall_mw": round(site_min_load_mw - ceiling_mw, 2) if not reachable else 0.0,
            "annual_saving_if_reached_gbp": round(annual_cost_gbp(current_band) - annual_cost_gbp(band), 0),
        })
    any_reachable = any(r["reachable"] for r in results)
    return {
        "current_band": current_band.band_name,
        "current_band_annual_gbp": round(annual_cost_gbp(current_band), 0),
        "site_min_load_mw": site_min_load_mw,
        "band_checks": results,
        "any_band_step_feasible": any_reachable,
    }


if __name__ == "__main__":
    print("Real TNUoS capacity bands (HV + EHV), NESO Table TB")
    print("=" * 78)
    for band in ALL_CAPACITY_BANDS:
        upper = f"{band.upper_threshold:,.0f}" if band.upper_threshold != float("inf") else "no cap"
        print(f"  {band.band_name:6s}  {band.lower_threshold:>7,.0f} - {upper:>8s} kVA   "
              f"£{band.gbp_per_site_per_day:>10,.2f}/day  ->  £{annual_cost_gbp(band):>12,.0f}/yr")

    print("\n" + "=" * 78)
    print("DataVita DV1 -- band assignment and step-feasibility")
    print("=" * 78)
    print("\nVoltage-tier assumption (PROVISIONAL, not confirmed for DV1 specifically):")
    print("  Stage 5 established its 100MW site as a real 132kV/EHV connection. DV1's own")
    print("  connection voltage hasn't been confirmed from a primary source. Assumed EHV here")
    print("  because a 24-40MW capacity connection would ordinarily require an EHV connection")
    print("  in GB practice (HV distribution networks aren't typically sized for this), consistent")
    print("  with how this project already treats its other large site. Flagged, not asserted.")

    for label, mw in [
        ("40MW (fee-liable target/expansion capacity -- same figure used in capex_central_belt.py's "
         "proportionality check)", 40.0),
        ("24MW ('live'/currently-contracted capacity, per public reporting on DV1 -- NOT independently "
         "verified against a primary DV1 source, included as a lower-bound sensitivity only)", 24.0),
    ]:
        print(f"\n--- Scenario: {label} ---")
        kva = mw * 1000 / 0.95
        assigned = assign_band(mw, voltage_tier="EHV")
        print(f"  {mw}MW @ 0.95 PF = {kva:,.0f} kVA -> assigned band: {assigned.band_name} "
              f"(£{annual_cost_gbp(assigned):,.0f}/yr)")

        # No real DV1 load telemetry exists, so we don't invent a minimum-load
        # figure and pass it through as if grounded (unlike Stage 6, where the
        # 4.0MW figure at least traced to an already-sourced load profile).
        # feasible_band_step() needs a min-load to test reachability; instead,
        # binary-search the minimum load AT WHICH the nearest lower band would
        # just become reachable, and report that threshold plus the required
        # cut from current capacity -- both answerable from Table TB alone,
        # with no load-profile assumption needed.
        lower_bands_same_tier = [b for b in TIER_BANDS[assigned.tier] if b.upper_threshold < assigned.lower_threshold or
                                  b is not assigned and b.upper_threshold <= assigned.lower_threshold]
        lower_candidates = sorted(
            [b for b in TIER_BANDS[assigned.tier] if b.upper_threshold <= assigned.lower_threshold],
            key=lambda b: -b.upper_threshold,
        )
        if lower_candidates:
            step_to = lower_candidates[0]
            step_to_mw = step_to.upper_threshold * 0.95 / 1000
            required_cut_mw = mw - step_to_mw
            required_cut_pct = required_cut_mw / mw * 100
            saving = annual_cost_gbp(assigned) - annual_cost_gbp(step_to)
            print(f"  Nearest lower band: {step_to.band_name} (ceiling {step_to.upper_threshold:,.0f}kVA "
                  f"= {step_to_mw:.2f}MW @ 0.95 PF)")
            print(f"  Required contracted-capacity CUT to reach it: {required_cut_mw:.2f}MW "
                  f"({required_cut_pct:.1f}% of current capacity)")
            print(f"  Annual saving IF reached: £{saving:,.0f}/yr")
            print(f"  NOTE: whether this is operationally/commercially feasible is NOT determined here --")
            print(f"        no real DV1 load telemetry exists. What IS established without any load")
            print(f"        assumption: the scale of cut required ({required_cut_pct:.1f}%) is far larger")
            print(f"        than a battery-enabled peak-shaving adjustment -- it is a capacity SURRENDER,")
            print(f"        not an operational dispatch decision.")
        else:
            print("  No lower band exists within this tier to step to.")

    print("\n" + "=" * 78)
    print("HV/EHV tier-uncertainty check: does the finding survive if DV1 is HV, not EHV?")
    print("=" * 78)
    print("DV1's real connection voltage at 40MW is not confirmed from a primary source (see")
    print("submission caveat). Rather than assert the finding is 'robust either way', check it:")
    for tier in ("EHV", "HV"):
        assigned = assign_band(40.0, voltage_tier=tier)
        lower_candidates = sorted(
            [b for b in TIER_BANDS[assigned.tier] if b.upper_threshold <= assigned.lower_threshold],
            key=lambda b: -b.upper_threshold,
        )
        step_to = lower_candidates[0]
        step_to_mw = step_to.upper_threshold * 0.95 / 1000
        required_cut_mw = 40.0 - step_to_mw
        required_cut_pct = required_cut_mw / 40.0 * 100
        print(f"  40MW assumed {tier:4s}: band {assigned.band_name}, £{annual_cost_gbp(assigned):,.0f}/yr, "
              f"cut to {step_to.band_name} = {required_cut_mw:.1f}MW ({required_cut_pct:.1f}%)")
    print("  Result: HV4 requires a LARGER cut (~95%) than EHV4 (52.5%), because HV4's own ceiling")
    print("  within the HV tier sits far below 40MW. The qualitative Dead Zone finding holds either")
    print("  way; only the specific reported percentage (52.5%) is EHV-specific and unconfirmed.")
