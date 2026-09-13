# FinViz Screener Filter Reference (best-effort)

**Status:** This file was reconstructed from the Common Concept Mapping table shipped with the
`finviz-screener` skill, the descriptive filter options scraped live from finviz.com/screener.ashx,
and widely-documented public FinViz filter-code conventions. It is **not** FinViz's official
exhaustive code list. If a code below doesn't produce the expected result, open the screener UI,
set the filter manually, and read the resulting `f=` query parameter — that's always ground truth.

---

## Operator Suffix Legend

Most `fa_`/`ta_`/`sh_` filters follow a `<metric>_<operator><value>` pattern:

| Suffix | Meaning | Example |
|---|---|---|
| `_oN` | Over N | `fa_pe_o20` → P/E over 20 |
| `_uN` | Under N | `fa_pe_u20` → P/E under 20 |
| `_NtoM` | Range N to M | `fa_pe_10to20` → P/E between 10 and 20 |
| `_pos` | Positive | `fa_epsqoq_pos` → positive QoQ EPS growth |
| `_neg` | Negative | `fa_eps5years_neg` → negative 5Y EPS growth |
| `_high` / `_low` | Qualitative tier (varies by metric) | `fa_div_high` → dividend yield > 5% |
| `_profitable` | Positive earnings | `fa_pe_profitable` |
| `_verypos` / `_veryneg` | Strong positive/negative (insider/inst. transactions) | `sh_insidertrans_verypos` |

---

## Descriptive Filters

### Market Cap (`cap_`)
| Code | Meaning |
|---|---|
| `cap_mega` | Mega ($200bln and more) |
| `cap_large` | Large ($10bln to $200bln) |
| `cap_mid` | Mid ($2bln to $10bln) |
| `cap_small` | Small ($300mln to $2bln) |
| `cap_micro` | Micro ($50mln to $300mln) |
| `cap_nano` | Nano (under $50mln) |
| `cap_largeover` | +Large (over $10bln) |
| `cap_midover` | +Mid (over $2bln) |
| `cap_smallover` | +Small (over $300mln) |
| `cap_microover` | +Micro (over $50mln) |

### Exchange (`exch_`)
`exch_amex`, `exch_cboe`, `exch_nasd`, `exch_nyse`

### Index (`idx_`)
`idx_sp500`, `idx_ndx` (NASDAQ 100), `idx_dji`, `idx_rut` (Russell 2000)

### Country / Geography (`geo_`)
`geo_usa`, `geo_notusa` (Foreign ex-USA), `geo_asia`, `geo_europe`, `geo_latinamerica`, `geo_bric`,
plus individual countries, e.g. `geo_china`, `geo_japan`, `geo_india`, `geo_canada`, `geo_uk`, `geo_germany`.

### Sector (`sec_`)
`sec_basicmaterials`, `sec_communicationservices`, `sec_consumercyclical`, `sec_consumerdefensive`,
`sec_energy`, `sec_financial`, `sec_healthcare`, `sec_industrials`, `sec_realestate`,
`sec_technology`, `sec_utilities`

### Industry (`ind_`)
One per FinViz industry taxonomy entry, e.g. `ind_semiconductors`, `ind_softwareapplication`,
`ind_softwareinfrastructure`, `ind_biotechnology`, `ind_banksregional`, `ind_oilgasep`,
`ind_reitresidential`, `ind_aerospacedefense`, `ind_internetretail`. Live list (Sep 2026) includes
over 140 industries spanning Advertising Agencies → Waste Management — confirm the exact slug in
the screener UI if unsure, since slugs are a lowercased/condensed form of the display name.

---

## Fundamental Filters (`fa_`)

| Metric | Example Codes |
|---|---|
| P/E | `fa_pe_u15`, `fa_pe_o30`, `fa_pe_10to20`, `fa_pe_profitable` |
| Forward P/E | `fa_fpe_u15`, `fa_fpe_o30` |
| PEG | `fa_peg_u1`, `fa_peg_low` |
| P/S | `fa_ps_u2` |
| P/B | `fa_pb_u1`, `fa_pb_u2` |
| P/Cash | `fa_pc_u3` |
| P/Free Cash Flow | `fa_pfcf_u15` |
| Dividend Yield | `fa_div_o3`, `fa_div_o5`, `fa_div_3to8`, `fa_div_none`, `fa_div_high` |
| Payout Ratio | `fa_payoutratio_u60` |
| EPS growth (this/next year) | `fa_eps_o10`, `fa_epsnext_o10` |
| EPS growth (3Y / 5Y) | `fa_eps3years_pos`, `fa_eps5years_pos`, `fa_eps5years_o10`, `fa_eps5years_neg` |
| EPS growth QoQ | `fa_epsqoq_pos`, `fa_epsqoq_o25` |
| Sales growth (5Y / QoQ) | `fa_sales5years_pos`, `fa_sales5years_o5`, `fa_salesqoq_pos`, `fa_salesqoq_o15` |
| Dividend growth | `fa_divgrowth_3yo10`, `fa_divgrowth_5ypos` |
| ROA / ROE / ROIC | `fa_roa_o10`, `fa_roe_o15`, `fa_roe_o20`, `fa_roic_o10` |
| Current / Quick Ratio | `fa_curratio_o1.5`, `fa_quickratio_o1` |
| Debt/Equity | `fa_debteq_u0.5`, `fa_ltdebteq_u0.5` |
| Margins | `fa_grossmargin_o40`, `fa_opermargin_o20`, `fa_netmargin_o10` |
| EV/EBITDA, EV/Sales | `fa_evebitda_u10`, `fa_evsales_u3` |

---

## Technical Filters (`ta_`)

| Metric | Example Codes |
|---|---|
| RSI (14) | `ta_rsi_os30` (oversold <30), `ta_rsi_ob70` (overbought >70) |
| SMA position | `ta_sma50_pa` (price above 50-SMA), `ta_sma200_pa`, `ta_sma20_pb` (price below) |
| SMA cross | `ta_sma200_sb50` (200-SMA below 50-SMA → uptrend context) |
| 52-week range | `ta_highlow52w_b0to5h` (within 5% of high), `ta_highlow52w_a0to5l` (within 5% of low), `ta_highlow52w_b20to30h` |
| All-time range | `ta_alltime_b0to5h` |
| Performance | `ta_perf_4wup`, `ta_perf_13wup`, `ta_perf_13wdown`, `ta_perf_26wup`, `ta_perf_52wup` |
| Beta | `ta_beta_u0.5`, `ta_beta_o1.5` |
| Average True Range | `ta_averagetruerange_o1.5` |
| Volatility (week/month) | `ta_volatility_wo3` |
| 20-day high/low | `ta_highlow20d_b0to5h` |

---

## Shareholders / Volume Filters (`sh_`)

| Metric | Example Codes |
|---|---|
| Average volume | `sh_avgvol_o200`, `sh_avgvol_o500`, `sh_avgvol_o1000` |
| Relative volume | `sh_relvol_o1.5`, `sh_relvol_o2`, `sh_relvol_u1` |
| Float | `sh_float_u20` (under 20M shares) |
| Institutional ownership | `sh_instown_o60` |
| Insider transactions | `sh_insidertrans_verypos`, `sh_insidertrans_veryneg` |
| Short float / short interest | `sh_short_o20` |

---

## Other Filters

| Prefix | Purpose | Examples |
|---|---|---|
| `earningsdate_` | Earnings date window | `earningsdate_today`, `earningsdate_nextweek`, `earningsdate_thismonth` |
| `ipodate_` | IPO recency | `ipodate_thismonth`, `ipodate_lastyear` |
| `targetprice_` | Analyst target vs. price | `targetprice_a20` (target ≥20% above price), `targetprice_b10` |
| `news_` | Recent news presence | `news_date_today` |
| `an_` | Analyst recommendation | `an_recom_buybetter`, `an_recom_strongbuy` |
| `etf_` | ETF-specific filters (category, AUM, flows) | Elite-heavy; verify in UI |

---

## Themes (Public tier — `--themes`)

Aging Population & Longevity, Agriculture & FoodTech, Artificial Intelligence, Autonomous Systems,
Big Data, Biometrics, Cloud Computing, Commodities (Agriculture/Energy/Metals), Consumer Goods,
Crypto & Blockchain, Cybersecurity, Defense & Aerospace, Digital Entertainment, E-commerce,
Education Technology, Electric Vehicles, Energy (Renewable/Traditional), Environmental
Sustainability, FinTech, Hardware, Healthcare & Biotech, Healthy Food & Nutrition, Industrial
Automation, Internet of Things, Nanotechnology, Quantum Computing, Real Estate & REITs, Robotics,
Semiconductors, Smart Home, Social Media, Software, Space Tech, Telecommunications, Transportation
& Logistics, Virtual & Augmented Reality, Wearables.

Pass the bare slug (lowercased, no spaces/punctuation), e.g. `artificialintelligence`, `cybersecurity`.

## Sub-themes (Elite-only — `--subthemes`)

Sub-themes drill into a theme (e.g. "AI - Cloud & Infrastructure", "Cybersecurity - Zero Trust").
**Confirmed during testing:** this filter requires a FinViz Elite subscription — on the Public tier
FinViz shows "The Sub-theme filter is an Elite subscription feature" and drops it from the applied
filter set without erroring. Only use `--subthemes` when the user has confirmed Elite access
(`--elite` flag or `$FINVIZ_API_KEY` set).
