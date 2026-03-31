# Model Integration Specification
## Epidemic Spread Prediction — API Contract for Frontend / Backend / RAG

> This document is written for teammates building the **frontend, backend REST API, and RAG pipeline** around the trained XGBoost epidemic prediction model. It defines exact input/output contracts so you can integrate without reading any model code.

---

## 1. What the Model Does (Plain English)

Given the **last 14 days of COVID-19 case/death data + current government policy indicators** for a country, the model predicts:

1. **The 7-day rolling average of new confirmed cases** for tomorrow (point forecast)
2. **An 80% prediction interval** — a lower and upper bound that the actual value will fall inside 80% of the time

It works in log-growth space internally (predicts `log(tomorrow/today)`) and converts back to raw case counts before returning results.

---

## 2. Model Input — What You Must Provide

The model needs **one row of feature data per prediction request**. All features describe the **current state of the epidemic on the day you want to predict from**.

### 2a. Required Input Fields

| Field | Type | Range | Description | How to Get It |
|-------|------|-------|-------------|---------------|
| `DayOfWeek` | `int` | 0–6 | Day of week of the prediction date (0=Mon, 6=Sun) | Computed from date |
| `Month` | `int` | 1–12 | Calendar month of the prediction date | Computed from date |
| `IsWeekend` | `int` | 0 or 1 | 1 if Saturday/Sunday, else 0 | Computed from date |
| `New_Confirmed_Lag1` | `float` | ≥ 0 | New confirmed cases **1 day ago** | Historical data |
| `New_Confirmed_Lag3` | `float` | ≥ 0 | New confirmed cases **3 days ago** | Historical data |
| `New_Confirmed_Lag7` | `float` | ≥ 0 | New confirmed cases **7 days ago** | Historical data |
| `New_Deaths_Lag1` | `float` | ≥ 0 | New deaths **1 day ago** | Historical data |
| `New_Confirmed_Roll14_Lag1` | `float` | ≥ 0 | **14-day rolling mean** of new cases, ending 1 day ago | Needs 14 days of history |
| `stringency_index` | `float` | 0–100 | Government restriction level (Oxford index). 0=no restrictions, 100=full lockdown | OWID API or manual entry |
| `reproduction_rate` | `float` | 0.1–5.0 | Effective reproduction number Rt. <1 = declining, >1 = growing | OWID API or estimate |

> **Minimum history required:** To compute `New_Confirmed_Roll14_Lag1`, the backend must store at least **15 days** of historical daily new cases for the requested country.

### 2b. Optional Context Fields (for frontend display only, not fed to model)

| Field | Type | Description |
|-------|------|-------------|
| `country` | `string` | Country name (e.g. `"US"`, `"India"`) |
| `prediction_date` | `string` (ISO 8601) | The date being predicted for, e.g. `"2024-03-15"` |
| `prev_Roll7` | `float` | Yesterday's 7-day rolling average — needed for inverse transform |

---

## 3. Model Output — What You Get Back

The model returns **one JSON object** per prediction:

### 3a. Output Schema

```json
{
  "prediction_date": "2024-03-15",
  "country": "US",
  "point_forecast": {
    "predicted_roll7_cases": 45230.5,
    "description": "Expected 7-day rolling average of new confirmed cases"
  },
  "prediction_interval_80pct": {
    "lower_q10": 31800.0,
    "median_q50": 44100.0,
    "upper_q90": 68500.0,
    "coverage_guarantee": "80% — actual value falls in this range 80% of the time"
  },
  "model_metadata": {
    "target": "New_Confirmed_Roll7",
    "model_type": "XGBoost (log-growth, quantile regression)",
    "naive_baseline_mae": 1682,
    "model_mae": 1394,
    "improvement_over_naive_pct": 17.1
  }
}
```

### 3b. Field Definitions

| Output Field | Type | Description |
|-------------|------|-------------|
| `predicted_roll7_cases` | `float` | **Main number for the frontend.** Predicted 7-day rolling average of new daily cases |
| `lower_q10` | `float` | 10th percentile — optimistic lower bound (cases unlikely to go below this) |
| `median_q50` | `float` | 50th percentile — the model's median prediction |
| `upper_q90` | `float` | 90th percentile — pessimistic upper bound (cases likely below this) |
| `naive_baseline_mae` | `int` | Reference: what a trivial "tomorrow = today" model achieves |
| `model_mae` | `int` | What this model achieves on the validation set |

---

## 4. REST API Contract (Suggested FastAPI Schema)

The backend developer should expose this model as a single POST endpoint:

### Endpoint: `POST /api/v1/predict`

**Request Body (JSON):**
```json
{
  "country": "US",
  "prediction_date": "2024-03-15",
  "features": {
    "DayOfWeek": 4,
    "Month": 3,
    "IsWeekend": 0,
    "New_Confirmed_Lag1": 48200.0,
    "New_Confirmed_Lag3": 51000.0,
    "New_Confirmed_Lag7": 44800.0,
    "New_Deaths_Lag1": 320.0,
    "New_Confirmed_Roll14_Lag1": 49150.0,
    "stringency_index": 42.6,
    "reproduction_rate": 0.95
  },
  "prev_Roll7": 46800.0
}
```

**Successful Response `200 OK` (JSON):**
```json
{
  "prediction_date": "2024-03-15",
  "country": "US",
  "point_forecast": {
    "predicted_roll7_cases": 45230.5
  },
  "prediction_interval_80pct": {
    "lower_q10": 31800.0,
    "median_q50": 44100.0,
    "upper_q90": 68500.0
  },
  "model_metadata": {
    "model_mae": 1394,
    "naive_baseline_mae": 1682,
    "improvement_over_naive_pct": 17.1
  }
}
```

**Error Response `422 Unprocessable Entity`:**
```json
{
  "error": "missing_field",
  "message": "reproduction_rate is required but was not provided",
  "missing_fields": ["reproduction_rate"]
}
```

### Batch Prediction Endpoint: `POST /api/v1/predict/batch`

For forecasting N days ahead (rolling multi-step):

**Request Body:**
```json
{
  "country": "US",
  "start_date": "2024-03-15",
  "horizon_days": 7,
  "history": [
    {
      "date": "2024-03-01",
      "new_confirmed": 48200,
      "new_deaths": 320,
      "stringency_index": 42.6,
      "reproduction_rate": 0.95
    },
    // ... 14 more days minimum
  ]
}
```

**Response:**
```json
{
  "country": "US",
  "forecasts": [
    {
      "prediction_date": "2024-03-15",
      "predicted_roll7_cases": 45230.5,
      "lower_q10": 31800.0,
      "upper_q90": 68500.0
    },
    {
      "prediction_date": "2024-03-16",
      "predicted_roll7_cases": 43900.0,
      "lower_q10": 29200.0,
      "upper_q90": 65100.0
    }
    // ... up to horizon_days entries
  ]
}
```

> **Important for batch:** Each subsequent day's features are computed from the *previous day's prediction* (autoregressive rollout). Uncertainty widens with each step.

---

## 5. What the Backend Must Store (Database Schema)

The backend needs to maintain a rolling history table to compute lag features on-demand:

```sql
CREATE TABLE epidemic_daily_data (
    id            SERIAL PRIMARY KEY,
    country       VARCHAR(100) NOT NULL,
    date          DATE NOT NULL,
    new_confirmed FLOAT,          -- Daily new confirmed cases (differenced, clipped ≥0)
    new_deaths    FLOAT,          -- Daily new deaths
    roll7         FLOAT,          -- 7-day rolling average (store for quick lookup)
    stringency_index   FLOAT,     -- From OWID or manual input (0-100)
    reproduction_rate  FLOAT,     -- Rt value (~0.5-3.0)
    UNIQUE(country, date)
);
```

**On prediction request**, the backend:
1. Queries the last 15 rows for `country` ordered by `date DESC`
2. Computes `New_Confirmed_Lag1/3/7` from the date offsets
3. Computes `New_Confirmed_Roll14_Lag1` as `mean(new_confirmed rows -2 to -15)`
4. Reads `stringency_index` and `reproduction_rate` from the latest row or from request body
5. Passes all 10 features to the model

---

## 6. RAG Pipeline Integration

The RAG (Retrieval-Augmented Generation) teammate needs to know what **context documents** to index and what **query outputs** the model provides.

### 6a. Documents to Index for RAG

The RAG retrieval store should contain documents that explain *why* predictions are what they are:

| Document Type | Source | Content |
|--------------|--------|---------|
| **Policy briefs** | OWID, WHO | Relationship between `stringency_index` changes and case trends (7–14 day delay) |
| **Epidemic reports** | CDC, ECDC | When Rt crosses 1.0, cases begin exponential growth in ~5–7 days |
| **Historical wave data** | JHU processed CSV | Country-specific surge events and their feature fingerprints |
| **SHAP explanations** | Model output | Per-prediction feature contributions (what drove the forecast up or down) |
| **Model card** | This document | Model limitations, MAE, what the prediction interval means |

### 6b. RAG Query Context Format

When a user asks *"Why will cases in the US rise next week?"*, the RAG pipeline should inject this structured context alongside the prediction output:

```json
{
  "rag_context": {
    "model_prediction": {
      "predicted_roll7_cases": 45230,
      "direction": "increasing",
      "change_from_today_pct": "+3.2%",
      "interval": "[31800, 68500]"
    },
    "top_shap_drivers": [
      {
        "feature": "reproduction_rate",
        "value": 1.08,
        "shap_contribution": "POSITIVE (pushing prediction UP)",
        "human_readable": "Rt above 1.0 — each infected person is spreading to more than 1 other on average"
      },
      {
        "feature": "New_Confirmed_Lag7",
        "value": 44800,
        "shap_contribution": "POSITIVE (pushing prediction UP)",
        "human_readable": "Cases 7 days ago were rising — weekly cycle suggests continued growth"
      },
      {
        "feature": "stringency_index",
        "value": 42.6,
        "shap_contribution": "NEUTRAL",
        "human_readable": "Government restrictions are moderate — no strong suppression signal"
      }
    ],
    "uncertainty_note": "Wide prediction interval (36,700 case spread) — high uncertainty, proceed with caution"
  }
}
```

The LLM (GPT-4 / Gemini) then synthesises the above context with retrieved documents to generate a natural-language explanation.

### 6c. Suggested RAG Prompt Template

```
You are an epidemic forecasting assistant. You have been given:
1. A model prediction for {country} on {date}
2. The top features driving that prediction (SHAP values)
3. Retrieved policy and epidemiology documents

Model prediction: {predicted_roll7_cases} cases (7-day rolling average)
80% confidence range: {lower_q10} to {upper_q90}
Key drivers: {top_shap_drivers}

User question: {user_query}

Using the prediction context and the following retrieved documents, explain the forecast in plain language:
{retrieved_documents}

Keep your answer under 200 words. Highlight the most important driving factor. 
If uncertainty is high (interval width > 30,000 cases), mention this clearly.
```

---

## 7. Frontend Display Recommendations

Based on the model outputs, here's what each frontend component should show:

### Main Forecast Card
```
┌─────────────────────────────────────────────┐
│  United States — 15 Mar 2024               │
│                                             │
│  Predicted 7-day avg new cases              │
│  ┌──────────────┐                           │
│  │   45,231     │  ▲ +3.2% from today      │
│  └──────────────┘                           │
│                                             │
│  80% Confidence Range                       │
│  ████████████████████░░░░░░░░░░░            │
│  31,800          45,231          68,500     │
└─────────────────────────────────────────────┘
```

| UI Component | Data Field | Notes |
|-------------|-----------|-------|
| **Big number** | `predicted_roll7_cases` | Round to nearest integer |
| **Direction arrow** | Computed: prediction vs prev_Roll7 | Show ▲/▼ + % change |
| **Confidence bar** | `lower_q10`, `predicted_roll7_cases`, `upper_q90` | Slider/range visual |
| **Risk badge** | Computed from `reproduction_rate` | Rt < 0.9 = 🟢 Low, 0.9–1.1 = 🟡 Moderate, >1.1 = 🔴 High |
| **7-day trend chart** | Batch forecast response | Show line chart with shaded PI band |

### Risk Level Computation (Frontend Logic)

```javascript
function getRiskLevel(reproduction_rate, predicted_change_pct) {
  if (reproduction_rate > 1.2 || predicted_change_pct > 20) return "HIGH";
  if (reproduction_rate > 1.0 || predicted_change_pct > 5)  return "MODERATE";
  return "LOW";
}
```

---

## 8. Data Sources for Live Updates

The backend/data engineer needs to keep the database fresh. These APIs provide live data:

| Data | API | Update Frequency | Key Field |
|------|-----|-----------------|-----------|
| New confirmed cases | [JHU CSSE GitHub](https://github.com/CSSEGISandData/COVID-19) | Daily | `new_confirmed` |
| Deaths | Same as above | Daily | `new_deaths` |
| Stringency index | [OWID API](https://ourworldindata.org/covid-government-stringency-index) | Weekly | `stringency_index` |
| Reproduction rate | [OWID API](https://ourworldindata.org/covid-r-estimated) | Weekly | `reproduction_rate` |

> **If live data is unavailable:** Use the last known `stringency_index` (forward-fill), and default `reproduction_rate = 1.0` (neutral assumption). Make this explicit in the frontend UI.

---

## 9. Quick Reference Cheat Sheet

```
┌─────────────────────────────────────────────────┐
│              MODEL CONTRACT                     │
├─────────────────────────────────────────────────┤
│  INPUTS  (10 features)                          │
│  • 3 calendar features   (date-derived)         │
│  • 4 lag features        (history: 7 days min)  │
│  • 1 rolling feature     (history: 14 days min) │
│  • 2 policy features     (OWID API)             │
│                                                 │
│  OUTPUT  (4 numbers + metadata)                 │
│  • predicted_roll7_cases  → main display        │
│  • lower_q10              → confidence lower    │
│  • median_q50             → probabilistic mid   │
│  • upper_q90              → confidence upper    │
│                                                 │
│  HISTORY REQUIRED                               │
│  • Minimum 15 days of daily case data           │
│  • Per country, not global                      │
│                                                 │
│  PREDICTION UNIT                                │
│  • 7-day rolling average of daily new cases     │
│  • 1-day ahead (next day forecast)             │
│  • Multi-day: autoregressive rollout            │
│                                                 │
│  CONFIDENCE                                     │
│  • 80% PI coverage (validated: exactly 80.0%)   │
│  • Point forecast beats naive baseline by 17%   │
└─────────────────────────────────────────────────┘
```

---

*Model trained and validated by: [Your Name] — IIT BHU Hackathon 2024*
*Reach out with questions about the feature computation logic before building the database schema.*
