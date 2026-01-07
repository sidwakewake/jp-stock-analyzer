"""
Technical Analysis Module
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.ticker import JPTickerData
from config import TECHNICAL_THRESHOLDS


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """
    Calculate RSI(14)
    
    Args:
        prices: Close price series (at least period+1 data points)
        period: RSI period, default 14
    
    Returns:
        RSI value (0-100)
    """
    if len(prices) < period + 1:
        return 50.0  # Return neutral if insufficient data
    
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # Avoid division by zero
    avg_loss_val = avg_loss.iloc[-1]
    if avg_loss_val == 0:
        return 100.0 if avg_gain.iloc[-1] > 0 else 50.0
    
    rs = avg_gain.iloc[-1] / avg_loss_val
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_moving_averages(prices: pd.Series) -> Dict[str, float]:
    """
    Calculate multiple moving averages
    
    Args:
        prices: Close price series
    
    Returns:
        {
            "ma_5": float,
            "ma_20": float,
            "ma_50": float,
            "ma_200": float
        }
    """
    result = {}
    
    for period, key in [(5, "ma_5"), (20, "ma_20"), (50, "ma_50"), (200, "ma_200")]:
        if len(prices) >= period:
            result[key] = prices.rolling(window=period).mean().iloc[-1]
        else:
            result[key] = None
    
    return result


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, num_std: float = 2.0) -> Dict[str, float]:
    """
    Calculate Bollinger Bands
    
    Args:
        prices: Close price series
        period: MA period, default 20
        num_std: Standard deviation multiplier, default 2
    
    Returns:
        {
            "upper": float,      # Upper band
            "middle": float,     # Middle band (MA20)
            "lower": float,      # Lower band
            "width": float,      # Band width = (upper-lower)/middle
            "position": float    # Current price position = (price-lower)/(upper-lower)
        }
    """
    if len(prices) < period:
        current_price = prices.iloc[-1]
        return {
            "upper": current_price,
            "middle": current_price,
            "lower": current_price,
            "width": 0,
            "position": 0.5
        }
    
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    
    upper = middle + num_std * std
    lower = middle - num_std * std
    
    current_price = prices.iloc[-1]
    upper_val = upper.iloc[-1]
    lower_val = lower.iloc[-1]
    middle_val = middle.iloc[-1]
    
    # Calculate position (0=lower, 1=upper)
    if upper_val != lower_val:
        position = (current_price - lower_val) / (upper_val - lower_val)
    else:
        position = 0.5
    
    # Calculate width
    if middle_val != 0:
        width = (upper_val - lower_val) / middle_val
    else:
        width = 0
    
    return {
        "upper": upper_val,
        "middle": middle_val,
        "lower": lower_val,
        "width": width,
        "position": position
    }


def determine_ma_alignment(data: JPTickerData) -> Dict[str, Any]:
    """
    Determine moving average alignment pattern
    
    Returns:
        {
            "pattern": str,      # "Perfect Bullish" / "Bullish" / "Bearish" / "Mixed"
            "trend": str,        # "UP" / "DOWN" / "SIDEWAYS"
            "price_vs_ma200": float,  # Price distance from MA200 percentage
            "price_vs_ma50": float
        }
    """
    price = data.current_price
    ma5 = data.ma_5
    ma20 = data.ma_20
    ma50 = data.ma_50
    ma200 = data.ma_200
    
    # Calculate distances
    price_vs_ma200 = (price - ma200) / ma200 if ma200 else 0
    price_vs_ma50 = (price - ma50) / ma50 if ma50 else 0
    
    # Determine pattern
    if price > ma5 > ma20 > ma50 > ma200:
        pattern = "Perfect Bullish"
        trend = "UP"
    elif price > ma50 > ma200:
        pattern = "Bullish"
        trend = "UP"
    elif price < ma50 < ma200:
        pattern = "Bearish"
        trend = "DOWN"
    else:
        pattern = "Mixed"
        trend = "SIDEWAYS"
    
    return {
        "pattern": pattern,
        "trend": trend,
        "price_vs_ma200": price_vs_ma200,
        "price_vs_ma50": price_vs_ma50
    }


def determine_support_status(data: JPTickerData) -> Dict[str, Any]:
    """
    Determine support level status
    
    Returns:
        {
            "status": str,           # "Above All" / "At MA50" / "At MA200" / "Below All"
            "nearest_support": float, # Nearest support price
            "nearest_support_name": str,  # "MA50" / "MA200" / "52W Low"
            "distance_pct": float    # Distance to nearest support percentage
        }
    """
    price = data.current_price
    ma50 = data.ma_50
    ma200 = data.ma_200
    low_52w = data.low_52w
    
    near_threshold = TECHNICAL_THRESHOLDS["ma200_near_pct"]  # 3%
    
    # Check each support level
    supports = []
    
    if ma50 and ma50 > 0:
        dist_ma50 = (price - ma50) / ma50
        supports.append(("MA50", ma50, dist_ma50))
    
    if ma200 and ma200 > 0:
        dist_ma200 = (price - ma200) / ma200
        supports.append(("MA200", ma200, dist_ma200))
    
    if low_52w and low_52w > 0:
        dist_52w = (price - low_52w) / low_52w
        supports.append(("52W Low", low_52w, dist_52w))
    
    if not supports:
        return {
            "status": "Unknown",
            "nearest_support": price,
            "nearest_support_name": "N/A",
            "distance_pct": 0
        }
    
    # Find nearest support below current price
    supports_below = [(n, p, d) for n, p, d in supports if d >= 0]
    
    if not supports_below:
        # Price is below all supports
        return {
            "status": "Below All",
            "nearest_support": supports[0][1],
            "nearest_support_name": supports[0][0],
            "distance_pct": supports[0][2]
        }
    
    # Sort by distance (closest first)
    supports_below.sort(key=lambda x: x[2])
    nearest = supports_below[0]
    
    # Determine status
    if nearest[2] < near_threshold:
        status = f"At {nearest[0]}"
    elif all(d > 0 for _, _, d in supports):
        status = "Above All"
    else:
        status = f"Near {nearest[0]}"
    
    return {
        "status": status,
        "nearest_support": nearest[1],
        "nearest_support_name": nearest[0],
        "distance_pct": nearest[2]
    }


def calculate_technical_score(data: JPTickerData) -> Dict[str, Any]:
    """
    Calculate comprehensive technical score
    
    Returns:
        {
            "score": float,          # 0-100
            "signal": str,           # "STRONG_BUY" / "BUY" / "HOLD" / "WAIT" / "SELL"
            "reasons": List[str],    # Score reasons
            "components": {
                "rsi_score": float,      # RSI score (0-25)
                "ma_score": float,       # MA score (0-25)
                "bb_score": float,       # Bollinger Band score (0-25)
                "support_score": float   # Support score (0-25)
            }
        }
    """
    reasons = []
    
    # === RSI Score (25 points) ===
    rsi = data.rsi_14
    if rsi < 30:
        rsi_score = 25
        reasons.append(f"RSI({rsi:.0f}) oversold - buy opportunity")
    elif rsi < 40:
        rsi_score = 20
        reasons.append(f"RSI({rsi:.0f}) low range")
    elif rsi < 60:
        rsi_score = 15
        reasons.append(f"RSI({rsi:.0f}) neutral")
    elif rsi < 70:
        rsi_score = 10
        reasons.append(f"RSI({rsi:.0f}) high range")
    else:
        rsi_score = 5
        reasons.append(f"RSI({rsi:.0f}) overbought - caution")
    
    # === MA Score (25 points) ===
    ma_info = determine_ma_alignment(data)
    pattern = ma_info["pattern"]
    
    if pattern == "Perfect Bullish":
        ma_score = 25
        reasons.append("Perfect bullish MA alignment")
    elif pattern == "Bullish":
        ma_score = 20
        reasons.append("Bullish trend (Price > MA50 > MA200)")
    elif pattern == "Mixed" and ma_info["price_vs_ma200"] > 0:
        ma_score = 15
        reasons.append("Mixed pattern but above MA200")
    elif pattern == "Mixed" and abs(ma_info["price_vs_ma200"]) < 0.05:
        ma_score = 10
        reasons.append("Near MA200 support")
    else:
        ma_score = 5
        reasons.append("Bearish MA pattern")
    
    # === Bollinger Band Score (25 points) ===
    bb_pos = data.bb_position
    if bb_pos < 0.2:
        bb_score = 25
        reasons.append(f"Near lower band ({bb_pos*100:.0f}%) - buy zone")
    elif bb_pos < 0.4:
        bb_score = 20
        reasons.append(f"Lower band region ({bb_pos*100:.0f}%)")
    elif bb_pos < 0.6:
        bb_score = 15
        reasons.append(f"Middle band ({bb_pos*100:.0f}%)")
    elif bb_pos < 0.8:
        bb_score = 10
        reasons.append(f"Upper band region ({bb_pos*100:.0f}%)")
    else:
        bb_score = 5
        reasons.append(f"Near upper band ({bb_pos*100:.0f}%) - overbought")
    
    # === Support Score (25 points) ===
    support_info = determine_support_status(data)
    status = support_info["status"]
    distance = support_info["distance_pct"]
    
    if "At MA50" in status or "At MA200" in status:
        support_score = 25
        reasons.append(f"At key support level: {support_info['nearest_support_name']}")
    elif distance < 0.05:
        support_score = 20
        reasons.append(f"Near support ({support_info['nearest_support_name']} {distance*100:.1f}% away)")
    elif status == "Above All" and distance < 0.10:
        support_score = 15
        reasons.append("Above supports, within 10% range")
    elif status == "Above All":
        support_score = 10
        reasons.append("Far from supports")
    else:
        support_score = 5
        reasons.append("Below all supports - verify fundamentals")
    
    # === Total Score ===
    total_score = rsi_score + ma_score + bb_score + support_score
    
    # === Determine Signal ===
    if total_score >= 85:
        signal = "STRONG_BUY"
    elif total_score >= 70:
        signal = "BUY"
    elif total_score >= 50:
        signal = "HOLD"
    elif total_score >= 35:
        signal = "WAIT"
    else:
        signal = "SELL"
    
    return {
        "score": total_score,
        "signal": signal,
        "reasons": reasons,
        "components": {
            "rsi_score": rsi_score,
            "ma_score": ma_score,
            "bb_score": bb_score,
            "support_score": support_score
        },
        "ma_info": ma_info,
        "support_info": support_info
    }
