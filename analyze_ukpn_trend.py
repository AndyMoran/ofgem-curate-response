import pandas as pd
import numpy as np
import os
os.chdir(os.path.expanduser("~/mnt/ofgem-curate-response"))

path = "ukpn-data-centre-demand-profiles.csv"
usecols = ["cleansed_voltage_level","anonymised_data_centre_name","dc_type","utc_timestamp","hh_utilisation_ratio"]
dtypes = {"cleansed_voltage_level":"category","anonymised_data_centre_name":"category","dc_type":"category","hh_utilisation_ratio":"float32"}
df = pd.read_csv(path, usecols=usecols, dtype=dtypes, parse_dates=["utc_timestamp"])
df["month"] = df["utc_timestamp"].dt.to_period("M")

# 1) how many distinct sites are actively reporting each month (pipeline/population growth)
active_by_month = df.groupby("month", observed=True)["anonymised_data_centre_name"].nunique().rename("active_site_count")
active_by_month.to_csv("ukpn_active_sites_by_month.csv")
print("=== Active reporting sites by month (first/last 6) ===")
print(active_by_month.head(6))
print(active_by_month.tail(6))
print()

# 2) first and last month each site appears
site_span = df.groupby("anonymised_data_centre_name", observed=True)["month"].agg(["min","max"])
site_span.columns = ["first_month","last_month"]
site_span["voltage"] = df.groupby("anonymised_data_centre_name", observed=True)["cleansed_voltage_level"].first()
site_span.to_csv("ukpn_site_span.csv")

dataset_start = df["month"].min()
buffer_cutoff = dataset_start + 3  # 3 months buffer
new_entrants = site_span[site_span["first_month"] > buffer_cutoff]
print(f"dataset starts {dataset_start}; sites first appearing after {buffer_cutoff}: {len(new_entrants)} of {len(site_span)}")
print(new_entrants["voltage"].value_counts())
print()

# 3) for new entrant sites, build a relative-month utilisation curve (months since first appearance)
if len(new_entrants) > 0:
    sub = df[df["anonymised_data_centre_name"].isin(new_entrants.index)].copy()
    first_month_map = new_entrants["first_month"]
    sub["site_month_idx"] = sub.apply(lambda r: (r["month"] - first_month_map[r["anonymised_data_centre_name"]]).n, axis=1)
    monthly_util = sub.groupby("month", observed=True)["hh_utilisation_ratio"].mean()  # quick sanity, not used directly
    ramp = sub.groupby("site_month_idx")["hh_utilisation_ratio"].agg(["mean","median","count"])
    ramp = ramp[ramp["count"] > 500]  # drop thin tail months with too few readings
    ramp.to_csv("ukpn_new_entrant_ramp.csv")
    print("=== New-entrant utilisation by months since first appearance (head 12) ===")
    print(ramp.head(12))
    print("=== tail 6 ===")
    print(ramp.tail(6))

# 4) churn check: sites whose last month is well before dataset end
dataset_end = df["month"].max()
churn_cutoff = dataset_end - 3
churned = site_span[site_span["last_month"] < churn_cutoff]
print()
print(f"dataset ends {dataset_end}; sites with last reading before {churn_cutoff} (possible churn/gaps): {len(churned)} of {len(site_span)}")
