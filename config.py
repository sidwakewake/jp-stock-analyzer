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

# === Buy Range Configuration ===
BUY_RANGE_CONFIG = {
    # Aggressive zone: near anchor
    "aggressive": {
        "from_anchor_pct": -0.03,  # Anchor -3%
        "to_anchor_pct": 0.05,     # Anchor +5%
        "allocation": "50%",
        "label": "Aggressive Zone"
    },
    # Standard zone: below anchor
    "standard": {
        "from_anchor_pct": -0.10,  # Anchor -10%
        "to_anchor_pct": -0.03,    # Anchor -3%
        "allocation": "50%",
        "label": "Standard Zone"
    },
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
