import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# Use absolute paths
BASE_DIR = r"c:\Users\hp\OneDrive\Desktop\IIT BHU\Epidemic_Spread_Prediction"
PROC_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
# Artifacts path for saving images
ARTIFACT_DIR = r"C:\Users\hp\.gemini\antigravity\brain\93562a5e-fca5-4115-a170-6e11108f668a"

df_jhu = pd.read_csv(os.path.join(PROC_DATA_DIR, "jhu_processed.csv"))
df_owid = pd.read_csv(os.path.join(RAW_DATA_DIR, "owid_covid_data.csv"))

# --- 1. Autocorrelation & Rolling Average Plot ---
plt.figure(figsize=(12, 6))
# Filter to a specific country with high cases for clear signal, e.g., US
df_us = df_jhu[df_jhu["Country/Region"] == "US"].copy()
df_us["Date"] = pd.to_datetime(df_us["Date"])
df_us = df_us.groupby("Date")[["New_Confirmed", "New_Confirmed_Roll7"]].sum()

# Autocorrelation using pandas
lags = range(1, 15)
corrs = [df_us["New_Confirmed"].corr(df_us["New_Confirmed"].shift(l)) for l in lags]

plt.subplot(1, 2, 1)
plt.bar(lags, corrs, color='skyblue', edgecolor='black')
plt.title("Autocorrelation of Daily New Cases (US)\nShows 7-day Seasonality")
plt.xlabel("Lag (Days)")
plt.ylabel("Pearson Correlation")
plt.xticks(lags)
plt.axhline(0, color='black', lw=1)
plt.grid(axis='y', alpha=0.3)

# Rolling Average vs Raw series
plt.subplot(1, 2, 2)
# zoom in on a specific period to see the weekend effect clearly
mask = (df_us.index > '2020-09-01') & (df_us.index < '2020-11-01')
plt.plot(df_us.index[mask], df_us.loc[mask, "New_Confirmed"], label="Raw New Cases", alpha=0.5, marker='o', markersize=4)
plt.plot(df_us.index[mask], df_us.loc[mask, "New_Confirmed_Roll7"], label="7-Day Rolling Avg", color='red', linewidth=3)
plt.title("Raw Daily Cases vs 7-Day Rolling Average\n(Smoothing out Weekend Drops)")
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(ARTIFACT_DIR, "signals_plot.png"), dpi=150)
plt.close()

# --- 2. FFill Stringency Plot ---
plt.figure(figsize=(8, 5))
df_owid_uk = df_owid[df_owid["iso_code"] == "GBR"].copy()
df_owid_uk["date"] = pd.to_datetime(df_owid_uk["date"])
df_owid_uk = df_owid_uk.sort_values("date")

# Create artificial missing data by dropping 80% to show what ffill does
np.random.seed(42)
df_owid_uk["stringency_with_nans"] = df_owid_uk["stringency_index"]
mask = np.random.rand(len(df_owid_uk)) > 0.2
df_owid_uk.loc[mask, "stringency_with_nans"] = np.nan

df_owid_uk["stringency_ffill"] = df_owid_uk["stringency_with_nans"].ffill()

mask_date = (df_owid_uk["date"] > '2020-03-01') & (df_owid_uk["date"] < '2020-07-01')
sub_uk = df_owid_uk[mask_date]

plt.plot(sub_uk["date"], sub_uk["stringency_ffill"], label="Forward-Filled", color='green', linewidth=2, linestyle='--')
plt.scatter(sub_uk["date"], sub_uk["stringency_with_nans"], label="Sparse Raw Data", color='red', zorder=5)
plt.title("Effect of Forward Fill (ffill) on Policy Indexes")
plt.xlabel("Date")
plt.ylabel("Stringency Index (0-100)")
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(ARTIFACT_DIR, "ffill_plot.png"), dpi=150)
plt.close()

print("Plots saved successfully.")
