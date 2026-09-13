---
name: trader-memory-core
description: The shared trade journal and state store for solo-trader OS. Records a trade idea's full lifecycle (IDEA -> ENTRY_READY -> ACTIVE -> PARTIALLY_CLOSED -> CLOSED/INVALIDATED) as one YAML file per thesis under state/theses/, which drawdown-circuit-breaker, pre-trade-discipline-gate, weekly-performance-digest, and trade-performance-coach all read directly. Use when the user wants to log a new trade idea, record an actual entry fill, record a partial exit (trim), close or invalidate a thesis, link a report to a thesis, or query past theses.
---

# Trader Memory Core

> **Reconstructed, not recovered.** This skill did not exist among the files
> shared with the assistant — it was inferred entirely from how every other
> skill in this repo (drawdown-circuit-breaker, pre-trade-discipline-gate,
> weekly-performance-digest, trade-hypothesis-ideator's recommended pairing,
> trade-performance-coach) already reads and imports it. The consumer
> contract (directory, filenames, field names, and the exact
> `scripts/thesis_store.py` module path with a `link_report(state_dir,
> thesis_id, source_skill, report_path, report_date)` function) is matched
> precisely because those consumer scripts hard-code it. The *implementation*
> behind that contract (exact P&L math, validation strictness, CLI ergonomics)
> is this assistant's own design and has not been tested against the
> original repo's test suite. See `references/thesis_schema.md` for the full
> field-by-field contract and known simplifications.

## Overview

Every trade idea, from first screen to final exit, is one YAML file under a
shared `state/theses/` directory (default; override with `--state-dir`).
This skill is the only thing that should ever *write* those files — every
other skill in the repo reads them directly with `state_dir.glob("th_*.yaml")`.

## When to Use

- User wants to log a new trade idea / candidate as a journaled thesis
- User has an actual fill to record (entry price, shares)
- User took a partial profit or scaled out of a position (a "trim")
- User closed or invalidated a trade thesis and wants the outcome recorded
- Another skill (e.g. pre-trade-discipline-gate) needs to link its generated
  report to a thesis
- User asks to list or review past/open theses

## Workflow

### Step 1: Create the idea

```bash
python3 skills/trader-memory-core/scripts/thesis_store.py new \
  --ticker AAPL \
  --thesis-type vcp_breakout \
  --mechanism-tag technical-breakout \
  --origin-skill vcp-screener \
  --screening-grade "A" \
  --planned-entry 232.50 --planned-stop 224.00 --planned-target 260.00 \
  --planned-risk-dollars 400 \
  --sector Technology \
  --note "Textbook VCP, pivot confirmed on volume"
```

Prints the new `thesis_id` (e.g. `th_AAPL_20260913_001`) — capture it for
every subsequent call.

### Step 2: Confirm the written plan (optional but recommended before entry)

```bash
python3 skills/trader-memory-core/scripts/thesis_store.py entry-ready \
  --thesis-id th_AAPL_20260913_001 \
  --entry-in-written-plan --stop-predefined --size-within-plan
```

### Step 3: Record the actual fill

```bash
python3 skills/trader-memory-core/scripts/thesis_store.py enter \
  --thesis-id th_AAPL_20260913_001 \
  --price 233.10 --shares 40 --risk-dollars 380
```

### Step 4 (as needed): Record a partial exit

```bash
python3 skills/trader-memory-core/scripts/thesis_store.py trim \
  --thesis-id th_AAPL_20260913_001 \
  --shares-sold 15 --price 248.00 \
  --note "Trimmed at first resistance"
```

Each trim appends a `status_history` event carrying `shares_sold`, `price`,
`proceeds`, and `realized_pnl` — this is the ledger
`drawdown-circuit-breaker` sums for daily/weekly/monthly drawdown accounting.

### Step 5: Close or invalidate

```bash
# Normal exit
python3 skills/trader-memory-core/scripts/thesis_store.py close \
  --thesis-id th_AAPL_20260913_001 \
  --price 255.00 --stop-loss 224.00 --exit-reason target_hit \
  --mae-pct -1.2 --mfe-pct 9.8 \
  --lessons-learned "Held through the pullback per plan; worked."

# Thesis broke before or without a full exit price history
python3 skills/trader-memory-core/scripts/thesis_store.py invalidate \
  --thesis-id th_AAPL_20260913_001 \
  --reason "Broke below the base on heavy volume before entry" \
  --price 226.00
```

Omit `--price` on `invalidate` only if the thesis never reached `ACTIVE`
(no open position to close out).

### Other operations

```bash
# List all open theses
python3 skills/trader-memory-core/scripts/thesis_store.py list --status ACTIVE

# Show one thesis as JSON
python3 skills/trader-memory-core/scripts/thesis_store.py show --thesis-id th_AAPL_20260913_001

# Attach a report to a thesis (used internally by pre-trade-discipline-gate)
python3 skills/trader-memory-core/scripts/thesis_store.py link-report \
  --thesis-id th_AAPL_20260913_001 \
  --source-skill pre-trade-discipline-gate \
  --report-path reports/pre-trade-discipline/2026-09-13.json \
  --report-date 2026-09-13

# Advance a thesis's monitoring review date (never call this from a
# pre-trade checklist — see pre-trade-discipline-gate's SKILL.md)
python3 skills/trader-memory-core/scripts/thesis_store.py mark-reviewed \
  --thesis-id th_AAPL_20260913_001 --next-review-date 2026-09-20
```

## Cross-skill integration

`pre-trade-discipline-gate` loads this exact file directly via
`importlib.util.spec_from_file_location` at
`skills/trader-memory-core/scripts/thesis_store.py` to call `link_report` —
the module path and that function's positional-argument order
(`state_dir, thesis_id, source_skill, report_path, report_date`) must not
change without updating that skill too.

## Resources

- `scripts/thesis_store.py` — the read/write library and CLI (importable; see docstring)
- `references/thesis_schema.md` — full field-by-field schema contract and design notes
