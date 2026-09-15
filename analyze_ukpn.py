import pandas as pd
import numpy as np

path = r"ukpn-data-centre-demand-profiles.csv"
import os
os.chdir(os.path.expanduser("~/mnt/ofgem-curate-response"))

usecols = ["cleansed_voltage_level","anonymised_data_centre_name","dc_type","utc_timestamp","hh_utilisation_ratio"]
dtypes = {"cleansed_voltage_level":"category","anonymised_data_centre_name":"category","dc_type":"category","hh_utilisation_ratio":"float32"}

df = pd.read_csv(path, usecols=usecols, dtype=dtypes, parse_dates=["utc_timestamp"])
print("rows:", len(df))
print("unique sites:", df["anonymised_data_centre_name"].nunique())
print("date range:", df["utc_timestamp"].min(), "to", df["utc_timestamp"].max())
print()
print("=== sites per voltage tier / dc_type ===")
print(df.drop_duplicates("anonymised_data_centre_name").groupby(["cleansed_voltage_level","dc_type"]).size())
print()

# per-site summary
site_summary = df.groupby("anonymised_data_centre_name", observed=True).agg(
    voltage=("cleansed_voltage_level","first"),
    dc_type=("dc_type","first"),
    mean_util=("hh_utilisation_ratio","mean"),
    median_util=("hh_utilisation_ratio","median"),
    p95_util=("hh_utilisation_ratio", lambda x: np.percentile(x,95)),
    max_util=("hh_utilisation_ratio","max"),
    n_readings=("hh_utilisation_ratio","count"),
).reset_index()
site_summary.to_csv("ukpn_site_summary.csv", index=False)

print("=== HEADLINE (all sites) ===")
print("median of site mean_util:", site_summary["mean_util"].median())
print("median of site p95_util (proxy for 'peak'):", site_summary["p95_util"].median())
print("median of site max_util:", site_summary["max_util"].median())
pct_never_above_40pct = (site_summary["max_util"] < 0.40).mean()*100
print("% of sites whose max never exceeded 40%:", pct_never_above_40pct)
print()

print("=== By voltage tier (median of per-site mean utilisation) ===")
print(site_summary.groupby("voltage")["mean_util"].median())
print()
print("=== By voltage tier (median of per-site P95 utilisation, peak proxy) ===")
print(site_summary.groupby("voltage")["p95_util"].median())
print()
print("=== By voltage tier (median of per-site MAX utilisation) ===")
print(site_summary.groupby("voltage")["max_util"].median())
print()
print("=== By dc_type (median of per-site mean utilisation) ===")
print(site_summary.groupby("dc_type")["mean_util"].median())
print()

# EHV as proxy for "largest connections"
ehv = site_summary[site_summary["voltage"]=="Extra-High Voltage Import"]
print("=== EHV sites (n=%d) as proxy for largest connections ===" % len(ehv))
print("median mean_util:", ehv["mean_util"].median())
print("median p95_util:", ehv["p95_util"].median())
print(ehv[["anonymised_data_centre_name","dc_type","mean_util","p95_util","max_util"]].sort_values("mean_util"))
print()

# overstate ratio
overall_mean = site_summary["mean_util"].mean()
print("mean of site mean_util (avg draw):", overall_mean, " => contracted/actual ratio ~", 1/overall_mean)

# time trend: monthly mean utilisation overall and by voltage tier
df["month"] = df["utc_timestamp"].dt.to_period("M")
monthly = df.groupby(["month","cleansed_voltage_level"], observed=True)["hh_utilisation_ratio"].mean().unstack()
monthly.to_csv("ukpn_monthly_by_voltage.csv")
print("=== Monthly trend (head/tail) ===")
print(monthly.head(3))
print(monthly.tail(3))
