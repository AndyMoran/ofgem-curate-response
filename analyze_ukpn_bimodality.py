"""
Checks whether the site-level utilisation distribution in UK Power Networks'
"Data Centre Demand Profiles" dataset is genuinely bimodal — i.e. whether it
splits into two hidden subpopulations (for example, steady cloud/enterprise
load vs. AI compute demand) rather than being a single blended shape.

Method: Hartigan's dip test (formal test of the null hypothesis that a
distribution is unimodal), Gaussian Mixture Models with BIC-based model
selection (1 vs 2 vs 3 components), skewness, and a cross-tab of any forced
2-cluster split against the only site attributes UKPN publishes (voltage
tier, dc_type). See README.md, "AI compute vs cloud compute" section, for
the result and what it does and doesn't show.

Requires: ukpn_site_summary.csv (produced by analyze_ukpn.py) and the raw
dataset is NOT needed — this operates on the already-aggregated per-site
summary.
"""

import os
import numpy as np
import pandas as pd
from scipy.stats import skew, gaussian_kde
from sklearn.mixture import GaussianMixture
from diptest import diptest
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.chdir(os.path.dirname(os.path.abspath(__file__)))

site = pd.read_csv("ukpn_site_summary.csv")
print("n sites:", len(site))

results = {}

for col in ["mean_util", "median_util"]:
    x = site[col].dropna().values
    print(f"\n=== {col} (n={len(x)}) ===")

    dip, pval = diptest(x)
    print(f"Hartigan dip statistic: {dip:.4f}, p-value: {pval:.4f}")
    print("  (p > 0.05: cannot reject unimodality; low p would support bimodality)")

    sk = skew(x)
    print(f"Skewness: {sk:.4f}")

    bics = {}
    for k in (1, 2, 3):
        gmm = GaussianMixture(n_components=k, random_state=0, n_init=5)
        gmm.fit(x.reshape(-1, 1))
        bics[k] = gmm.bic(x.reshape(-1, 1))
    best_k = min(bics, key=bics.get)
    print("BIC by number of components:", {k: round(v, 1) for k, v in bics.items()})
    print("BIC-preferred number of components:", best_k)

    gmm2 = GaussianMixture(n_components=2, random_state=0, n_init=5).fit(x.reshape(-1, 1))
    order = np.argsort(gmm2.means_.ravel())
    for i in order:
        w = gmm2.weights_[i]
        print(f"  component: mean={gmm2.means_[i][0]:.3f}, "
              f"std={np.sqrt(gmm2.covariances_[i][0][0]):.3f}, "
              f"weight={w:.2f} (~{round(w*len(x))} sites)")

    results[col] = {"dip": dip, "pval": pval, "skew": sk, "bics": bics}

# Forced 2-cluster split on mean_util, cross-tabbed against the only site
# attributes UKPN actually publishes.
x = site["mean_util"].dropna().values
gmm2 = GaussianMixture(n_components=2, random_state=0, n_init=5).fit(x.reshape(-1, 1))
labels = gmm2.predict(x.reshape(-1, 1))
site = site.loc[site["mean_util"].notna()].copy()
site["cluster"] = labels
lo, hi = sorted(range(2), key=lambda i: gmm2.means_[i][0])
site["cluster_label"] = site["cluster"].map({lo: "low-util", hi: "high-util"})

print("\n=== Forced 2-cluster split vs. voltage tier ===")
print(pd.crosstab(site["cluster_label"], site["voltage"]))
print("\n=== Forced 2-cluster split vs. dc_type ===")
print(pd.crosstab(site["cluster_label"], site["dc_type"]))
print("\nCluster means:")
print(site.groupby("cluster_label")["mean_util"].agg(["mean", "count"]))

# Data-quality flag, surfaced by this same pass: sites reading above 100%
# utilisation, which souldn't be possible against a correctly recorded
# secured-capacity figure.
over = site[site["max_util"] > 1.0]
print(f"\n=== Sites with max_util > 100% (n={len(over)}) ===")
print(over[["anonymised_data_centre_name", "voltage", "dc_type", "mean_util", "max_util"]]
      .to_string(index=False))

# Chart: histogram + KDE + the 1- and 2-component GMM fits, for mean_util.
x = site["mean_util"].values
xs = np.linspace(0, x.max() * 1.05, 500)
kde = gaussian_kde(x)

gmm1 = GaussianMixture(n_components=1, random_state=0).fit(x.reshape(-1, 1))

fig, ax = plt.subplots(figsize=(9, 5.5))
ax.hist(x, bins=24, density=True, alpha=0.35, color="#4C72B0", label="observed sites")
ax.plot(xs, kde(xs), color="#222222", lw=2, label="KDE (actual shape)")

from scipy.stats import norm
m1, s1 = gmm1.means_[0][0], np.sqrt(gmm1.covariances_[0][0][0])
ax.plot(xs, norm.pdf(xs, m1, s1), color="#55A868", lw=1.5, ls="--", label="1-component fit")

dens2 = np.zeros_like(xs)
for i in range(2):
    m, s, w = gmm2.means_[i][0], np.sqrt(gmm2.covariances_[i][0][0]), gmm2.weights_[i]
    dens2 += w * norm.pdf(xs, m, s)
ax.plot(xs, dens2, color="#C44E52", lw=1.5, ls="--", label="2-component fit")

ax.set_xlabel("Site mean utilisation (hh_utilisation_ratio)")
ax.set_ylabel("Density")
ax.set_title("Is site-level utilisation bimodal? (96 sites)")
ax.legend()
fig.tight_layout()
fig.savefig("ukpn_bimodality_check.png", dpi=150)
print("\nSaved chart: ukpn_bimodality_check.png")
