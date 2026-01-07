"""
JP Stock Analyzer Configuration
All stock symbols are passed dynamically via command line
"""
from typing import Dict, Any

# === Technical Indicator Thresholds ===
TECHNICAL_THRESHOLDS = {
    # RSI
    "rsi_oversold": 30,            # RSI < 30 oversold
    "rsi_overbought": 70,          # RSI > 70 overbought
    "rsi_neutral_low": 40,         # RSI 40-60 neutral zone
    "rsi_neutral_high": 60,
    
    # Bollinger Band Position
    "bb_oversold": 0.20,           # Position < 20% oversold
    "bb_overbought": 0.80,         # Position > 80% overbought
    
    # MA Distance
    "ma200_near_pct": 0.03,        # Within ±3% of MA200 is "near"
    "ma50_near_pct": 0.02,         # Within ±2% of MA50 is "near"
}

# === Buy Range Configuration v2.0 (from KINRO) ===
# Per-company-type configuration:
# - drawdown_from_anchor: Drawdown percentages for each zone
# - allocation: Suggested position allocation per zone
# - anchor_weights: Weights for anchor price calculation
# - pullback_pct: Pullback percentage from 90-day high

BUY_RANGE_CONFIG = {
    # Type A: Stable Profitable (e.g., 7011.T Mitsubishi Heavy Industries)
    "A": {
        "drawdown_from_anchor": {
            "aggressive": 0.03,    # Anchor -3%
            "standard": 0.10,      # Anchor -10%
            "conservative": 0.18,  # Anchor -18%
        },
        "allocation": {
            "aggressive": "25%",
            "standard": "40%",
            "conservative": "35%",
        },
        "anchor_weights": {
            "ma50": 0.20,
            "ma120": 0.30,
            "ma200": 0.30,
            "pullback": 0.20,
        },
        "pullback_pct": 0.90,  # 90% of 90-day high
    },
    
    # Type B: Growth (e.g., 8316.T Sumitomo Mitsui)
    "B": {
        "drawdown_from_anchor": {
            "aggressive": 0.05,
            "standard": 0.15,
            "conservative": 0.25,
        },
        "allocation": {
            "aggressive": "25%",
            "standard": "40%",
            "conservative": "35%",
        },
        "anchor_weights": {
            "ma50": 0.25,
            "ma120": 0.25,
            "ma200": 0.20,
            "pullback": 0.30,
        },
        "pullback_pct": 0.80,
    },
    
    # Type C: High Growth (unprofitable but high revenue growth)
    "C": {
        "drawdown_from_anchor": {
            "aggressive": 0.08,
            "standard": 0.20,
            "conservative": 0.35,
        },
        "allocation": {
            "aggressive": "25%",
            "standard": "40%",
            "conservative": "35%",
        },
        "anchor_weights": {
            "ma50": 0.30,
            "ma120": 0.25,
            "ma200": 0.15,
            "pullback": 0.30,
        },
        "pullback_pct": 0.75,
    },
    
    # Type D: Cyclical (energy, materials, industrials)
    "D": {
        "drawdown_from_anchor": {
            "aggressive": 0.05,
            "standard": 0.12,
            "conservative": 0.22,
        },
        "allocation": {
            "aggressive": "30%",
            "standard": "35%",
            "conservative": "35%",
        },
        "anchor_weights": {
            "ma50": 0.20,
            "ma120": 0.25,
            "ma200": 0.35,
            "pullback": 0.20,
        },
        "pullback_pct": 0.85,
    },
    
    # DEFAULT: Used when company type is unknown
    "DEFAULT": {
        "drawdown_from_anchor": {
            "aggressive": 0.05,
            "standard": 0.12,
            "conservative": 0.20,
        },
        "allocation": {
            "aggressive": "25%",
            "standard": "40%",
            "conservative": "35%",
        },
        "anchor_weights": {
            "ma50": 0.25,
            "ma120": 0.25,
            "ma200": 0.25,
            "pullback": 0.25,
        },
        "pullback_pct": 0.80,
    },
}

# Volatility adjustment configuration
BUY_RANGE_VOLATILITY_CONFIG = {
    "baseline": 0.30,    # 30% annualized volatility as baseline
    "min_factor": 0.75,  # Low volatility: narrow zones
    "max_factor": 1.50,  # High volatility: widen zones
}

# === Scoring Weights ===
SCORE_WEIGHTS = {
    "technical": 0.60,             # Technical weight
    "valuation": 0.40,             # Valuation weight
}

# === Output Configuration ===
OUTPUT_CONFIG = {
    "currency_symbol": "¥",
    "decimal_places": 0,           # JPY has no decimals
    "percentage_decimals": 1,
}

# === Default Valuation Parameters (when API data unavailable) ===
DEFAULT_VALUATION = {
    "pe_floor": 8,                 # Default PE floor
    "pe_ceiling": 30,              # Default PE ceiling
    "pe_5y_avg": 15,               # Default 5-year average PE
}
