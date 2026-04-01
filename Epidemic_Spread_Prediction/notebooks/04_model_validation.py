"""
04_model_validation.py — XGBoost Epidemic Model Validation Suite (v2 — Leakage-Free)
======================================================================================
Fixes applied vs v1:
  1. POST-SPLIT rolling feature recomputation — no future data bleeds into training
  2. Purged TimeSeriesSplit (gap=14) — fold boundaries can't see through rolling windows
  3. Log-growth-rate target — stationary signal that can beat the naive 1-day baseline
  4. OWID features (stringency_index, reproduction_rate) — real epidemic policy signals
  5. L1/L2 regularization on baseline + Optuna search space includes regularization
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import os
import warnings
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit
import shap
from statsmodels.graphics.tsaplots import plot_acf
import optuna

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
optuna.logging.set_verbosity(optuna.logging.WARNING)

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC_DATA_DIR = os.path.join(BASE_DIR, 'data', 'processed')
ARTIFACT_DIR  = os.path.join(BASE_DIR, 'artifacts')
os.makedirs(ARTIFACT_DIR, exist_ok=True)

TARGET_COL = "New_Confirmed_Roll7"  # raw 7-day rolling average (cases)
EVAL_COUNTRY = "US"
N_PURGE   = 14   # rows to skip between CV train-end and val-start
EPSILON   = 1.0  # log(x+ε) guard to avoid log(0)

# -----------------------------------------------------------------------------
# 1. DATA LOADING
# -----------------------------------------------------------------------------
print("== Data Loading ==")
df = pd.read_csv(os.path.join(PROC_DATA_DIR, "jhu_processed.csv"))
df["Date"] = pd.to_datetime(df["Date"])

# OWID policy features (stringency_index = government restrictions 0-100,
# reproduction_rate = Rt; both are powerful epidemic predictors)
owid_path = os.path.join(PROC_DATA_DIR, "owid_processed.csv")
df_owid = pd.read_csv(owid_path, low_memory=False)
df_owid["date"] = pd.to_datetime(df_owid["date"])

# OWID calls US "United States", JHU calls it "US"
owid_us = df_owid[df_owid["location"] == "United States"][
    ["date", "stringency_index", "reproduction_rate"]
].copy()
owid_us.columns = ["Date", "stringency_index", "reproduction_rate"]

# Isolate US from JHU and merge OWID policy columns
df_us = df[df["Country/Region"] == EVAL_COUNTRY].copy()
df_us = df_us.sort_values("Date").reset_index(drop=True)
df_us = df_us.merge(owid_us, on="Date", how="left")
df_us["stringency_index"]  = df_us["stringency_index"].ffill().fillna(0.0)
df_us["reproduction_rate"] = df_us["reproduction_rate"].ffill().fillna(1.0)

# Drop any rows where raw New_Confirmed or target is missing
df_us = df_us.dropna(subset=[TARGET_COL, "New_Confirmed",
                               "New_Confirmed_Lag1", "New_Confirmed_Lag3",
                               "New_Confirmed_Lag7", "New_Deaths"]).reset_index(drop=True)

print(f"  US dataset shape: {df_us.shape}  |  Date range: {df_us['Date'].min().date()} → {df_us['Date'].max().date()}")

# -----------------------------------------------------------------------------
# 2. TRAIN/TEST SPLIT — done BEFORE any rolling feature computation
# -----------------------------------------------------------------------------
test_start_date = df_us["Date"].max() - pd.Timedelta(days=30)
train_df = df_us[df_us["Date"] < test_start_date].copy().reset_index(drop=True)
test_df  = df_us[df_us["Date"] >= test_start_date].copy().reset_index(drop=True)

print(f"  Train: {len(train_df)} rows | Test: {len(test_df)} rows")

# -----------------------------------------------------------------------------
# 3. POST-SPLIT ROLLING FEATURE ENGINEERING (zero leakage)
# -----------------------------------------------------------------------------
def engineer_features(train: pd.DataFrame, test: pd.DataFrame):
    """
    Recomputes all lag/rolling features AFTER the train/test split.
    Test features are derived by bridging with the tail of training data
    so the rolling window never sees forward-in-time test observations.
    """
    BRIDGE = 21  # rows of train tail needed to prime a 14-day rolling window

    # -- Training set features ----------------------------------------------
    train = train.copy()
    train["New_Deaths_Lag1"]         = train["New_Deaths"].shift(1)
    train["New_Confirmed_Roll14_Lag1"] = (
        train["New_Confirmed"].rolling(14, min_periods=1).mean().shift(1)
    )

    # -- Test set features (bridged to avoid cold-start artefacts) ---------
    bridge = pd.concat([train.tail(BRIDGE), test], ignore_index=True)
    bridge["New_Deaths_Lag1"] = bridge["New_Deaths"].shift(1)
    bridge["New_Confirmed_Roll14_Lag1"] = (
        bridge["New_Confirmed"].rolling(14, min_periods=1).mean().shift(1)
    )
    test_feats = bridge.iloc[BRIDGE:].copy().reset_index(drop=True)

    # Drop NaN rows from lag shifts at the very start of each partition
    train = train.dropna(subset=["New_Deaths_Lag1", "New_Confirmed_Roll14_Lag1"]).reset_index(drop=True)
    test_feats = test_feats.dropna(subset=["New_Deaths_Lag1", "New_Confirmed_Roll14_Lag1"]).reset_index(drop=True)

    return train, test_feats

train_df, test_df = engineer_features(train_df, test_df)

# -----------------------------------------------------------------------------
# 4. LOG-GROWTH TARGET
#    Predict log(Roll7_t / Roll7_{t-1}) instead of raw count.
#    This removes the nonstationary trend so XGBoost competes on the growth
#    signal rather than absolute magnitude — and can actually beat the naive
#    "tomorrow = today" baseline.
# -----------------------------------------------------------------------------
def log_growth(series: pd.Series) -> pd.Series:
    return np.log(series + EPSILON) - np.log(series.shift(1) + EPSILON)

def inv_log_growth(prev_roll7: np.ndarray, lg_pred: np.ndarray) -> np.ndarray:
    """Recover predicted case count from log-growth prediction."""
    return (prev_roll7 + EPSILON) * np.exp(lg_pred) - EPSILON

train_df["LogGrowth"] = log_growth(train_df[TARGET_COL])
test_df["LogGrowth"]  = log_growth(test_df[TARGET_COL])

train_df = train_df.dropna(subset=["LogGrowth"]).reset_index(drop=True)
test_df  = test_df.dropna(subset=["LogGrowth"]).reset_index(drop=True)

TARGET_TRAIN = "LogGrowth"

# -----------------------------------------------------------------------------
# 5. FEATURE / TARGET ARRAYS
# -----------------------------------------------------------------------------
FEATURES = [
    # Calendar signals
    "DayOfWeek", "Month", "IsWeekend",
    # Lag features (purely backward-looking → no leakage)
    "New_Confirmed_Lag1", "New_Confirmed_Lag3", "New_Confirmed_Lag7",
    "New_Deaths_Lag1",
    # Rolling feature recomputed post-split
    "New_Confirmed_Roll14_Lag1",
    # OWID epidemic policy signals (new)
    "stringency_index", "reproduction_rate",
]

X_train = train_df[FEATURES].astype(float)
y_train = train_df[TARGET_TRAIN].astype(float)

X_test       = test_df[FEATURES].astype(float)
y_test_raw   = test_df[TARGET_COL].astype(float)            # original scale for MAE
prev_roll7   = test_df[TARGET_COL].shift(1).bfill().values  # for inverse transform

# Baseline model with explicit regularization to curb overfitting
baseline_model = xgb.XGBRegressor(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=6,        # reduced from 8 → less overfitting
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,      # L1 (sparse feature weights)
    reg_lambda=1.5,     # L2 (weight shrinkage)
    random_state=42,
    tree_method="hist",
)

# -----------------------------------------------------------------------------
# TEST 1: NOISE FLOOR CHECK
# -----------------------------------------------------------------------------
print("\n-- 1. Noise Floor Check (Irreducible Error) --")

naive_1d_preds   = test_df[TARGET_COL].shift(1).bfill()
naive_1d_mae     = mean_absolute_error(y_test_raw.iloc[1:], naive_1d_preds.iloc[1:])
print(f"  Naive 1-day shift MAE:    {naive_1d_mae:.0f}")

naive_7d_preds   = test_df[TARGET_COL].shift(7).bfill()
naive_7d_mae     = mean_absolute_error(y_test_raw.iloc[7:], naive_7d_preds.iloc[7:])
print(f"  Seasonal Naive (7-day):   {naive_7d_mae:.0f}")

print(f"  → Model must beat {naive_1d_mae:.0f} to add value over a trivial baseline")

# -----------------------------------------------------------------------------
# TEST 2: PURGED TIMESERIESSPLIT CROSS VALIDATION
# -----------------------------------------------------------------------------
print(f"\n-- 2. TimeSeriesSplit CV (n=5, gap={N_PURGE} purge rows) --")

tscv = TimeSeriesSplit(n_splits=5, gap=N_PURGE)
cv_maes = []

for i, (tr_idx, va_idx) in enumerate(tscv.split(X_train)):
    cv_X_tr, cv_X_va = X_train.iloc[tr_idx], X_train.iloc[va_idx]
    cv_y_tr          = y_train.iloc[tr_idx]
    cv_y_va_raw      = train_df[TARGET_COL].iloc[va_idx].values
    cv_prev          = train_df[TARGET_COL].shift(1).iloc[va_idx].values

    m = xgb.XGBRegressor(
        n_estimators=300, learning_rate=0.05, max_depth=6,
        subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.1, reg_lambda=1.5,
        random_state=42, tree_method="hist",
    )
    m.fit(cv_X_tr, cv_y_tr)
    cv_lg_preds = m.predict(cv_X_va)
    cv_preds    = inv_log_growth(cv_prev, cv_lg_preds)
    mae         = mean_absolute_error(cv_y_va_raw, cv_preds)
    cv_maes.append(mae)
    print(f"  Fold {i+1} MAE: {mae:.0f}")

avg_cv  = np.mean(cv_maes)
std_cv  = np.std(cv_maes)
ratio   = max(cv_maes) / max(min(cv_maes), 1)
print(f"  Avg CV MAE: {avg_cv:.0f}  |  Std: {std_cv:.0f}  |  Max/Min: {ratio:.1f}x  (healthy target: <3x)")

# -----------------------------------------------------------------------------
# TEST 3: LEARNING CURVE
# -----------------------------------------------------------------------------
print("\n-- 3. Learning Curve Analysis --")

train_sizes = [0.3, 0.5, 0.7, 0.9, 1.0]
lc_maes = []
for size in train_sizes:
    n = max(20, int(len(X_train) * size))
    m = xgb.XGBRegressor(
        n_estimators=300, learning_rate=0.05, max_depth=6,
        subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.1, reg_lambda=1.5,
        random_state=42, tree_method="hist",
    )
    m.fit(X_train.iloc[:n], y_train.iloc[:n])
    lc_lg    = m.predict(X_test)
    lc_preds = inv_log_growth(prev_roll7, lc_lg)
    mae      = mean_absolute_error(y_test_raw.values, lc_preds)
    lc_maes.append(mae)
    print(f"  Train size {size:.0%} (n={n}): Test MAE = {mae:.0f}")

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot([s * 100 for s in train_sizes], lc_maes, marker='o', color='#2ecc71', linewidth=2.5)
ax.axhline(naive_1d_mae, color='#e74c3c', linestyle='--', linewidth=1.5, label=f'Naive baseline ({naive_1d_mae:.0f})')
ax.set_title("Learning Curve — Monotonic = Healthy (No Overfitting)")
ax.set_xlabel("Training Data Size (%)")
ax.set_ylabel("Test MAE (original case scale)")
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(ARTIFACT_DIR, "learning_curve.png"), dpi=150)
plt.close()

# -----------------------------------------------------------------------------
# TEST 4: SHAP FEATURE IMPORTANCE
# -----------------------------------------------------------------------------
print("\n-- 4. Feature Importance Saturation (SHAP) --")

shap_model = xgb.XGBRegressor(
    max_depth=6, n_estimators=100, random_state=42,
    reg_alpha=0.1, reg_lambda=1.5, tree_method="hist"
)
shap_model.fit(X_train.values, y_train.values)

explainer   = shap.TreeExplainer(shap_model)
shap_values = explainer(X_train.values, check_additivity=False)
shap_values.feature_names = FEATURES

shap.summary_plot(shap_values, X_train, show=False)
plt.tight_layout()
plt.savefig(os.path.join(ARTIFACT_DIR, "shap_summary.png"), dpi=150)
plt.close()
print("  Saved SHAP summary → artifacts/shap_summary.png")
print("  ** Check: after leakage fix, Roll14_Lag1 dominance should reduce;")
print("     reproduction_rate / stringency_index should now appear as meaningful contributors.")

# -----------------------------------------------------------------------------
# TEST 5: RESIDUAL ACF (WHITE NOISE CHECK)
# -----------------------------------------------------------------------------
print("\n-- 5. Residual Analysis (White Noise / ACF Check) --")

baseline_model.fit(X_train, y_train)
lg_preds_test  = baseline_model.predict(X_test)
preds_raw_test = inv_log_growth(prev_roll7, lg_preds_test)
residuals      = y_test_raw.values - preds_raw_test

test_mae_baseline = mean_absolute_error(y_test_raw.values, preds_raw_test)

fig, ax = plt.subplots(figsize=(10, 4))
plot_acf(residuals, lags=min(20, len(residuals) - 1), alpha=0.05, ax=ax)
plt.title("Residual ACF — Spikes outside band = unexploited pattern remaining")
plt.tight_layout()
plt.savefig(os.path.join(ARTIFACT_DIR, "residual_acf.png"), dpi=150)
plt.close()

beat_naive = test_mae_baseline < naive_1d_mae
print(f"  Baseline Test MAE (log-growth → original scale): {test_mae_baseline:.0f}")
print(f"  Naive 1-day baseline:                            {naive_1d_mae:.0f}")
print(f"  Beat naive? {'[YES] YES — model adds genuine value' if beat_naive else '[NO] NO — further work needed'}")
print("  Saved Residual ACF → artifacts/residual_acf.png")

# -----------------------------------------------------------------------------
# TEST 6: OPTUNA HYPERPARAMETER SEARCH (purged CV, log-growth, with regularization)
# -----------------------------------------------------------------------------
print("\n-- 6. Optuna Hyperparameter Search (30 trials, purged CV) --")

def objective(trial):
    params = {
        "n_estimators":     trial.suggest_int("n_estimators", 100, 800),
        "max_depth":        trial.suggest_int("max_depth", 3, 7),
        "learning_rate":    trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "subsample":        trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_alpha":        trial.suggest_float("reg_alpha", 0.0, 3.0),
        "reg_lambda":       trial.suggest_float("reg_lambda", 0.5, 5.0),
        "tree_method":      "hist",
        "random_state":     42,
    }
    tscv_opt = TimeSeriesSplit(n_splits=3, gap=N_PURGE)
    fold_maes = []
    for tr_idx, va_idx in tscv_opt.split(X_train):
        m = xgb.XGBRegressor(**params)
        m.fit(X_train.iloc[tr_idx], y_train.iloc[tr_idx])
        lg_p = m.predict(X_train.iloc[va_idx])
        prv  = train_df[TARGET_COL].shift(1).bfill().iloc[va_idx].values
        p    = inv_log_growth(prv, lg_p)
        fold_maes.append(mean_absolute_error(train_df[TARGET_COL].iloc[va_idx].values, p))
    return np.mean(fold_maes)

study = optuna.create_study(direction="minimize")
print("  Running Optuna trials...")
study.optimize(objective, n_trials=30)

print(f"\n  Best Optuna CV MAE:  {study.best_value:.0f}")
print(f"  Best params: {study.best_params}")

# Retrain final model with best params on full training set, evaluate on held-out test
final_model = xgb.XGBRegressor(**study.best_params, tree_method="hist", random_state=42)
final_model.fit(X_train, y_train)
final_lg     = final_model.predict(X_test)
final_preds  = inv_log_growth(prev_roll7, final_lg)
final_mae    = mean_absolute_error(y_test_raw.values, final_preds)

beat_naive_optuna = final_mae < naive_1d_mae
print(f"  Optuna Final Test MAE:  {final_mae:.0f}")
print(f"  Naive Baseline MAE:     {naive_1d_mae:.0f}")
print(f"  Beat naive? {'[YES] YES' if beat_naive_optuna else '[NO] NO'}")

# -----------------------------------------------------------------------------
# TEST 7: QUANTILE REGRESSION — PREDICTION INTERVALS
# -----------------------------------------------------------------------------
# XGBoost 2.0+ supports native quantile loss via objective='reg:quantileerror'.
# We train three separate models (q10, q50, q90) on the same log-growth target
# and inverse-transform all three back to the original case scale.
# This gives an 80% prediction interval (PI) alongside the point forecast.
#
# Two metrics reported:
#   Coverage   — % of actuals that fall inside the [q10, q90] interval (target: ~80%)
#   Sharpness  — mean width of the PI in cases (narrower = more informative)
# -----------------------------------------------------------------------------
print("\n-- 7. Quantile Regression — Prediction Intervals --")

QUANTILES = [0.10, 0.50, 0.90]
q_base_params = dict(
    n_estimators      = study.best_params.get("n_estimators", 300),
    max_depth         = study.best_params.get("max_depth", 6),
    learning_rate     = study.best_params.get("learning_rate", 0.05),
    subsample         = study.best_params.get("subsample", 0.8),
    colsample_bytree  = study.best_params.get("colsample_bytree", 0.8),
    reg_alpha         = study.best_params.get("reg_alpha", 0.1),
    reg_lambda        = study.best_params.get("reg_lambda", 1.5),
    tree_method       = "hist",
    random_state      = 42,
)

q_preds_raw = {}
for q in QUANTILES:
    qm = xgb.XGBRegressor(
        objective      = "reg:quantileerror",
        quantile_alpha = q,
        **q_base_params,
    )
    qm.fit(X_train, y_train)
    lg_q        = qm.predict(X_test)
    raw_q       = inv_log_growth(prev_roll7, lg_q)
    q_preds_raw[q] = raw_q
    print(f"  q={q:.2f}  Test MAE: {mean_absolute_error(y_test_raw.values, raw_q):.0f}")

# Interval coverage and sharpness
lower  = q_preds_raw[0.10]
median = q_preds_raw[0.50]
upper  = q_preds_raw[0.90]
actual = y_test_raw.values

in_band  = np.sum((actual >= lower) & (actual <= upper))
coverage = in_band / len(actual)
sharpness = np.mean(upper - lower)

print(f"\n  80% Prediction Interval — Coverage : {coverage:.1%}  (target ~80%)")
print(f"  80% Prediction Interval — Sharpness: {sharpness:.0f} cases  (narrower = better)")

# ── Plot ───────────────────────────────────────────────────────────────────
dates = test_df["Date"].values

fig, ax = plt.subplots(figsize=(13, 6))

ax.fill_between(dates, lower, upper,
                alpha=0.25, color="#3498db", label="80% PI  [q10 — q90]")
ax.plot(dates, actual,  color="black",    linewidth=2.5, label=f"Actual 7-day roll")
ax.plot(dates, median,  color="#e74c3c",  linewidth=2,   linestyle="--",
        label=f"q50 (median) — MAE {mean_absolute_error(actual, median):.0f}")
ax.plot(dates, lower,   color="#3498db",  linewidth=1,   linestyle=":",  alpha=0.7,
        label=f"q10 lower bound")
ax.plot(dates, upper,   color="#3498db",  linewidth=1,   linestyle=":",  alpha=0.7,
        label=f"q90 upper bound")

ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
ax.set_title(
    f"Quantile Regression — 80% Prediction Interval (US, 30-day holdout)\n"
    f"Coverage: {coverage:.1%}  |  Sharpness: {sharpness:.0f} cases",
    fontsize=13,
)
ax.set_xlabel("Date")
ax.set_ylabel("7-Day Rolling Cases")
ax.legend(loc="upper left", fontsize=9)
ax.grid(True, alpha=0.25)
plt.tight_layout()
plt.savefig(os.path.join(ARTIFACT_DIR, "quantile_pi.png"), dpi=150)
plt.close()
print("  Saved Quantile PI chart  artifacts/quantile_pi.png")

# Calibration check: q50 median MAE vs point-forecast MAE
q50_mae = mean_absolute_error(actual, median)
print(f"\n  Calibration: q50 MAE = {q50_mae:.0f}  vs  point-forecast MAE = {test_mae_baseline:.0f}")
if q50_mae < test_mae_baseline * 1.1:
    print("  [OK] Median quantile and point forecast are well-aligned.")
else:
    print("  [WARN] Large divergence between q50 and point forecast — check target skew.")

# -----------------------------------------------------------------------------
# SUMMARY DASHBOARD
# -----------------------------------------------------------------------------
print("\n" + "=" * 60)
print(" VALIDATION SUITE SUMMARY")
print("=" * 60)
print(f"  Noise floor  — Naive 1-day MAE:       {naive_1d_mae:.0f}")
print(f"  CV stability — Avg MAE:               {avg_cv:.0f} +/- {std_cv:.0f}")
print(f"                 Max/Min fold ratio:    {ratio:.1f}x  (healthy: <3x)")
print(f"  Learning crv — Final 100% MAE:        {lc_maes[-1]:.0f}  (should be lowest)")
print(f"  Test MAE     — Baseline model:        {test_mae_baseline:.0f}")
print(f"  Test MAE     — Optuna optimized:      {final_mae:.0f}")
print(f"  Quantile     — q50 (median) MAE:      {q50_mae:.0f}")
print(f"  Quantile     — 80% PI Coverage:       {coverage:.1%}  (target ~80%)")
print(f"  Quantile     — 80% PI Sharpness:      {sharpness:.0f} cases")
print(f"  Beat naive?  — {'[YES]' if beat_naive_optuna else '[NO]'}")
convergence = abs(final_mae - study.best_value) / max(study.best_value, 1)
print(f"  CV ↔ Test gap: {convergence:.1%}  (small % = no test-set overfitting)")
print("=" * 60)
print("Validation Suite Complete.")

