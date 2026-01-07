"""
JP Stock Data Model
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class JPTickerData:
    """Japanese stock data model"""
    
    # === Basic Info ===
    symbol: str                    # "7011.T"
    name: str                      # Company name from yfinance
    currency: str                  # "JPY"
    sector: str                    # "Industrials" from yfinance
    
    # === Price Data ===
    current_price: float           # Current price
    prev_close: float              # Previous close
    change_pct: float              # Change percentage
    high_52w: float                # 52-week high
    low_52w: float                 # 52-week low
    
    # === Moving Averages ===
    ma_5: float                    # 5-day MA
    ma_20: float                   # 20-day MA
    ma_50: float                   # 50-day MA
    ma_120: float                  # 120-day MA (new for v2.0)
    ma_200: float                  # 200-day MA
    
    # === New for v2.0 ===
    high_90d: float                # 90-day high (for pullback anchor)
    volatility: float              # Annualized volatility
    
    # === Technical Indicators ===
    rsi_14: float                  # RSI(14)
    bb_upper: float                # Bollinger Band upper
    bb_middle: float               # Bollinger Band middle (=MA20)
    bb_lower: float                # Bollinger Band lower
    bb_width: float                # Band width (upper-lower)/middle
    bb_position: float             # Current price position (0=lower, 1=upper)
    
    # === Fundamentals (Simplified) ===
    pe_ttm: Optional[float]        # Trailing PE
    pb: Optional[float]            # Price to Book
    dividend_yield: Optional[float] # Dividend yield
    market_cap: Optional[float]    # Market cap (billion JPY)
    
    # === Historical Valuation Reference ===
    pe_percentile: Optional[float] # Current PE percentile in 1-year history
    
    # === Metadata ===
    last_updated: datetime
    data_quality: str              # "good" / "partial" / "error"
