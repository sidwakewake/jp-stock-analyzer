"""
Simplified Fundamental Analysis Module
"""
from typing import Dict, List, Any, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.ticker import JPTickerData
from config import DEFAULT_VALUATION


def calculate_pe_percentile(current_pe: float, pe_history: list = None) -> float:
    """
    Calculate current PE percentile in historical range
    
    Args:
        current_pe: Current PE
        pe_history: PE history list (optional, use default range if None)
    
    Returns:
        Percentile (0-100), 0 = cheapest, 100 = most expensive
    """
    if current_pe is None:
        return 50.0  # Return neutral if no PE data
    
    if pe_history and len(pe_history) > 0:
        # Calculate actual percentile from history
        count_below = sum(1 for pe in pe_history if pe < current_pe)
        percentile = (count_below / len(pe_history)) * 100
    else:
        # Use default range
        pe_floor = DEFAULT_VALUATION["pe_floor"]
        pe_ceiling = DEFAULT_VALUATION["pe_ceiling"]
        
        if pe_ceiling == pe_floor:
            return 50.0
        
        percentile = (current_pe - pe_floor) / (pe_ceiling - pe_floor) * 100
    
    # Clamp to 0-100
    return max(0, min(100, percentile))


def calculate_valuation_score(data: JPTickerData) -> Dict[str, Any]:
    """
    Calculate simplified valuation score
    
    Returns:
        {
            "score": float,          # 0-100
            "pe_status": str,        # "Cheap" / "Fair" / "Expensive" / "N/A"
            "pe_vs_avg": float,      # Premium/discount vs default average
            "pe_percentile": float,  # PE historical percentile
            "dividend_status": str,  # "Attractive" / "Normal" / "Low" / "N/A"
            "reasons": List[str]
        }
    """
    reasons = []
    
    # === PE Score (70 points) ===
    pe = data.pe_ttm
    
    if pe is None or pe <= 0:
        pe_score = 35  # Neutral
        pe_status = "N/A"
        pe_percentile = 50
        pe_vs_avg = 0
        reasons.append("PE data unavailable")
    else:
        pe_percentile = calculate_pe_percentile(pe)
        pe_vs_avg = (pe - DEFAULT_VALUATION["pe_5y_avg"]) / DEFAULT_VALUATION["pe_5y_avg"]
        
        if pe_percentile < 20:
            pe_score = 70
            pe_status = "Cheap"
            reasons.append(f"PE {pe:.1f} very cheap (percentile: {pe_percentile:.0f}%)")
        elif pe_percentile < 40:
            pe_score = 55
            pe_status = "Cheap"
            reasons.append(f"PE {pe:.1f} cheap (percentile: {pe_percentile:.0f}%)")
        elif pe_percentile < 60:
            pe_score = 40
            pe_status = "Fair"
            reasons.append(f"PE {pe:.1f} fair value (percentile: {pe_percentile:.0f}%)")
        elif pe_percentile < 80:
            pe_score = 25
            pe_status = "Expensive"
            reasons.append(f"PE {pe:.1f} expensive (percentile: {pe_percentile:.0f}%)")
        else:
            pe_score = 10
            pe_status = "Expensive"
            reasons.append(f"PE {pe:.1f} very expensive (percentile: {pe_percentile:.0f}%)")
    
    # === Dividend Yield Score (30 points) ===
    div_yield = data.dividend_yield
    
    if div_yield is None:
        div_score = 15  # Neutral
        dividend_status = "N/A"
        reasons.append("Dividend data unavailable")
    else:
        # Convert to percentage if needed
        div_pct = div_yield * 100 if div_yield < 1 else div_yield
        
        if div_pct > 3:
            div_score = 30
            dividend_status = "Attractive"
            reasons.append(f"Dividend yield {div_pct:.1f}% attractive")
        elif div_pct > 2:
            div_score = 22
            dividend_status = "Normal"
            reasons.append(f"Dividend yield {div_pct:.1f}% normal")
        elif div_pct > 1:
            div_score = 15
            dividend_status = "Low"
            reasons.append(f"Dividend yield {div_pct:.1f}% low")
        else:
            div_score = 8
            dividend_status = "Low"
            reasons.append(f"Dividend yield {div_pct:.1f}% very low")
    
    # === Total Score ===
    total_score = pe_score + div_score
    
    return {
        "score": total_score,
        "pe_status": pe_status,
        "pe_vs_avg": pe_vs_avg,
        "pe_percentile": pe_percentile,
        "dividend_status": dividend_status,
        "reasons": reasons,
        "components": {
            "pe_score": pe_score,
            "div_score": div_score
        }
    }
