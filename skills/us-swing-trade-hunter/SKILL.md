---
name: us-swing-trade-hunter
description: Identify high-probability US stock swing trade setups with exact entry zone, stop-loss, TP1/TP2/TP3 targets, risk:reward, confidence score, and holding period. Use when the user asks for swing trade ideas, stock setups, "any swing trades?", "any trades before market open?", "find opportunities now", or wants entry/exit levels and position sizing for a US equity swing trade. Returns NO TRADE if no high-quality setup exists rather than forcing a recommendation.
---

# US Swing Trade Hunter

## Objective
Identify high-probability US stock swing trades quickly and return actionable:

- Entry price / entry zone
- Stop Loss
- TP1 / TP2 / TP3
- Risk:Reward
- Confidence score
- Expected holding period
- Setup invalidation

Never force a trade. If no high-quality setup exists, return **NO TRADE**.

## Universe
Scan liquid US-listed stocks, prioritizing:

- S&P 500
- Nasdaq 100
- Large/mid-cap liquid stocks
- Average daily volume > 1M shares
- Prefer market cap > $2B
- Exclude penny stocks and illiquid names

## Live Data Rule
Before recommending any trade:

1. Verify the latest market price.
2. Timestamp the analysis.
3. Check pre-market/after-hours when relevant.
4. Never generate entry/TP/SL using stale prices.
5. Check upcoming earnings and major scheduled catalysts.

If reliable current pricing cannot be verified, do not issue the trade.

# SETUPS TO SEARCH

Prioritize these setups:

### 1. Pullback in Strong Uptrend
Look for:

- Price above rising 20 EMA
- 20 EMA above 50 DMA
- 50 DMA above 200 DMA
- Pullback toward 10/20 EMA or previous breakout
- Declining volume during pullback
- RSI resetting toward 40–55
- Bullish reversal candle
- Strong relative strength vs SPY/QQQ

This is the preferred setup.

### 2. Breakout + Retest
Look for:

- Clear multi-week resistance
- Breakout with volume >1.5× average
- Price retests breakout level
- Old resistance becomes support
- Market trend supports the move

Avoid chasing extended breakouts.

### 3. Momentum Breakout
Require:

- Strong relative strength
- Volume expansion
- Catalyst or sector strength
- Clean resistance level
- Enough upside to provide ≥2:1 R:R

### 4. Oversold Reversal
Only trade strong companies where:

- Price reaches major support
- RSI shows bullish divergence
- Selling momentum is weakening
- Reversal candle confirms
- Market/sector is not collapsing

Require stronger confirmation than trend trades.

### 5. Relative-Strength Leader
Find stocks outperforming SPY/QQQ during:

- Market pullbacks
- Sector weakness
- Consolidations

Prioritize stocks making higher lows while the index makes lower lows.

# HARD FILTERS

Reject the trade if:

- Risk/reward < 2.0
- Price is >5% above ideal entry
- Earnings are within 2 trading days unless explicitly an earnings trade
- Stop must be unrealistically tight
- Major resistance sits directly above entry
- Average liquidity is poor
- Market regime strongly contradicts the trade
- Setup depends only on RSI/MACD without price structure
- Stock has already made an excessively extended move

# MARKET REGIME

Before individual stocks, evaluate:

- SPY trend
- QQQ trend
- IWM trend
- VIX
- Breadth
- Market advance/decline
- Sector relative strength
- Treasury yields when relevant

Classify environment:

**GREEN**
Normal long setups allowed.

**YELLOW**
Reduce position size and demand better entries.

**RED**
Avoid ordinary long swing trades. Only exceptional setups qualify.

# SWING SCORE — 100 POINTS

## Trend — 20
- Daily trend: 10
- Weekly trend: 5
- Moving-average alignment: 5

## Price Structure — 20
- Support quality: 5
- Breakout/retest quality: 5
- Higher highs/lows: 5
- Clean invalidation level: 5

## Relative Strength — 15
- vs SPY/QQQ: 8
- vs sector: 7

## Volume / Institutional Activity — 10
- Accumulation: 5
- Breakout/reversal volume: 5

## Momentum — 10
Use:
- RSI
- MACD
- Rate of change
- Momentum divergence

## Catalyst — 10
Examples:
- Earnings revisions
- Guidance
- Product/news catalyst
- Analyst revisions
- Sector catalyst

## Market/Sector Alignment — 10

## Risk/Reward — 5
- <2:1 = reject
- 2–2.5 = 2
- 2.5–3 = 4
- >3 = 5

# RATING

90–100 = A+ / Exceptional
85–89 = A / High confidence
80–84 = A− / Strong
75–79 = B+ / Tradable
70–74 = Watchlist only
<70 = Reject

Default recommendation threshold:

**Only recommend trades scoring ≥78.**

# ENTRY LOGIC

Do not simply say "Buy at current price."

Choose one:

**Aggressive Entry**
Near support before full confirmation.

**Standard Entry**
After confirmation/reclaim.

**Breakout Entry**
Above clearly defined resistance.

Always state which entry is preferred.

Example:

Preferred entry: $142.50–143.50
Confirmation: Hold above $142.00 and reclaim $143.20
Do not chase >$146.

# STOP LOSS

Stop must be based on technical invalidation, not an arbitrary percentage.

Place below:

- Swing low
- Support level
- Breakout structure
- ATR-adjusted invalidation

Calculate:

Entry → Stop distance
% risk per share

Avoid stops sitting directly inside ordinary market noise.

# PROFIT TARGETS

Provide:

TP1 = first resistance / ~1.5–2R
TP2 = next structural target / ~2.5–3R
TP3 = extended target if trend continues

Example:

Entry: $100
SL: $96
Risk: $4

TP1: $108 = 2R
TP2: $112 = 3R
TP3: $118 = 4.5R

After TP1, consider moving the stop toward breakeven only if price structure supports it.

# POSITION SIZING

Default maximum portfolio risk:

0.5–1% per trade.

Formula:

Position Size =
Maximum Dollar Risk ÷ (Entry − Stop)

Never increase position size simply because confidence is high.

# OUTPUT

Start with:

## MARKET STATUS
Regime: GREEN / YELLOW / RED
SPY: Bullish / Neutral / Bearish
QQQ: Bullish / Neutral / Bearish
VIX: value + interpretation

Then show only the best opportunities:

| Rank | Ticker | Setup | Entry | SL | TP1 | TP2 | TP3 | R:R | Score | Confidence |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | XYZ | Pullback | $ | $ | $ | $ | $ | | /100 | High |

Then for each A-quality trade:

### TICKER — Setup

Current price:
Preferred entry:
Alternative entry:
Do-not-chase level:
Stop:
TP1:
TP2:
TP3:
Risk/reward:
Holding period:
Swing score: /100
Confidence: /10

**Why it works:**
Maximum 3 concise points.

**Invalidation:**
State exactly what would make the setup wrong.

**Catalysts/Risks:**
Include earnings date and relevant upcoming events.

# FAST SCAN MODE

When asked:

- "Any swing trades?"
- "Anything before market open?"
- "Any trades today?"
- "Find opportunities now."

Immediately scan the market and return only:

1. Top 5 setups
2. Exact entry
3. SL
4. TP1/TP2
5. Score
6. Confidence
7. Whether to ENTER NOW / WAIT / SKIP

Do not provide long company descriptions.

# SECONDARY WATCHLIST

Also return up to 5 stocks that are good setups but have not triggered.

For each give:

Ticker | Trigger price | Ideal entry | Reason for waiting

This prevents chasing and allows preparation before the trade activates.

# CRITICAL RULE

A stock being a great company does NOT make it a good swing trade.

A stock being oversold does NOT make it a buy.

The priority order is:

**Price structure → Risk/reward → Market regime → Relative strength → Momentum → Fundamentals/catalyst.**

When conditions are poor, cash is a valid position.
