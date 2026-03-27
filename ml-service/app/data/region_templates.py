"""
Region-aware template data for ML service stubs.

Each region has plausible baseline epidemiological parameters.
These are NOT random — they represent realistic relative magnitudes
so the system produces coherent outputs across endpoints.

risk_score = w1*growth + w2*mobility + w3*(1-vaccination) + w4*hospital_pressure
"""

from datetime import date

REGION_DATA = {
    "ITA": {
        "name": "Italy",
        "base_cases": 15000,
        "growth_rate": 0.08,
        "mobility_index": 0.23,
        "vaccination_rate": 0.62,
        "hospital_pressure": 0.35,
        "stringency_index": 45.0,
    },
    "IND": {
        "name": "India",
        "base_cases": 85000,
        "growth_rate": 0.05,
        "mobility_index": 0.18,
        "vaccination_rate": 0.48,
        "hospital_pressure": 0.42,
        "stringency_index": 55.0,
    },
    "USA": {
        "name": "United States",
        "base_cases": 45000,
        "growth_rate": 0.06,
        "mobility_index": 0.30,
        "vaccination_rate": 0.72,
        "hospital_pressure": 0.20,
        "stringency_index": 30.0,
    },
    "BRA": {
        "name": "Brazil",
        "base_cases": 38000,
        "growth_rate": 0.09,
        "mobility_index": 0.28,
        "vaccination_rate": 0.55,
        "hospital_pressure": 0.45,
        "stringency_index": 40.0,
    },
    "GBR": {
        "name": "United Kingdom",
        "base_cases": 12000,
        "growth_rate": 0.04,
        "mobility_index": 0.15,
        "vaccination_rate": 0.78,
        "hospital_pressure": 0.18,
        "stringency_index": 35.0,
    },
    "DEU": {
        "name": "Germany",
        "base_cases": 18000,
        "growth_rate": 0.05,
        "mobility_index": 0.20,
        "vaccination_rate": 0.74,
        "hospital_pressure": 0.22,
        "stringency_index": 38.0,
    },
    "FRA": {
        "name": "France",
        "base_cases": 20000,
        "growth_rate": 0.07,
        "mobility_index": 0.25,
        "vaccination_rate": 0.68,
        "hospital_pressure": 0.28,
        "stringency_index": 42.0,
    },
    "JPN": {
        "name": "Japan",
        "base_cases": 22000,
        "growth_rate": 0.03,
        "mobility_index": 0.12,
        "vaccination_rate": 0.82,
        "hospital_pressure": 0.15,
        "stringency_index": 50.0,
    },
    "ZAF": {
        "name": "South Africa",
        "base_cases": 9000,
        "growth_rate": 0.11,
        "mobility_index": 0.32,
        "vaccination_rate": 0.35,
        "hospital_pressure": 0.50,
        "stringency_index": 48.0,
    },
    "AUS": {
        "name": "Australia",
        "base_cases": 8000,
        "growth_rate": 0.02,
        "mobility_index": 0.10,
        "vaccination_rate": 0.85,
        "hospital_pressure": 0.10,
        "stringency_index": 25.0,
    },
}

# Risk weights (must sum to 1.0)
RISK_WEIGHTS = {
    "predicted_growth_rate": 0.35,
    "mobility_index": 0.25,
    "vaccination_gap": 0.22,
    "hospital_pressure": 0.18,
}


def get_region(region_id: str) -> dict:
    """Get region data, returns None if not found."""
    return REGION_DATA.get(region_id.upper())


def get_all_region_ids() -> list:
    return list(REGION_DATA.keys())


def compute_risk_score(growth_rate: float, mobility: float,
                       vaccination_rate: float, hospital_pressure: float) -> float:
    """
    Unified risk formula:
    risk = w1*growth + w2*mobility + w3*(1-vaccination) + w4*hospital_pressure

    All inputs should be normalized [0-1] range for meaningful scores.
    growth_rate is clamped to [0, 0.3] and scaled.
    """
    w = RISK_WEIGHTS
    growth_normalized = min(growth_rate / 0.15, 1.0)  # 15%+ growth = max risk contribution
    vaccination_gap = 1.0 - vaccination_rate

    score = (
        w["predicted_growth_rate"] * growth_normalized +
        w["mobility_index"] * mobility +
        w["vaccination_gap"] * vaccination_gap +
        w["hospital_pressure"] * hospital_pressure
    )
    return round(min(max(score, 0.0), 1.0), 3)


def risk_level_from_score(score: float) -> str:
    if score > 0.7:
        return "High"
    elif score > 0.4:
        return "Medium"
    else:
        return "Low"


def get_as_of_date() -> str:
    return date.today().isoformat()
