# solo-trader OS

A personal, semi-automated trading-operations system: a library of single-purpose
skills (screeners, risk gates, journaling, coaching) wired together by workflow
manifests in [`workflows/`](workflows/). See [`workflows/README.md`](workflows/README.md)
for the full workflow schema and how manifests are validated.

**Status:** reconstruction in progress. This repo is being rebuilt from files
recovered piecemeal, so this README doubles as a honest progress tracker —
update it as pieces come back.

## Skills present (`skills/`)

| Skill | Complete? | Notes |
|---|---|---|
| finviz-screener | Yes | Patched (Windows Chrome support, Elite sub-theme warning); best-effort filter reference reconstructed |
| us-swing-trade-hunter | Yes | Frontmatter added; rest was already self-contained |
| downtrend-duration-analyzer | Yes | Complete package as received |
| breakout-trade-planner | Yes | Complete package as received; verified it only builds Alpaca order templates, never places live orders |
| value-dividend-screener | Yes | Complete; needs FINVIZ Elite + FMP API keys |
| uptrend-analyzer | Yes | Complete; no API key needed |
| trade-performance-coach | Yes | Complete; depends on trader-memory-core for input data |
| trade-hypothesis-ideator | Yes | Complete |
| scenario-analyzer | Yes | Complete |
| pre-trade-discipline-gate | Yes | Complete; verified end-to-end against a live trader-memory-core thesis, including the `link_report` cross-import |
| market-news-analyst | Yes | Complete — supersedes an earlier incomplete copy (SKILL.md + failing test, missing all 4 references) |
| market-breadth-analyzer | Yes | Complete; no API key (public TraderMonty CSV) |
| market-environment-analysis | Yes | Complete |
| economic-calendar-fetcher | Yes | Complete; needs FMP API key |
| drawdown-circuit-breaker | Yes | Complete; verified end-to-end against a live trader-memory-core thesis (full IDEA→CLOSED lifecycle, ledger P&L reconciliation) |
| crypto-regime-analyzer | Yes | Complete; no API key (CoinGecko + Binance, free) |
| weekly-performance-digest | Yes | Complete; verified end-to-end against a live trader-memory-core thesis |
| **trader-memory-core** | Yes | **Reconstructed from scratch** (not recovered — no source file existed for it). Inferred the full contract by reading every consumer script's `.get()` calls, glob patterns, and the exact `importlib` module path pre-trade-discipline-gate uses for `link_report`. Verified end-to-end: full thesis lifecycle (IDEA→ENTRY_READY→ACTIVE→PARTIALLY_CLOSED→CLOSED) produces output that drawdown-circuit-breaker, weekly-performance-digest, and pre-trade-discipline-gate all accept with zero warnings. See its SKILL.md for the "reconstructed, not recovered" caveat and `references/thesis_schema.md` for the full field contract. |
| vcp-screener | **Partial** | 6 of ~14 files recovered: `screen_vcp.py` (orchestrator), `scorer.py`, `report_generator.py`, `historical_scanner.py`, `fmp_client.py`, `_fmp_compat.py` — confirmed to be the real implementation, not reconstructed. Still missing: the `calculators/` package (8 files — this is where the actual VCP pattern-detection math lives: contraction depths, Stage-2 trend-template scoring, etc.), `historical_report.py`, and 3 reference docs. `python3 screen_vcp.py` currently fails with `ModuleNotFoundError: No module named 'calculators'` (confirmed by running it). The `calculators/` package is deliberately *not* being reconstructed like trader-memory-core was — it's specific quantitative pattern-detection math that the SKILL.md only describes at a high level; guessing at the actual thresholds risks silently wrong screening results. |

## Skills referenced but not yet recovered

Named in workflow manifests or the skills index but no content received yet:

- `signal-postmortem`
- `backtest-expert`
- `exposure-coach`
- `portfolio-manager`
- `kanchi-dividend-review-monitor`
- `position-sizer`
- `macro-regime-detector`
- `theme-detector`
- `stockbee-episodic-pivot-analyzer`
- `stockbee-20pct-study`
- `stockbee-setup-fluency-trainer`
- `cot-contrarian-detector`
- `news-reaction-failure-analyzer`
- `technical-analyst`
- `contrarian-setup-gate`
- `futures-position-sizer`
- `kanchi-dividend-sop`
- `dividend-growth-pullback-screener`
- `stockbee-momentum-burst-screener`
- `stockbee-exhaustion-hammer-screener`
- `canslim-screener`

## Workflows present (`workflows/`)

- `README.md` — the canonical schema/index doc
- `swing-opportunity-daily.yaml` — present, but 3 of its 6 required skills are still missing (`vcp-screener` incomplete; `technical-analyst`, `position-sizer` not recovered). `trader-memory-core` and `drawdown-circuit-breaker` and `pre-trade-discipline-gate` are now ready.

## Workflows referenced but not yet recovered

Per `workflows/README.md`'s table, 9 more manifests exist in the original repo:
`market-regime-daily.yaml`, `core-portfolio-weekly.yaml`, `multi-asset-opportunity-daily.yaml`,
`stockbee-ep-daily.yaml`, `stockbee-20pct-study-daily.yaml`, `stockbee-fluency-loop.yaml`,
`trade-memory-loop.yaml`, `monthly-performance-review.yaml`, `shapiro-contrarian.yaml`,
`kanchi-dividend-weekly.yaml`.

## Other referenced infrastructure not yet recovered

- `docs/dev/metadata-and-workflow-schema.md` — the schema doc `workflows/README.md` points to
- `scripts/validate_skills_index.py` — the validator (`--strict-workflows` flag, WF001-014 error codes)
- `skills_index.yaml` — placeholder created at repo root with the one entry received so far (`trade-memory`); real filename/structure unconfirmed
