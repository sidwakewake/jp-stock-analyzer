"""
Buy Range Calculation Module
"""
from dataclasses import dataclass
from typing import Dict, Tuple, Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.ticker import JPTickerData
from config import BUY_RANGE_CONFIG


@dataclass
class BuyZone:
    """Buy zone definition"""
    label: str           # "Aggressive Zone" / "Standard Zone"
    price_low: float     # Zone lower bound
    price_high: float    # Zone upper bound
    allocation: str      # Suggested allocation "50%"
    is_current: bool     # Is current price in this zone


def calculate_anchor_price(data: JPTickerData) -> Tuple[float, str]:
    """
    Calculate anchor price for buy range
    
    Returns:
        (anchor_price, anchor_type)
    
    Anchor logic (priority):
    1. MA200 (if trend is healthy and price within reasonable range)
    2. MA50 (if MA200 is too far)
    3. Bollinger Band lower (if oversold)
    """
    price = data.current_price
    ma200 = data.ma_200
    ma50 = data.ma_50
    bb_lower = data.bb_lower
    
    # Check if MA200 is valid
    if ma200 and ma200 > 0:
        distance_ma200 = (price - ma200) / ma200
        
        # If price is within +15% of MA200, use MA200 (healthy uptrend)
        if 0 <= distance_ma200 < 0.15:
            return (ma200, "MA200")
        
        # If price is below MA200, still use MA200 (bottom fishing)
        if distance_ma200 < 0:
            return (ma200, "MA200")
    
    # Fallback to MA50 if MA200 is too far or unavailable
    if ma50 and ma50 > 0:
        distance_ma50 = (price - ma50) / ma50
        # Only use MA50 as anchor if price is within +10%
        if distance_ma50 < 0.10:
            return (ma50, "MA50")
        else:
            # Price is extended from MA50 too, mark as FAR
            return (ma50, "MA50_FAR")
    
    # Last resort: Bollinger Band lower
    if bb_lower and bb_lower > 0:
        return (bb_lower, "BB_Lower")
    
    # If nothing available, use current price
    return (price, "Current")


def calculate_buy_range(data: JPTickerData) -> Dict[str, Any]:
    """
    Calculate buy range zones
    
    Returns:
        {
            "anchor_price": float,
            "anchor_type": str,        # "MA200" / "MA50" / "BB_Lower"
            "aggressive": BuyZone,
            "standard": BuyZone,
            "current_zone": str,       # "above" / "aggressive" / "standard" / "below"
            "action": str,             # Buy suggestion text
            "distance_to_aggressive": float,  # Distance to aggressive zone upper (positive=need drop, negative=already in)
        }
    """
    price = data.current_price
    anchor_price, anchor_type = calculate_anchor_price(data)
    
    # Get configuration
    agg_config = BUY_RANGE_CONFIG["aggressive"]
    std_config = BUY_RANGE_CONFIG["standard"]
    
    # Calculate aggressive zone: [anchor * (1-3%), anchor * (1+5%)]
    agg_low = anchor_price * (1 + agg_config["from_anchor_pct"])
    agg_high = anchor_price * (1 + agg_config["to_anchor_pct"])
    
    # Calculate standard zone: [anchor * (1-10%), anchor * (1-3%)]
    std_low = anchor_price * (1 + std_config["from_anchor_pct"])
    std_high = anchor_price * (1 + std_config["to_anchor_pct"])
    
    # Determine current zone
    if price > agg_high:
        current_zone = "above"
        in_aggressive = False
        in_standard = False
    elif price >= agg_low:
        current_zone = "aggressive"
        in_aggressive = True
        in_standard = False
    elif price >= std_low:
        current_zone = "standard"
        in_aggressive = False
        in_standard = True
    else:
        current_zone = "below"
        in_aggressive = False
        in_standard = False
    
    # Create BuyZone objects
    aggressive_zone = BuyZone(
        label=agg_config["label"],
        price_low=agg_low,
        price_high=agg_high,
        allocation=agg_config["allocation"],
        is_current=in_aggressive
    )
    
    standard_zone = BuyZone(
        label=std_config["label"],
        price_low=std_low,
        price_high=std_high,
        allocation=std_config["allocation"],
        is_current=in_standard
    )
    
    # Calculate distance to aggressive zone upper
    distance_to_aggressive = (price - agg_high) / agg_high
    
    # Generate action text with anchor type consideration
    if anchor_type == "MA50_FAR":
        # Price is extended from all moving averages, give conservative advice
        if current_zone == "above":
            action = f"Price extended from MA50, wait for deeper pullback to ¥{std_low:,.0f}"
        elif current_zone == "aggressive":
            action = "In aggressive zone but price extended, consider 25% position only"
        elif current_zone == "standard":
            action = "In standard zone, can open 50% position"
        else:
            action = "Below standard zone, verify fundamentals"
    else:
        # Normal logic
        if current_zone == "above":
            action = f"Price too high, wait for pullback to ¥{agg_high:,.0f}"
        elif current_zone == "aggressive":
            action = "In aggressive zone, can open 50% position"
        elif current_zone == "standard":
            action = "In standard zone, can add to 100% position"
        else:
            action = "Below standard zone, verify fundamentals before heavy position"
    
    return {
        "anchor_price": anchor_price,
        "anchor_type": anchor_type,
        "aggressive": aggressive_zone,
        "standard": standard_zone,
        "current_zone": current_zone,
        "action": action,
        "distance_to_aggressive": distance_to_aggressive
    }
