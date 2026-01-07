"""
Terminal Output Formatter Module
"""
from typing import Dict, List, Any
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.ticker import JPTickerData
from config import OUTPUT_CONFIG


def format_header() -> str:
    """
    Generate header line
    
    Output:
    ================================================================================
                         JP STOCK ANALYZER - 2026-01-08
    ================================================================================
    """
    today = datetime.now().strftime("%Y-%m-%d")
    width = 80
    title = f"JP STOCK ANALYZER - {today}"
    
    lines = [
        "=" * width,
        title.center(width),
        "=" * width,
    ]
    
    return "\n".join(lines)


def format_score_bar(score: float, width: int = 20) -> str:
    """
    Generate score progress bar
    
    Args:
        score: Score 0-100
        width: Bar width (character count)
    
    Returns:
        "████████████░░░░░░░░" format string
    """
    filled = int(score / 100 * width)
    filled = max(0, min(width, filled))  # Clamp
    return "█" * filled + "░" * (width - filled)


def format_currency(value: float) -> str:
    """
    Format Japanese Yen amount
    
    Examples:
        1234.5 -> "¥1,234"
        1234567 -> "¥1,234,567"
    """
    if value is None:
        return "N/A"
    return f"¥{value:,.0f}"


def format_percentage(value: float, with_sign: bool = True) -> str:
    """
    Format percentage
    
    Examples:
        0.0523 -> "+5.2%"
        -0.0312 -> "-3.1%"
    """
    if value is None:
        return "N/A"
    
    pct = value * 100
    decimals = OUTPUT_CONFIG["percentage_decimals"]
    
    if with_sign:
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.{decimals}f}%"
    else:
        return f"{pct:.{decimals}f}%"


def format_stock_analysis(data: JPTickerData, technical: Dict, valuation: Dict, buy_range: Dict, warning: str = None) -> str:
    """
    Format complete analysis output for a single stock
    """
    lines = []
    
    # === Header ===
    lines.append(f"\n[{data.symbol}] {data.name}")
    lines.append("─" * 80)
    
    # === Price Line ===
    change_str = format_percentage(data.change_pct)
    high_dist = (data.current_price - data.high_52w) / data.high_52w if data.high_52w else 0
    
    lines.append(f" Price: {format_currency(data.current_price)} ({change_str})  |  "
                 f"52W: {format_currency(data.low_52w)} - {format_currency(data.high_52w)}  |  "
                 f"From High: {format_percentage(high_dist)}")
    lines.append("")
    
    # === Technical Analysis ===
    tech_score = technical["score"]
    tech_signal = technical["signal"]
    tech_bar = format_score_bar(tech_score)
    
    lines.append(f" Technical [{tech_score:.0f}/100] {tech_bar} {tech_signal}")
    lines.append(f" ├─ RSI(14): {data.rsi_14:.0f} ({_get_rsi_status(data.rsi_14)})")
    
    ma_info = technical.get("ma_info", {})
    ma_pattern = ma_info.get("pattern", "N/A")
    lines.append(f" ├─ MA: {ma_pattern}")
    
    bb_pct = data.bb_position * 100
    lines.append(f" ├─ Bollinger Band: {bb_pct:.0f}% ({_get_bb_status(data.bb_position)})")
    
    support_info = technical.get("support_info", {})
    support_name = support_info.get("nearest_support_name", "N/A")
    support_price = support_info.get("nearest_support", 0)
    support_dist = support_info.get("distance_pct", 0)
    lines.append(f" └─ Support: {support_name} {format_currency(support_price)} ({format_percentage(-support_dist)})")
    lines.append("")
    
    # === Valuation Analysis ===
    val_score = valuation["score"]
    pe_status = valuation["pe_status"]
    val_bar = format_score_bar(val_score)
    
    lines.append(f" Valuation [{val_score:.0f}/100] {val_bar} {pe_status}")
    
    if data.pe_ttm:
        pe_percentile = valuation.get("pe_percentile", 50)
        lines.append(f" ├─ PE: {data.pe_ttm:.1f} (Percentile: {pe_percentile:.0f}%)")
    else:
        lines.append(f" ├─ PE: N/A")
    
    if data.pb:
        lines.append(f" ├─ PB: {data.pb:.2f}")
    else:
        lines.append(f" ├─ PB: N/A")
    
    if data.dividend_yield:
        div_pct = data.dividend_yield * 100 if data.dividend_yield < 1 else data.dividend_yield
        lines.append(f" └─ Dividend Yield: {div_pct:.1f}%")
    else:
        lines.append(f" └─ Dividend Yield: N/A")
    lines.append("")
    
    # === Buy Range (v2.0 with 3 tiers) ===
    anchor = buy_range["anchor_price"]
    anchor_type = buy_range["anchor_type"]
    agg = buy_range["aggressive"]
    std = buy_range["standard"]
    con = buy_range.get("conservative")  # v2.0: conservative tier
    current_zone = buy_range["current_zone"]
    company_type = buy_range.get("company_type", "DEFAULT")
    
    # Format anchor type display
    anchor_display = anchor_type.replace("_FAR", "").replace("weighted_average", "Weighted Avg")
    lines.append(f" Buy Range (Type {company_type}, Anchor: {anchor_display} {format_currency(anchor)})")
    lines.append(" ┌──────────────────┬──────────────────────────┬────────┐")
    lines.append(" │ Zone             │ Price Range              │ Alloc  │")
    lines.append(" ├──────────────────┼──────────────────────────┼────────┤")
    
    # Aggressive zone row
    agg_mark = " ← Current" if agg.is_current else ""
    lines.append(f" │ Aggressive       │ {format_currency(agg.price_low):>10} - {format_currency(agg.price_high):<10} │ {agg.suggested_allocation:>6} │{agg_mark}")
    
    # Standard zone row
    std_mark = " ← Current" if std.is_current else ""
    lines.append(f" │ Standard         │ {format_currency(std.price_low):>10} - {format_currency(std.price_high):<10} │ {std.suggested_allocation:>6} │{std_mark}")
    
    # Conservative zone row (v2.0)
    if con:
        con_mark = " ← Current" if con.is_current else ""
        lines.append(f" │ Conservative     │ {format_currency(con.price_low):>10} - {format_currency(con.price_high):<10} │ {con.suggested_allocation:>6} │{con_mark}")
    
    lines.append(" └──────────────────┴──────────────────────────┴────────┘")
    
    # Current zone status
    if current_zone == "above_range":
        dist = buy_range["distance_to_aggressive"]
        lines.append(f" Current price {format_currency(data.current_price)} above range ({format_percentage(dist)})")
    lines.append("")
    
    # === Recommendation ===
    pe_percentile = valuation.get("pe_percentile", 50)
    total_score = technical["score"] * 0.6 + valuation["score"] * 0.4
    
    # Valuation veto logic
    valuation_veto = pe_percentile >= 80 and val_score < 50
    
    if valuation_veto:
        if current_zone == "above_range":
            signal = "WAIT"
        else:
            signal = "HOLD"
    elif total_score >= 75 and current_zone in ["aggressive", "standard", "conservative"]:
        signal = "STRONG_BUY"
    elif total_score >= 60 and current_zone != "above_range":
        signal = "BUY"
    elif total_score >= 50:
        signal = "HOLD"
    elif current_zone == "above_range":
        signal = "WAIT"
    else:
        signal = "CAUTION"
    
    action = buy_range["action"]
    lines.append(f" ★ Recommendation: {signal} - {action}")
    
    # Display warning (if any)
    if warning:
        lines.append(f" ⚠ Warning: {warning}")
    elif valuation_veto:
        lines.append(f" ⚠ Warning: Valuation at historical high (PE percentile: {pe_percentile:.0f}%), signal downgraded")
    
    lines.append("─" * 80)
    
    return "\n".join(lines)


def _get_rsi_status(rsi: float) -> str:
    """Get RSI status text"""
    if rsi < 30:
        return "Oversold"
    elif rsi < 40:
        return "Low"
    elif rsi < 60:
        return "Neutral"
    elif rsi < 70:
        return "High"
    else:
        return "Overbought"


def _get_bb_status(position: float) -> str:
    """Get Bollinger Band position status"""
    if position < 0.2:
        return "Near Lower"
    elif position < 0.4:
        return "Lower Region"
    elif position < 0.6:
        return "Middle"
    elif position < 0.8:
        return "Upper Region"
    else:
        return "Near Upper"


def format_summary_table(results: List[Dict]) -> str:
    """
    Format summary table
    """
    lines = []
    
    lines.append("\n" + "=" * 80)
    lines.append("SUMMARY".center(80))
    lines.append("=" * 80)
    
    # Header
    lines.append(f" {'Symbol':<10} | {'Price':>12} | {'Tech':>4} | {'Val':>4} | {'Zone':<16} | {'Signal':<10} | Action")
    lines.append("-" * 10 + "-+-" + "-" * 12 + "-+-" + "-" * 4 + "-+-" + "-" * 4 + "-+-" + "-" * 16 + "-+-" + "-" * 10 + "-+-" + "-" * 14)
    
    for result in results:
        data = result["data"]
        tech = result["technical"]
        val = result["valuation"]
        buy = result["buy_range"]
        
        symbol = data.symbol
        price = format_currency(data.current_price)
        tech_score = tech["score"]
        val_score = val["score"]
        
        zone = buy["current_zone"]
        if zone == "aggressive":
            zone_str = "Aggressive"
        elif zone == "standard":
            zone_str = "Standard"
        elif zone == "conservative":
            zone_str = "Conservative"
        elif zone == "above_range":
            zone_str = "Above Range"
        else:
            zone_str = "Below Range"
        
        signal = result.get("signal", tech["signal"])
        
        # Short action (v2.0: cumulative allocation)
        if zone == "above_range":
            action = "Wait"
        elif zone == "aggressive":
            action = "Open 25%"
        elif zone == "standard":
            action = "Add to 65%"
        elif zone == "conservative":
            action = "Full 100%"
        else:
            action = "Verify"
        
        lines.append(f" {symbol:<10} | {price:>12} | {tech_score:>4.0f} | {val_score:>4.0f} | {zone_str:<16} | {signal:<10} | {action}")
    
    lines.append("=" * 80)
    
    return "\n".join(lines)
