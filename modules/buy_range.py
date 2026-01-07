"""
Buy Range Calculator v2 for JP Stock Analyzer
Based on KINRO backend logic

Strategy: Technical-anchored using weighted average of MA50, MA120, MA200, and 90-day high pullback.
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BUY_RANGE_CONFIG, BUY_RANGE_VOLATILITY_CONFIG
from models.ticker import JPTickerData


@dataclass
class BuyRangeTier:
    """Single buy range tier"""
    price_low: float
    price_high: float
    suggested_allocation: str
    tier_label: str
    is_current: bool = False


@dataclass
class BuyRangeResult:
    """Complete buy range calculation result"""
    symbol: str
    current_price: float
    
    # Three-tier zones
    aggressive: BuyRangeTier
    standard: BuyRangeTier
    conservative: BuyRangeTier
    
    # Current position
    current_zone: str  # "above_range" | "aggressive" | "standard" | "conservative" | "below_range"
    
    # Anchor information
    anchor_price: float
    anchor_type: str  # "weighted_average"
    primary_support: float
    
    # Action guidance
    action_text: str
    
    # Calculation notes (for debugging)
    calculation_notes: List[str]


def get_volatility_factor(volatility: float) -> float:
    """
    Calculate volatility adjustment factor.
    Higher volatility -> wider zones; Lower volatility -> tighter zones.
    """
    if volatility <= 0:
        return 1.0
    
    cfg = BUY_RANGE_VOLATILITY_CONFIG
    factor = volatility / cfg["baseline"]
    return max(cfg["min_factor"], min(cfg["max_factor"], factor))


def calculate_anchor_price(data: JPTickerData, company_type: str) -> Tuple[float, List[str]]:
    """
    Calculate weighted average anchor price (KINRO core logic).
    
    Formula: anchor = MA50×w1 + MA120×w2 + MA200×w3 + (90d_high × pullback_pct)×w4
    
    Returns:
        (anchor_price, calculation_notes)
    """
    config = BUY_RANGE_CONFIG.get(company_type, BUY_RANGE_CONFIG["DEFAULT"])
    weights = config["anchor_weights"]
    pullback_pct = config["pullback_pct"]
    
    current_price = data.current_price
    notes: List[str] = []
    
    # Get MA values, fallback to estimated values if missing
    ma_50 = data.ma_50 if data.ma_50 > 0 else current_price * 0.95
    ma_120 = data.ma_120 if data.ma_120 > 0 else current_price * 0.90
    ma_200 = data.ma_200 if data.ma_200 > 0 else current_price * 0.85
    high_90d = data.high_90d if data.high_90d > 0 else current_price
    
    # Calculate pullback anchor
    pullback_anchor = high_90d * pullback_pct
    
    # Weighted average
    anchor = (
        ma_50 * weights["ma50"] +
        ma_120 * weights["ma120"] +
        ma_200 * weights["ma200"] +
        pullback_anchor * weights["pullback"]
    )
    
    notes.append(f"Type {company_type} anchor calculation:")
    notes.append(f"  MA50=¥{ma_50:,.0f} × {weights['ma50']:.0%}")
    notes.append(f"  MA120=¥{ma_120:,.0f} × {weights['ma120']:.0%}")
    notes.append(f"  MA200=¥{ma_200:,.0f} × {weights['ma200']:.0%}")
    notes.append(f"  Pullback(90d_high×{pullback_pct:.0%})=¥{pullback_anchor:,.0f} × {weights['pullback']:.0%}")
    notes.append(f"  → Anchor=¥{anchor:,.0f}")
    
    return anchor, notes


def calculate_buy_range(data: JPTickerData, company_type: str = "DEFAULT") -> Dict[str, Any]:
    """
    Calculate three-tier buy range.
    
    Args:
        data: Stock data
        company_type: Company type (A/B/C/D/DEFAULT)
    
    Returns:
        Dictionary with all zone information (compatible with v1 interface)
    """
    config = BUY_RANGE_CONFIG.get(company_type, BUY_RANGE_CONFIG["DEFAULT"])
    current_price = data.current_price
    notes: List[str] = []
    
    # Step 1: Calculate anchor
    anchor_price, anchor_notes = calculate_anchor_price(data, company_type)
    notes.extend(anchor_notes)
    
    # Step 2: Get drawdown configuration
    drawdowns = config["drawdown_from_anchor"]
    allocations = config["allocation"]
    
    # Step 3: Volatility adjustment
    vol_factor = get_volatility_factor(data.volatility) if data.volatility > 0 else 1.0
    if vol_factor != 1.0:
        notes.append(f"Volatility={data.volatility*100:.0f}% → factor={vol_factor:.2f}")
    
    adjusted_drawdowns = {k: v * vol_factor for k, v in drawdowns.items()}
    
    # Step 4: Calculate three-tier zones
    # Aggressive: anchor +3% ~ anchor - aggressive_drawdown
    aggressive_high = anchor_price * 1.03
    aggressive_low = anchor_price * (1 - adjusted_drawdowns["aggressive"])
    
    # Standard: aggressive_low ~ anchor - standard_drawdown
    standard_high = aggressive_low
    standard_low = anchor_price * (1 - adjusted_drawdowns["standard"])
    
    # Conservative: standard_low ~ anchor - conservative_drawdown
    conservative_high = standard_low
    conservative_low = anchor_price * (1 - adjusted_drawdowns["conservative"])
    
    notes.append(f"Zones (vol_factor={vol_factor:.2f}):")
    notes.append(f"  Aggressive: ¥{aggressive_low:,.0f} - ¥{aggressive_high:,.0f}")
    notes.append(f"  Standard:   ¥{standard_low:,.0f} - ¥{standard_high:,.0f}")
    notes.append(f"  Conservative: ¥{conservative_low:,.0f} - ¥{conservative_high:,.0f}")
    
    # Step 5: Determine current zone
    if current_price > aggressive_high:
        current_zone = "above_range"
        in_agg, in_std, in_con = False, False, False
    elif current_price >= aggressive_low:
        current_zone = "aggressive"
        in_agg, in_std, in_con = True, False, False
    elif current_price >= standard_low:
        current_zone = "standard"
        in_agg, in_std, in_con = False, True, False
    elif current_price >= conservative_low:
        current_zone = "conservative"
        in_agg, in_std, in_con = False, False, True
    else:
        current_zone = "below_range"
        in_agg, in_std, in_con = False, False, False
    
    # Step 6: Create tier objects
    aggressive = BuyRangeTier(
        price_low=aggressive_low,
        price_high=aggressive_high,
        suggested_allocation=allocations["aggressive"],
        tier_label="aggressive",
        is_current=in_agg,
    )
    standard = BuyRangeTier(
        price_low=standard_low,
        price_high=standard_high,
        suggested_allocation=allocations["standard"],
        tier_label="standard",
        is_current=in_std,
    )
    conservative = BuyRangeTier(
        price_low=conservative_low,
        price_high=conservative_high,
        suggested_allocation=allocations["conservative"],
        tier_label="conservative",
        is_current=in_con,
    )
    
    # Step 7: Generate action text
    action_text = _generate_action_text(current_price, current_zone, aggressive, standard, conservative)
    
    # Step 8: Determine primary support
    primary_support = data.ma_200 if data.ma_200 > 0 else data.ma_120
    
    # Calculate distance to aggressive zone
    distance_to_aggressive = (current_price - aggressive_high) / aggressive_high
    
    # Return compatible dictionary format
    return {
        "anchor_price": anchor_price,
        "anchor_type": "weighted_average",
        "aggressive": aggressive,
        "standard": standard,
        "conservative": conservative,
        "current_zone": current_zone,
        "action": action_text,
        "distance_to_aggressive": distance_to_aggressive,
        "primary_support": primary_support,
        "calculation_notes": notes,
        "company_type": company_type,
    }


def _generate_action_text(
    price: float,
    zone: str,
    aggressive: BuyRangeTier,
    standard: BuyRangeTier,
    conservative: BuyRangeTier,
) -> str:
    """Generate action guidance text."""
    if zone == "above_range":
        gap_pct = (price - aggressive.price_high) / aggressive.price_high * 100
        return f"Above range (+{gap_pct:.1f}%). Wait for ¥{aggressive.price_high:,.0f} or lower."
    
    elif zone == "aggressive":
        return f"Aggressive zone. Consider {aggressive.suggested_allocation} position."
    
    elif zone == "standard":
        agg_pct = _parse_pct(aggressive.suggested_allocation)
        std_pct = _parse_pct(standard.suggested_allocation)
        cumulative = agg_pct + std_pct
        return f"Standard zone. Consider {cumulative:.0f}% cumulative position."
    
    elif zone == "conservative":
        return f"Conservative zone - excellent entry. Consider full position."
    
    else:  # below_range
        return f"Below range (¥{conservative.price_low:,.0f}). Verify thesis before buying."


def _parse_pct(s: str) -> float:
    """Parse percentage string '25%' -> 25.0"""
    match = re.search(r'(\d+)', s)
    return float(match.group(1)) if match else 0.0


def get_cumulative_allocation(zone: str, buy_range: Dict[str, Any]) -> float:
    """
    Get cumulative position allocation for current zone.
    
    Logic: Buy more as price drops
    - aggressive: 25%
    - standard: 25%+40%=65%
    - conservative: 25%+40%+35%=100%
    """
    if zone == "above_range":
        return 0.0
    
    agg = buy_range["aggressive"]
    std = buy_range["standard"]
    con = buy_range["conservative"]
    
    aggr_pct = _parse_pct(agg.suggested_allocation) / 100
    std_pct = _parse_pct(std.suggested_allocation) / 100
    cons_pct = _parse_pct(con.suggested_allocation) / 100
    
    if zone == "aggressive":
        return aggr_pct
    elif zone == "standard":
        return aggr_pct + std_pct
    elif zone == "conservative":
        return aggr_pct + std_pct + cons_pct
    elif zone == "below_range":
        return 1.0
    
    return 0.0
