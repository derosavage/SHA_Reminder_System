# Danvas1 - Strategy Logic Documentation

## Trading Philosophy

Danvas1 trades like a professional institutional trader:

1. **Higher Timeframe Analysis**: Determine trend direction and market structure
2. **Lower Timeframe Precision**: Execute entries with precision
3. **RSI Confirmation**: Use RSI for overbought/oversold conditions
4. **Liquidity Zones**: Trade at key liquidity areas
5. **Support/Resistance**: Respect structural levels
6. **Market Structure**: Follow the trend unless reversal is certain
7. **Confirmation Candles**: Never trade without confirmation
8. **Volatility Conditions**: Adjust based on market volatility
9. **Multi-Timeframe Confluence**: Require alignment across timeframes
10. **Dynamic Risk Management**: Adjust based on conditions

## Core Strategy: Strategy V1

### Higher Timeframe Analysis (1H, 4H, 12H, Daily)

**Purpose**: Determine overall market direction and bias

**Analysis Components:**
1. **Trend Direction**: EMA alignment (50, 200)
2. **Market Structure**: Higher highs/lows vs lower highs/lows
3. **Momentum Bias**: RSI state and momentum
4. **Strong S/R Zones**: Key price levels
5. **Premium/Discount Zones**: Fair value areas
6. **Liquidity Pools**: Institutional interest areas
7. **Volatility Regime**: Current market conditions

### Lower Timeframe Entry (15m)

**Purpose**: Precise entry with confirmation

**Entry Components:**
1. **RSI Oscillator**: Oversold (<30) for longs, Overbought (>70) for shorts
2. **EMA Crossover**: Fast EMA crossing slow EMA
3. **Candlestick Patterns**: Engulfing, hammer, shooting star
4. **Volume Confirmation**: High volume confirming move
5. **Structure Break**: Breaking key levels

### Signal Generation

**LONG Signal Requirements:**
- HTF: Bullish trend (price > EMA50 > EMA200)
- HTF: RSI in oversold or recovering
- HTF: Momentum bullish
- LTF: RSI < 40 (recovering from oversold)
- LTF: Bullish candle formation
- LTF: Volume confirmation
- Confluence Score >= 3

**SHORT Signal Requirements:**
- HTF: Bearish trend (price < EMA50 < EMA200)
- HTF: RSI in overbought or weakening
- HTF: Momentum bearish
- LTF: RSI > 60 (weakening from overbought)
- LTF: Bearish candle formation
- LTF: Volume confirmation
- Confluence Score >= 3

### Stop Loss Placement

**Method**: ATR-based dynamic stop loss

**Formula**:
```
SL Distance = ATR × ATR_Multiplier
Default Multiplier = 2.5
```

**Adjustments**:
- High volatility: Increase multiplier to 3.0
- Low volatility: Decrease multiplier to 2.0
- S/R nearby: Place SL just beyond level

### Take Profit Strategy

**Method**: Multi-level TP with partial exits

**Default Levels**:
- TP1: 50% at 2:1 RR
- TP2: 30% at 3:1 RR
- TP3: 20% at 4:1 RR

**Dynamic Adjustment**:
- Strong trends: Extend TP
- Weak momentum: Tighten TP
- Structure near: Take profit

### Position Management

**Breakeven Rule**:
When profit exceeds 2x risk, move SL to breakeven + small buffer

**Early Exit Conditions**:
1. Reversal candlestick pattern
2. Structure break
3. RSI divergence
4. Momentum fading
5. News/event risk

### Risk Management Rules

1. **Position Sizing**: Risk 20% of equity per trade
2. **Max Margin Usage**: 50% of available margin
3. **Daily Drawdown Limit**: 5% of starting equity
4. **Consecutive Loss Limit**: Stop after 3 losses
5. **Trade Cooldown**: 30 minutes between trades
6. **Minimum R/R Ratio**: 2:1 required

## Signal Filters

### Volatility Filter
- Minimum ATR%: 0.5%
- Maximum ATR%: 5.0%
- Purpose: Avoid choppy and extreme markets

### Liquidity Filter
- Maximum spread: 0.5%
- Minimum order book depth
- Purpose: Ensure execution quality

### Session Filter
- Avoid weekends
- Avoid late Friday
- Purpose: Trade during liquid hours

### Spread Filter
- Maximum spread: 0.3%
- Purpose: Ensure tight execution

### Momentum Filter
- Minimum 60% directional candles
- Volume trend confirmation
- Purpose: Trade with momentum

## Market Regime Adaptation

### Trending Markets (ADX > 70)
- Wider SL (2.0 ATR)
- Extended TP (3.5 ATR)
- Higher confidence threshold
- Trade with trend only

### Ranging Markets (ADX < 40)
- Tighter SL (2.5 ATR)
- Normal TP (4.0 ATR)
- Higher confluence required
- Mean reversion strategy

### Volatile Markets (ATR > 5%)
- Wider SL (3.0 ATR)
- Extended TP (5.0 ATR)
- Maximum confidence required
- Reduced position size

## Confluence Scoring

| Factor | Points |
|--------|--------|
| HTF Trend Aligned | 1.0 |
| HTF RSI Oversold/Overbought | 0.5 |
| Momentum Direction | 0.5 |
| Volume Spike | 0.5 |
| Adequate Volatility | 0.5 |

**Minimum Score**: 3.0 for signal activation

## Entry Flow

```
1. Scan Symbol
   ↓
2. HTF Analysis
   ↓
3. Trend Detection
   ↓
4. Signal Check (RSI + Candle + Volume)
   ↓
5. Confluence Score >= 3?
   → No: Reject
   → Yes: Continue
   ↓
6. Risk/Reward >= 2:1?
   → No: Adjust TP
   → Yes: Continue
   ↓
7. Risk Validation
   ↓
8. Execute Trade
```

## Exit Flow

```
1. Check Partial TP Levels
   ↓
2. Check Breakeven Trigger
   ↓
3. Check Early Exit Conditions
   ↓
4. Monitor for Reversal
   ↓
5. TP or SL Hit → Close Trade
```