# %%
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt

# Metrics
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error, r2_score
from sklearn.preprocessing import MinMaxScaler

# Models
from prophet import Prophet
import xgboost as xgb
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

# %% [markdown]
# ## 1. Config & Data Source
# %%
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC_DATA_DIR = os.path.join(BASE_DIR, 'data', 'processed')

# DEBUG_MODE: If True, trains only on a subset of countries to iterate quickly.
# Hardware Optimization Note: For a machine with an i5 14th Gen, 16GB CPU RAM, and 
# an RTX 2050 (4GB VRAM), your system is excellent for XGBoost but deep learning 
# sequence generation will eat up CPU RAM quickly if evaluating the entire globe simultaneously.
# The 4GB VRAM *can* train perfectly here because our sliding window arrays are small!
DEBUG_MODE = True
TARGET_COL = "New_Confirmed_Roll7"

print("Loading dataset...")
df = pd.read_csv(os.path.join(PROC_DATA_DIR, "jhu_processed.csv"))
df["Date"] = pd.to_datetime(df["Date"])

# Create additional robust explanatory features
df["New_Deaths_Lag1"] = df.groupby("Country/Region")["New_Deaths"].shift(1)
df["New_Confirmed_Roll14_Lag1"] = df.groupby("Country/Region")["New_Confirmed_Roll14"].shift(1)
df["Country_Cat"] = df["Country/Region"].astype("category")

df = df.dropna(subset=[TARGET_COL, "New_Confirmed_Lag1", "New_Deaths_Lag1", "New_Confirmed_Roll14_Lag1"]) # drop early NaNs

if DEBUG_MODE:
    print("DEBUG_MODE is ON. Filtering to Top 5 countries to save time...")
    top_countries = ["US", "India", "Brazil", "France", "United Kingdom"]
    df = df[df["Country/Region"].isin(top_countries)].copy()

print(f"Dataset shape: {df.shape}")

# Train / Test Split (Time-based: Let's use the last 30 days as our test set)
test_start_date = df["Date"].max() - pd.Timedelta(days=30)
train_df = df[df["Date"] < test_start_date].copy()
test_df = df[df["Date"] >= test_start_date].copy()

print(f"Train size: {train_df.shape}, Test size: {test_df.shape}")

# We will focus our final visual comparative evaluation on a single large country
EVAL_COUNTRY = "US"
train_us = train_df[train_df["Country/Region"] == EVAL_COUNTRY]
test_us = test_df[test_df["Country/Region"] == EVAL_COUNTRY]

# %% [markdown]
# ## 2. Tier 1: Statistical Baseline (Prophet)
# Prophet requires a univariate series per country, so we will benchmark it specifically for the EVAL_COUNTRY.
# %%
print("\n--- Training Prophet Baseline ---")
# Prophet requires columns to be named 'ds' and 'y'
prophet_train = train_us[["Date", TARGET_COL]].rename(columns={"Date": "ds", TARGET_COL: "y"})
prophet_test = test_us[["Date", TARGET_COL]].rename(columns={"Date": "ds", TARGET_COL: "y"})

# Initialize and fit
model_prophet = Prophet(daily_seasonality=False, yearly_seasonality=True)
model_prophet.fit(prophet_train)

# Predict
future = model_prophet.make_future_dataframe(periods=len(prophet_test))
forecast = model_prophet.predict(future)

# Extract test period predictions
prophet_preds = forecast.tail(len(prophet_test))["yhat"].values
prophet_true = prophet_test["y"].values

mae_prophet = mean_absolute_error(prophet_true, prophet_preds)
rmse_prophet = np.sqrt(mean_squared_error(prophet_true, prophet_preds))
mape_prophet = mean_absolute_percentage_error(prophet_true, prophet_preds)
r2_prophet = r2_score(prophet_true, prophet_preds)
print(f"Prophet MAE ({EVAL_COUNTRY}): {mae_prophet:.2f} | RMSE: {rmse_prophet:.2f} | MAPE: {mape_prophet:.2%} | R2: {r2_prophet:.4f}")

# %% [markdown]
# ## 3. Tier 2: Global Tabular Regression (XGBoost)
# XGBoost can train on ALL countries simultaneously because we give it the engineered lag features.
# %%
print("\n--- Training XGBoost Global Model ---")
features = ["DayOfWeek", "Month", "IsWeekend", "New_Confirmed_Lag1", "New_Confirmed_Lag3", "New_Confirmed_Lag7", "New_Deaths_Lag1", "New_Confirmed_Roll14_Lag1", "Country_Cat"]

X_train_xgb = train_df[features]
y_train_xgb = train_df[TARGET_COL]

X_test_xgb = test_df[features]
y_test_xgb = test_df[TARGET_COL]

model_xgb = xgb.XGBRegressor(
    n_estimators=500, 
    learning_rate=0.05, 
    max_depth=8, 
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    enable_categorical=True,
    tree_method="hist", # CPU hardware optimization (if you run out of VRAM), change to 'gpu_hist' to use the 2050
)

model_xgb.fit(X_train_xgb, y_train_xgb)

# Evaluate locally on EVAL_COUNTRY for fair comparison
xg_test_us = test_us[features]
xgb_preds = model_xgb.predict(xg_test_us)
mae_xgb = mean_absolute_error(test_us[TARGET_COL], xgb_preds)
rmse_xgb = np.sqrt(mean_squared_error(test_us[TARGET_COL], xgb_preds))
mape_xgb = mean_absolute_percentage_error(test_us[TARGET_COL], xgb_preds)
r2_xgb = r2_score(test_us[TARGET_COL], xgb_preds)
print(f"XGBoost MAE ({EVAL_COUNTRY}): {mae_xgb:.2f} | RMSE: {rmse_xgb:.2f} | MAPE: {mape_xgb:.2%} | R2: {r2_xgb:.4f}")

# %% [markdown]
# ## 4. Tier 3: Deep Sequence Modeling (TensorFlow LSTM)
# LSTMs require data to be reshaped into [Samples, Sequence_Length, Features]
# %%
print("\n--- Training Deep Learning LSTM Model ---")
# We must scale Neural Network inputs
scaler_X = MinMaxScaler()
scaler_y = MinMaxScaler()

# To ensure the 16GB RAM is perfectly optimized and no Data Leakage occurs between Countries,
# we isolate sequence building to specific grouped dataframes. For the comparative plot, we build the US set.
lstm_train_df = train_us.copy()
lstm_test_df = test_us.copy()

lstm_features = [f for f in features if f != "Country_Cat"]

# Fit scaler on training data only
seq_train_X = scaler_X.fit_transform(lstm_train_df[lstm_features])
seq_train_y = scaler_y.fit_transform(lstm_train_df[[TARGET_COL]])

seq_test_X = scaler_X.transform(lstm_test_df[lstm_features])
seq_test_y = scaler_y.transform(lstm_test_df[[TARGET_COL]])

def build_sequences(X_data, y_data, seq_len=14):
    X, y = [], []
    for i in range(len(X_data) - seq_len):
        X.append(X_data[i:(i + seq_len)])
        y.append(y_data[i + seq_len])
    return np.array(X), np.array(y)

SEQ_LEN = 7 # 7 days lookback
X_lstm_train, y_lstm_train = build_sequences(seq_train_X, seq_train_y, SEQ_LEN)
X_lstm_test, y_lstm_test = build_sequences(seq_test_X, seq_test_y, SEQ_LEN)

print(f"LSTM Sequence Shape: {X_lstm_train.shape}")

# Build Keras LSTM
model_lstm = Sequential([
    LSTM(64, activation='relu', input_shape=(SEQ_LEN, len(lstm_features)), return_sequences=False),
    Dropout(0.2),
    Dense(32, activation='relu'),
    Dense(1)
])

model_lstm.compile(optimizer='adam', loss='mse')

# Train. Tensorflow automatically hooks into your RTX 2050 if CUDA is installed.
history = model_lstm.fit(
    X_lstm_train, y_lstm_train,
    epochs=15 if DEBUG_MODE else 50,
    batch_size=32,
    validation_split=0.1,
    verbose=1
)

lstm_preds_scaled = model_lstm.predict(X_lstm_test)
lstm_preds = scaler_y.inverse_transform(lstm_preds_scaled).flatten()

# Because we lose SEQ_LEN days at the start of the test set to build the first window,
# we must truncate the true values and baseline predictions for a perfectly fair, mathematically identical comparison chart.
lstm_true = test_us[TARGET_COL].iloc[SEQ_LEN:].values
xgb_preds_trunc = xgb_preds[SEQ_LEN:]
prophet_preds_trunc = prophet_preds[SEQ_LEN:]

mae_lstm = mean_absolute_error(lstm_true, lstm_preds)
rmse_lstm = np.sqrt(mean_squared_error(lstm_true, lstm_preds))
mape_lstm = mean_absolute_percentage_error(lstm_true, lstm_preds)
r2_lstm = r2_score(lstm_true, lstm_preds)
print(f"LSTM MAE ({EVAL_COUNTRY}): {mae_lstm:.2f} | RMSE: {rmse_lstm:.2f} | MAPE: {mape_lstm:.2%} | R2: {r2_lstm:.4f}")

# %% [markdown]
# ## 5. Comparative Evaluation Graph
# %%
plt.figure(figsize=(14, 7))
plot_dates = test_us["Date"].iloc[SEQ_LEN:]

prophet_lbl = f'Prophet [MAE: {mae_prophet:.0f} | RMSE: {rmse_prophet:.0f} | MAPE: {mape_prophet:.0%} | R²: {r2_prophet:.2f}]'
xgb_lbl = f'XGBoost [MAE: {mae_xgb:.0f} | RMSE: {rmse_xgb:.0f} | MAPE: {mape_xgb:.0%} | R²: {r2_xgb:.2f}]'
lstm_lbl = f'LSTM [MAE: {mae_lstm:.0f} | RMSE: {rmse_lstm:.0f} | MAPE: {mape_lstm:.0%} | R²: {r2_lstm:.2f}]'

plt.plot(plot_dates, lstm_true, label='Actual 7-Day', color='black', linewidth=3)
plt.plot(plot_dates, prophet_preds_trunc, label=prophet_lbl, linestyle='--')
plt.plot(plot_dates, xgb_preds_trunc, label=xgb_lbl, linestyle='-.')
plt.plot(plot_dates, lstm_preds, label=lstm_lbl, color='red', linewidth=2)

plt.title(f"Model Performance Comparison on Unseen Future Data ({EVAL_COUNTRY})")
plt.xlabel("Date")
plt.ylabel("Cases")
plt.legend()
plt.tight_layout()

# Save plot
output_path = os.path.join(BASE_DIR, "artifacts", "model_comparison.png")
os.makedirs(os.path.dirname(output_path), exist_ok=True)
plt.savefig(output_path, dpi=150)
print(f"\nComparative plot saved to {output_path}")
plt.close()
