"""
Data Fetcher Module - Fetch JP stock data from yfinance
"""
import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.ticker import JPTickerData


def normalize_symbol(symbol: str) -> str:
    """
    Normalize stock symbol
    
    Args:
        symbol: Input symbol, e.g. "7011" or "7011.T"
    
    Returns:
        Normalized symbol, e.g. "7011.T"
    """
    symbol = symbol.strip().upper()
    if not symbol.endswith(".T"):
        symbol = symbol + ".T"
    return symbol


def parse_input_symbols(input_str: str) -> List[str]:
    """
    Parse user input stock symbols
    
    Args:
        input_str: User input, e.g. "7011,8316,9984" or "7011.T, 8316.T"
    
    Returns:
        List of normalized symbols ["7011.T", "8316.T", "9984.T"]
    """
    if not input_str:
        return []
    
    # Split by comma
    parts = input_str.split(",")
    
    # Normalize each symbol
    symbols = []
    for part in parts:
        part = part.strip()
        if part:
            normalized = normalize_symbol(part)
            if normalized not in symbols:
                symbols.append(normalized)
    
    return symbols


def fetch_price_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch historical price data
    
    Args:
        symbol: Stock symbol
        period: Time period ("1y", "2y", "5y")
    
    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume
    """
    symbol = normalize_symbol(symbol)
    
    try:
        df = yf.download(symbol, period=period, progress=False)
        
        if df.empty:
            raise ValueError(f"No data available for {symbol}")
        
        # Handle missing values with forward fill
        df = df.ffill()
        
        return df
    except Exception as e:
        raise ValueError(f"Failed to fetch price history for {symbol}: {str(e)}")


def _calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate RSI internally"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.iloc[-1] if not rsi.empty else 50.0


def _calculate_bollinger_bands(prices: pd.Series, period: int = 20, num_std: float = 2.0) -> Dict[str, float]:
    """Calculate Bollinger Bands internally"""
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


def fetch_jp_stock(symbol: str) -> JPTickerData:
    """
    Fetch complete data for a single JP stock
    
    Args:
        symbol: Stock symbol, e.g. "7011.T" (will be normalized)
    
    Returns:
        JPTickerData object
    
    Raises:
        ValueError: If unable to fetch data
    """
    symbol = normalize_symbol(symbol)
    
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Get company name
        name = info.get("shortName") or info.get("longName") or symbol
        
        # Get current price
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose") or 0
        
        # Calculate change percentage
        if prev_close and prev_close > 0:
            change_pct = (current_price - prev_close) / prev_close
        else:
            change_pct = 0
        
        # 52-week high/low
        high_52w = info.get("fiftyTwoWeekHigh") or 0
        low_52w = info.get("fiftyTwoWeekLow") or 0
        
        # Fetch historical data for technical analysis
        history = fetch_price_history(symbol, period="1y")
        
        # Handle multi-level columns from yfinance
        if isinstance(history.columns, pd.MultiIndex):
            close_prices = history["Close"][symbol] if symbol in history["Close"].columns else history["Close"].iloc[:, 0]
        else:
            close_prices = history["Close"]
        
        # Calculate moving averages
        ma_5 = close_prices.rolling(window=5).mean().iloc[-1] if len(close_prices) >= 5 else current_price
        ma_20 = close_prices.rolling(window=20).mean().iloc[-1] if len(close_prices) >= 20 else current_price
        ma_50 = close_prices.rolling(window=50).mean().iloc[-1] if len(close_prices) >= 50 else current_price
        ma_120 = close_prices.rolling(window=120).mean().iloc[-1] if len(close_prices) >= 120 else current_price * 0.90
        ma_200 = close_prices.rolling(window=200).mean().iloc[-1] if len(close_prices) >= 200 else current_price * 0.85
        
        # Calculate 90-day high (for pullback anchor)
        if isinstance(history.columns, pd.MultiIndex):
            high_prices = history["High"][symbol] if symbol in history["High"].columns else history["High"].iloc[:, 0]
        else:
            high_prices = history["High"]
        high_90d = high_prices.tail(90).max() if len(high_prices) >= 90 else high_prices.max()
        
        # Calculate annualized volatility
        if len(close_prices) >= 20:
            daily_returns = close_prices.pct_change().dropna()
            volatility = daily_returns.std() * (252 ** 0.5)  # Annualized
        else:
            volatility = 0.30  # Default 30%
        
        # Calculate RSI
        rsi_14 = _calculate_rsi(close_prices, 14)
        
        # Calculate Bollinger Bands
        bb = _calculate_bollinger_bands(close_prices, 20, 2.0)
        
        # Fundamentals
        pe_ttm = info.get("trailingPE")
        pb = info.get("priceToBook")
        
        # Validate dividend_yield (normal range 0-15%)
        # yfinance sometimes returns wrong dividendYield, prefer trailingAnnualDividendYield
        dividend_yield_raw = info.get("dividendYield")
        trailing_yield = info.get("trailingAnnualDividendYield")
        
        if dividend_yield_raw is not None:
            # yfinance returns decimal form, e.g. 0.03 = 3%
            if dividend_yield_raw > 0.15:  # Over 15% is abnormal, use trailing instead
                dividend_yield = trailing_yield if trailing_yield and 0 < trailing_yield < 0.15 else None
            elif dividend_yield_raw < 0:
                dividend_yield = None
            else:
                dividend_yield = dividend_yield_raw
        elif trailing_yield is not None and 0 < trailing_yield < 0.15:
            dividend_yield = trailing_yield
        else:
            dividend_yield = None
        
        market_cap_raw = info.get("marketCap")
        market_cap = market_cap_raw / 1e9 if market_cap_raw else None  # Convert to billions
        
        # Sector
        sector = info.get("sector") or "N/A"
        
        # Data quality assessment
        data_quality = "good"
        if not current_price or current_price == 0:
            data_quality = "error"
        elif not pe_ttm or not ma_200:
            data_quality = "partial"
        
        return JPTickerData(
            symbol=symbol,
            name=name,
            currency="JPY",
            sector=sector,
            current_price=current_price,
            prev_close=prev_close,
            change_pct=change_pct,
            high_52w=high_52w,
            low_52w=low_52w,
            ma_5=ma_5,
            ma_20=ma_20,
            ma_50=ma_50,
            ma_120=ma_120,
            ma_200=ma_200,
            high_90d=high_90d,
            volatility=volatility,
            rsi_14=rsi_14,
            bb_upper=bb["upper"],
            bb_middle=bb["middle"],
            bb_lower=bb["lower"],
            bb_width=bb["width"],
            bb_position=bb["position"],
            pe_ttm=pe_ttm,
            pb=pb,
            dividend_yield=dividend_yield,
            market_cap=market_cap,
            pe_percentile=None,  # Will be calculated later
            last_updated=datetime.now(),
            data_quality=data_quality
        )
        
    except Exception as e:
        raise ValueError(f"Failed to fetch data for {symbol}: {str(e)}")


def fetch_multiple_stocks(symbols: List[str]) -> Dict[str, JPTickerData]:
    """
    Fetch data for multiple stocks
    
    Args:
        symbols: List of stock symbols (will be normalized)
    
    Returns:
        {symbol: JPTickerData} mapping
    """
    results = {}
    
    for symbol in symbols:
        try:
            normalized = normalize_symbol(symbol)
            data = fetch_jp_stock(normalized)
            results[normalized] = data
        except Exception as e:
            print(f"[WARNING] Failed to fetch {symbol}: {str(e)}")
    
    return results
