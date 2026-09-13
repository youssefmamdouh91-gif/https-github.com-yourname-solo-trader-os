# Thesis YAML Schema

One YAML file per trade idea, stored at `state/theses/th_<TICKER>_<YYYYMMDD>_<seq>.yaml`
(or under a caller-provided `--state-dir`). This is the shared contract every
other skill in the repo reads directly — do not change field names or the
`th_*.yaml` filename glob without updating every consumer:

- `drawdown-circuit-breaker` — reads `status_history[].realized_pnl`/`.at`,
  `status`, `exit.actual_date`, `outcome.pnl_dollars`
- `pre-trade-discipline-gate` — reads theses for recent-loss checks, and
  imports this module directly (`scripts/thesis_store.py`) to call `link_report`
- `weekly-performance-digest` — reads `status_history` trims, `outcome.*`,
  `entry.actual_price`, `exit.stop_loss`, `position.shares`, `thesis_type`,
  `origin.skill`, `market_context.sector`, `mechanism_tag`, `lessons_learned`
- `trade-performance-coach` — reads closed theses for process/behavior review

## Top-level fields

| Field | Type | Set by | Notes |
|---|---|---|---|
| `thesis_id` | str | `new_thesis` | `th_<TICKER>_<YYYYMMDD>_<seq3>`, matches the filename stem |
| `ticker` | str | `new_thesis` | Upper-cased |
| `status` | str | lifecycle calls | `IDEA` \| `ENTRY_READY` \| `ACTIVE` \| `PARTIALLY_CLOSED` \| `CLOSED` \| `INVALIDATED` |
| `thesis_type` | str \| null | `new_thesis` | Free text, e.g. `vcp_breakout`, `dividend_value` |
| `mechanism_tag` | str \| null | `new_thesis` | Short causal tag used for pattern analysis in weekly-performance-digest |
| `lessons_learned` | str \| null | `close_thesis` / `invalidate_thesis` | Free text postmortem note |

## `origin`

| Field | Notes |
|---|---|
| `skill` | The skill that generated this idea (e.g. `vcp-screener`). Read by weekly-performance-digest's `by_source_skill` breakdown. |
| `screening_grade` | e.g. `A+`. Read by `by_screening_grade` breakdown. |

## `plan`

Written-plan checklist fields, set via `entry-ready`. Consumed by
pre-trade-discipline-gate style checklists (`entry_in_written_plan`,
`stop_predefined`, `size_within_plan` are the exact field names used
elsewhere as candidate-level checklist answers; here they're the thesis's
own record of the plan that was made *before* entry).

| Field | Type |
|---|---|
| `planned_entry` | float \| null |
| `planned_stop` | float \| null |
| `planned_target` | float \| null |
| `planned_risk_dollars` | float \| null |
| `entry_in_written_plan` | bool \| null |
| `stop_predefined` | bool \| null |
| `size_within_plan` | bool \| null |

## `entry`

| Field | Set by |
|---|---|
| `actual_price` | `record_entry` |
| `actual_date` | `record_entry` (ISO 8601, UTC if no tz given) |

## `position`

| Field | Notes |
|---|---|
| `shares` | Original total size at entry. **Never decremented by trims** — drawdown-circuit-breaker and weekly-performance-digest's R-multiple calculation use `(entry.actual_price - exit.stop_loss) * position.shares` as the *original* risk denominator. |
| `shares_open` | This module's own addition. Decremented by `record_trim`, zeroed by `close_thesis`/`invalidate_thesis`. No known consumer reads it yet. |
| `actual_risk_dollars` | Optional, informational. |

## `exit`

| Field | Notes |
|---|---|
| `actual_date` | Set by `close_thesis` / `invalidate_thesis` |
| `stop_loss` | **Lives under `exit`, not `entry`** — weekly-performance-digest's R-multiple calc explicitly reads `exit.stop_loss` |
| `exit_reason` | Free text, e.g. `target_hit`, `stop_hit`, `thesis_invalidated`, `time_stop`. Read by `by_exit_reason` breakdown. |

## `outcome`

| Field | Notes |
|---|---|
| `pnl_dollars` | Total realized P&L across the whole thesis (all trims + final leg), computed by `close_thesis`/`invalidate_thesis` |
| `pnl_pct` | `pnl_dollars / (entry.actual_price * position.shares) * 100` |
| `mae_pct` | Max adverse excursion. Convention: `<= 0`. Caller-supplied (this module does not compute it from price history). |
| `mfe_pct` | Max favorable excursion. Convention: `>= 0`. Caller-supplied. |
| `holding_days` | Explicit if set; weekly-performance-digest falls back to `exit.actual_date - entry.actual_date` if this is absent. This module always sets it explicitly on close. |

## `market_context`

| Field | Notes |
|---|---|
| `sector` | Read by `by_sector` breakdown |
| `market_regime` | Not currently written by any lifecycle call; set manually if needed |

## `monitoring`

| Field | Set by |
|---|---|
| `next_review_date` | `mark_reviewed` |
| `last_reviewed_at` | `mark_reviewed` |

**Never called by pre-trade-discipline-gate** — checklist logging must not
advance monitoring review dates (see that skill's SKILL.md).

## `linked_reports`

List of `{source_skill, report_path, report_date, linked_at}`, appended by
`link_report`. Used to trace which generated reports (e.g. a pre-trade
discipline JSON report) relate to a given thesis.

## `status_history`

Append-only ledger. Every lifecycle call appends exactly one event.

| Field | Present on |
|---|---|
| `status` | always |
| `at` | always (ISO 8601) |
| `note` | always (may be null) |
| `shares_sold`, `price`, `proceeds`, `realized_pnl` | only on `PARTIALLY_CLOSED` (trim) events |

`drawdown-circuit-breaker` sums `realized_pnl` across `status_history` events
for daily/weekly/monthly drawdown accounting — every trim **must** carry a
finite `realized_pnl`, which `record_trim` always computes and sets.

## `_index.json`

A generated (not hand-edited) lightweight lookup file at
`state/theses/_index.json`, rebuilt on every write. Maps `thesis_id` to
`{ticker, status, thesis_type, path}`. **Never used for P&L or ledger data**
by any consumer — it exists purely for fast listing/lookup.
