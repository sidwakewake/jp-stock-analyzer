"""
JP Stock Analyzer - Main Entry Point
Japanese Stock Buy Point Analysis CLI Tool

Usage:
    python main.py 7011,8316,9984
    python main.py 7011.T,8316.T
    python main.py 7011 8316 9984
    python main.py --brief 7011,8316
"""
import argparse
import sys
import warnings
from datetime import datetime
from typing import List

# Suppress yfinance FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning)

# Set UTF-8 encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from data.fetcher import fetch_jp_stock, parse_input_symbols
from modules.technical import calculate_technical_score
from modules.fundamental import calculate_valuation_score
from modules.buy_range import calculate_buy_range
from utils.formatter import (
    format_header,
    format_stock_analysis,
    format_summary_table,
)
from config import SCORE_WEIGHTS


def classify_company_type(data) -> str:
    """
    Classify company type for buy range calculation.
    
    Type A: Stable Profitable (PE>0, low growth)
    Type B: Growth (PE>0, high growth)
    Type C: High Growth (PE<0 or None, high revenue growth)
    Type D: Cyclical (energy, materials, industrials)
    """
    # Cyclical sector detection
    cyclical_sectors = ["Energy", "Materials", "Industrials", "Utilities"]
    if data.sector in cyclical_sectors:
        return "D"
    
    # Based on profitability
    is_profitable = data.pe_ttm is not None and data.pe_ttm > 0
    
    if is_profitable:
        return "A"  # Default stable type
    else:
        return "C"  # Unprofitable / high growth


def analyze_single_stock(symbol: str) -> dict:
    """
    Analyze a single stock
    
    Returns:
        {
            "data": JPTickerData,
            "technical": dict,
            "valuation": dict,
            "buy_range": dict,
            "total_score": float,
            "signal": str,
            "warning": str or None,
            "company_type": str
        }
    """
    # 1. Fetch data
    data = fetch_jp_stock(symbol)
    
    # 2. Classify company type
    company_type = classify_company_type(data)
    
    # 3. Technical analysis
    technical = calculate_technical_score(data)
    
    # 4. Valuation analysis
    valuation = calculate_valuation_score(data)
    
    # 5. Buy range calculation (v2.0 with company type)
    buy_range_result = calculate_buy_range(data, company_type)
    
    # 6. Combined score (Technical 60% + Valuation 40%)
    total_score = (technical["score"] * SCORE_WEIGHTS["technical"] + 
                   valuation["score"] * SCORE_WEIGHTS["valuation"])
    
    # 7. Determine signal (simplified - no HOLD)
    current_zone = buy_range_result["current_zone"]
    pe_percentile = valuation.get("pe_percentile", 50)
    val_score = valuation["score"]
    warning = None
    
    # === Signal logic (simplified) ===
    if current_zone == "above_range":
        # Above range = always WAIT
        signal = "WAIT"
        if pe_percentile >= 80:
            warning = f"PE percentile {pe_percentile:.0f}% - wait for better entry"
    elif pe_percentile >= 80 and val_score < 50:
        # In range but valuation too high = CAUTION
        signal = "CAUTION"
        warning = f"Valuation at historical high (PE percentile: {pe_percentile:.0f}%)"
    elif total_score >= 75:
        signal = "STRONG_BUY"
    elif total_score >= 60:
        signal = "BUY"
    elif total_score >= 45:
        signal = "BUY"  # Buyable but no rush
    else:
        signal = "AVOID"
    
    return {
        "data": data,
        "company_type": company_type,
        "technical": technical,
        "valuation": valuation,
        "buy_range": buy_range_result,
        "total_score": total_score,
        "signal": signal,
        "warning": warning
    }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="JP Stock Analyzer - Japanese Stock Buy Point Analysis",
        epilog="Example: python main.py 7011,8316,9984"
    )
    parser.add_argument(
        "symbols", 
        nargs="?",
        default="",
        help="Stock symbols, comma separated (e.g.: 7011,8316,9984)"
    )
    parser.add_argument(
        "--brief", "-b",
        action="store_true",
        help="Brief mode, only show summary table"
    )
    args = parser.parse_args()
    
    # Parse stock symbols
    if not args.symbols:
        print("Please input stock symbols, comma separated")
        print("Example: python main.py 7011,8316,9984")
        sys.exit(1)
    
    symbols = parse_input_symbols(args.symbols)
    
    if not symbols:
        print("No valid stock symbols found")
        sys.exit(1)
    
    # Print header
    print(format_header())
    print(f"Analyzing: {', '.join(symbols)}\n")
    
    results = []
    
    # Analyze each stock
    for symbol in symbols:
        try:
            result = analyze_single_stock(symbol)
            results.append(result)
            
            if not args.brief:
                print(format_stock_analysis(
                    result["data"],
                    result["technical"],
                    result["valuation"],
                    result["buy_range"],
                    result.get("warning")
                ))
        except Exception as e:
            print(f"[ERROR] {symbol}: {str(e)}\n")
    
    # Print summary table
    if len(results) > 0:
        print(format_summary_table(results))
    
    print(f"\nLast Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
