# JP Stock Analyzer

日本股票技术面买点分析 CLI 工具。

## Features

- 实时价格与技术指标获取（via yfinance）
- RSI / MA / 布林带技术分析
- 买入区间计算与当前位置判断
- 简化估值分析（PE 历史百分位）
- Terminal 友好的输出格式

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Analyze single stock
python main.py 7011

# Analyze multiple stocks
python main.py 7011,8316,9984

# Brief mode (summary only)
python main.py -b 7011,8316
```

## Output Example

```
================================================================================
                         JP STOCK ANALYZER - 2026-01-08
================================================================================
Analyzing: 7011.T, 8316.T

[7011.T] Mitsubishi Heavy Industries
────────────────────────────────────────────────────────────────────────────────
 Price: ¥4,163 (+1.2%)  |  52W: ¥1,850 - ¥2,680  |  From High: -8.6%

 Technical [70/100] ██████████████░░░░░░ HOLD
 ├─ RSI(14): 42 (Neutral)
 ├─ MA: Bullish
 ├─ Bollinger Band: 45% (Middle)
 └─ Support: MA200 ¥2,180 (-11.0%)

 Buy Range (Anchor: MA200 ¥2,180)
 ┌─────────────────┬──────────────────────────┬────────┐
 │ Zone            │ Price Range              │ Alloc  │
 ├─────────────────┼──────────────────────────┼────────┤
 │ Aggressive Zone │     ¥2,115 - ¥2,289      │   50%  │ ← Current
 │ Standard Zone   │     ¥1,962 - ¥2,115      │   50%  │
 └─────────────────┴──────────────────────────┴────────┘

 ★ Recommendation: HOLD - In aggressive zone, can open 50% position
────────────────────────────────────────────────────────────────────────────────
```

## Technical Scoring

| Component | Max Score | Description |
|-----------|-----------|-------------|
| RSI | 25 | RSI(14) position analysis |
| MA | 25 | Moving average alignment |
| Bollinger Band | 25 | Price position in BB |
| Support | 25 | Distance to support levels |

## Signal Mapping

| Total Score | Zone | Signal |
|-------------|------|--------|
| ≥75 | In Range | STRONG_BUY |
| ≥60 | In Range | BUY |
| ≥45 | In Range | BUY |
| Any | Above Range | WAIT |
| Any | In Range + PE%≥80 | CAUTION |
| <45 | Any | AVOID |

## License

MIT
