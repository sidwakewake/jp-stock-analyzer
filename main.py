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
            "warning": str or None
        }
    """
    # 1. Fetch data
    data = fetch_jp_stock(symbol)
    
    # 2. Technical analysis
    technical = calculate_technical_score(data)
    
    # 3. Valuation analysis
    valuation = calculate_valuation_score(data)
    
    # 4. Buy range calculation
    buy_range_result = calculate_buy_range(data)
    
    # 5. Combined score (Technical 60% + Valuation 40%)
    total_score = (technical["score"] * SCORE_WEIGHTS["technical"] + 
                   valuation["score"] * SCORE_WEIGHTS["valuation"])
    
    # 6. Combined signal with valuation veto
    current_zone = buy_range_result["current_zone"]
    pe_percentile = valuation.get("pe_percentile", 50)
    val_score = valuation["score"]
    warning = None
    
    # === Valuation veto logic ===
    # Downgrade buy signal when valuation is at historical high
    valuation_veto = False
    if pe_percentile >= 80 and val_score < 50:
        valuation_veto = True
        warning = f"Valuation at historical high (PE percentile: {pe_percentile:.0f}%)"
    
    # 7. Determine signal
    if valuation_veto:
        # Valuation too high, max HOLD, no buy signal
        if current_zone == "above":
            signal = "WAIT"
        else:
            signal = "HOLD"
            warning = f"{warning}. Consider smaller position or wait for pullback."
    elif total_score >= 75 and current_zone in ["aggressive", "standard", "below"]:
        signal = "STRONG_BUY"
    elif total_score >= 60 and current_zone != "above":
        signal = "BUY"
    elif total_score >= 50:
        signal = "HOLD"
    elif current_zone == "above":
        signal = "WAIT"
    else:
        signal = "CAUTION"
    
    return {
        "data": data,
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
