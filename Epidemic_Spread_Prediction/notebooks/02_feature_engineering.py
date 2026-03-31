
import pandas as pd
import numpy as np
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')
PROC_DATA_DIR = os.path.join(BASE_DIR, 'data', 'processed')


print("Loading raw datasets..")
jhu_c_path = os.path.join(RAW_DATA_DIR, "jhu_confirmed.csv")
jhu_d_path = os.path.join(RAW_DATA_DIR, "jhu_deaths.csv")
owid_path = os.path.join(RAW_DATA_DIR, "owid_covid_data.csv")

if not all([os.path.exists(jhu_c_path), os.path.exists(jhu_d_path), os.path.exists(owid_path)]):
    raise FileNotFoundError("Raw datasets are missing. Please run 01_data_collection.py first.")

df_jhu_c = pd.read_csv(jhu_c_path)
df_jhu_d = pd.read_csv(jhu_d_path)
df_owid = pd.read_csv(owid_path)

# %%
print("Transforming JHU Data from Wide to Long format...")
# The JHU data has columns: Province/State, Country/Region, Lat, Long, and dates (e.g. 1/22/20)
id_vars = ["Province/State", "Country/Region", "Lat", "Long"]

# Melt Confirmed
df_jhu_c_long = df_jhu_c.melt(id_vars=id_vars, var_name="Date", value_name="Confirmed")
# Melt Deaths
df_jhu_d_long = df_jhu_d.melt(id_vars=id_vars, var_name="Date", value_name="Deaths")

# Convert Date column to datetime
df_jhu_c_long["Date"] = pd.to_datetime(df_jhu_c_long["Date"], errors='coerce')
df_jhu_d_long["Date"] = pd.to_datetime(df_jhu_d_long["Date"], errors='coerce')

# Merge JHU datasets
df_jhu = pd.merge(df_jhu_c_long, df_jhu_d_long, on=id_vars + ["Date"], how="inner")
df_jhu = df_jhu.sort_values(["Country/Region", "Province/State", "Date"])

# %%
print("Creating temporal features for JHU dataset...")
df_jhu["DayOfWeek"] = df_jhu["Date"].dt.dayofweek
df_jhu["Month"] = df_jhu["Date"].dt.month
df_jhu["IsWeekend"] = df_jhu["DayOfWeek"].isin([5, 6]).astype(int)

# Group by to calculate daily new cases/deaths since JHU is cumulative
# If Province is NaN, fill with "Entire Country"
df_jhu["Province_State_Filled"] = df_jhu["Province/State"].fillna("Entire Country")

print("Calculating daily differences (New Confirmed/Deaths)...")
# Calculate daily new cases (differencing)
df_jhu["New_Confirmed"] = df_jhu.groupby(["Country/Region", "Province_State_Filled"])["Confirmed"].diff().fillna(0)
# Ensure no negative new cases (reporting anomalies)
df_jhu["New_Confirmed"] = df_jhu["New_Confirmed"].clip(lower=0)

df_jhu["New_Deaths"] = df_jhu.groupby(["Country/Region", "Province_State_Filled"])["Deaths"].diff().fillna(0)
df_jhu["New_Deaths"] = df_jhu["New_Deaths"].clip(lower=0)

# %%
print("Engineering Lag and Rolling Features for JHU...")
groups = df_jhu.groupby(["Country/Region", "Province_State_Filled"])

# Lags
df_jhu["New_Confirmed_Lag1"] = groups["New_Confirmed"].shift(1)
df_jhu["New_Confirmed_Lag3"] = groups["New_Confirmed"].shift(3)
df_jhu["New_Confirmed_Lag7"] = groups["New_Confirmed"].shift(7)

# Rolling Averages (smoothed cases)
# We use reset_index to match the original dataframe's index
df_jhu["New_Confirmed_Roll7"] = groups["New_Confirmed"].rolling(window=7, min_periods=1).mean().reset_index(level=[0,1], drop=True)
df_jhu["New_Confirmed_Roll14"] = groups["New_Confirmed"].rolling(window=14, min_periods=1).mean().reset_index(level=[0,1], drop=True)

# Drop the temporary column
df_jhu = df_jhu.drop(columns=["Province_State_Filled"])

# %%
print("Processing OWID Data...")
df_owid["date"] = pd.to_datetime(df_owid["date"], errors="coerce")

# OWID already has new_cases, new_deaths, reproduction_rate, stringency_index, etc.
# Select a subset of important features for modeling disease spread
owid_cols = ["iso_code", "location", "date", "total_cases", "new_cases", "total_deaths", "new_deaths", 
             "stringency_index", "reproduction_rate", "people_vaccinated_per_hundred"]
available_cols = [c for c in owid_cols if c in df_owid.columns]
df_owid_subset = df_owid[available_cols].copy()

# Temporal features
df_owid_subset["Month"] = df_owid_subset["date"].dt.month
df_owid_subset["DayOfWeek"] = df_owid_subset["date"].dt.dayofweek

print("Engineering Lags for OWID...")
df_owid_subset = df_owid_subset.sort_values(["location", "date"])
owid_groups = df_owid_subset.groupby("location")

df_owid_subset["New_Cases_Lag1"] = owid_groups["new_cases"].shift(1)
df_owid_subset["New_Cases_Roll7"] = owid_groups["new_cases"].rolling(window=7, min_periods=1).mean().reset_index(level=0, drop=True)

print("Handling Missing Values in external indicators...")
# Fill missing values for factors like stringency index using forward fill within each country
if "stringency_index" in df_owid_subset.columns:
    df_owid_subset["stringency_index"] = owid_groups["stringency_index"].ffill()

if "reproduction_rate" in df_owid_subset.columns:
    # Reproduction rate changes smoothly, interpolate or ffill
    df_owid_subset["reproduction_rate"] = owid_groups["reproduction_rate"].transform(lambda x: x.interpolate(method='linear').ffill().bfill())

# %%
print("Saving processed datasets...")
# Save processed JHU
file_jhu = os.path.join(PROC_DATA_DIR, "jhu_processed.csv")
df_jhu.to_csv(file_jhu, index=False)
print(f"Saved JHU processed data to {file_jhu}. Shape: {df_jhu.shape}")

# Save processed OWID
file_owid = os.path.join(PROC_DATA_DIR, "owid_processed.csv")
df_owid_subset.to_csv(file_owid, index=False)
print(f"Saved OWID processed data to {file_owid}. Shape: {df_owid_subset.shape}")

print("Feature engineering completed successfully!")
