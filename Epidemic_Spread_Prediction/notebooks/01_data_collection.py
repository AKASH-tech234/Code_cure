# %%
import pandas as pd
import os

# Define paths relative to the script location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')

# URLs for datasets
JHU_CONFIRMED_URL = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"
JHU_DEATHS_URL = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"
OWID_URL = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv"

# %% Download JHU Data
print("Downloading JHU Confirmed Cases...")
df_confirmed = pd.read_csv(JHU_CONFIRMED_URL)
df_confirmed.to_csv(os.path.join(RAW_DATA_DIR, "jhu_confirmed.csv"), index=False)
print(f"Saved JHU Confirmed Cases. Shape: {df_confirmed.shape}")

print("Downloading JHU Deaths...")
df_deaths = pd.read_csv(JHU_DEATHS_URL)
df_deaths.to_csv(os.path.join(RAW_DATA_DIR, "jhu_deaths.csv"), index=False)
print(f"Saved JHU Deaths. Shape: {df_deaths.shape}")

# %% Download OWID Data
print("Downloading OWID Data (this may take a bit longer as the dataset is large)...")
df_owid = pd.read_csv(OWID_URL)
df_owid.to_csv(os.path.join(RAW_DATA_DIR, "owid_covid_data.csv"), index=False)
print(f"Saved OWID Data. Shape: {df_owid.shape}")

print("All downloads completed and saved to data/raw/")
