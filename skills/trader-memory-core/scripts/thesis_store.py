#!/usr/bin/env python3
"""
trader-memory-core / thesis_store — the shared trade-journal state store.

This module is both a library (imported directly by sibling skills, e.g.
pre-trade-discipline-gate loads this exact file via importlib to call
``link_report``) and a CLI for recording a trade thesis's lifecycle.

Every trade idea in solo-trader OS is one YAML file under a shared
``state/theses/`` directory, named ``th_<TICKER>_<YYYYMMDD>_<seq>.yaml``.
Every other skill in the repo (drawdown-circuit-breaker, pre-trade-discipline-
gate, weekly-performance-digest, trade-performance-coach) reads these files
directly with a plain ``state_dir.glob("th_*.yaml")`` — this module is the
only thing that should ever write them, so the schema stays consistent.

Schema (see references/thesis_schema.md for the full field-by-field contract):

    thesis_id: th_AAPL_20260913_001
    ticker: AAPL
    status: IDEA | ENTRY_READY | ACTIVE | PARTIALLY_CLOSED | CLOSED | INVALIDATED
    thesis_type: str | null
    mechanism_tag: str | null
    origin: {skill: str | null, screening_grade: str | null}
    plan: {planned_entry, planned_stop, planned_target, planned_risk_dollars,
           entry_in_written_plan, stop_predefined, size_within_plan}
    entry: {actual_price: float | null, actual_date: iso8601 | null}
    position: {shares: int | null, shares_open: int | null, actual_risk_dollars: float | null}
    exit: {actual_date, stop_loss, exit_reason}
    outcome: {pnl_dollars, pnl_pct, mae_pct, mfe_pct, holding_days}
    market_context: {sector, market_regime}
    monitoring: {next_review_date, last_reviewed_at}
    linked_reports: [{source_skill, report_path, report_date, linked_at}]
    status_history: [{status, at, note, shares_sold, price, proceeds, realized_pnl}]
    lessons_learned: str | null

Design notes / known simplifications versus the original repo (documented
here because this module was reconstructed from the consumer contract, not
recovered):

- Long-only P&L math (``(price - entry_price) * shares``). Short theses are
  not specially handled.
- ``position.shares`` is the ORIGINAL total size at entry and never changes
  on a trim (drawdown-circuit-breaker / weekly-performance-digest use it as
  the R-multiple risk denominator, which must reflect the original planned
  risk, not the remaining open size). ``position.shares_open`` is this
  module's own addition tracking what is still open; no consumer currently
  reads it, so it's safe to have added.
- Duplicate-thesis-id detection, malformed-ledger detection, etc. described
  in drawdown-circuit-breaker's circuit_breaker_framework.md are the
  *readers'* defensive validation. This writer always emits well-formed
  records, so that validation should never trigger against files produced
  by this module — but it hasn't been tested against the original repo's
  test suite, since that suite was not recovered either.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

TERMINAL_STATUSES = {"CLOSED", "INVALIDATED"}
THESIS_STATUSES = {"IDEA", "ENTRY_READY", "ACTIVE", "PARTIALLY_CLOSED", *TERMINAL_STATUSES}


class ThesisStoreError(ValueError):
    """Raised for any invalid operation against the thesis store."""


# --------------------------------------------------------------------------- #
# Path / IO helpers
# --------------------------------------------------------------------------- #
def _ensure_state_dir(state_dir: Path) -> Path:
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _thesis_path(state_dir: Path, thesis_id: str) -> Path:
    return Path(state_dir) / f"{thesis_id}.yaml"


def _now_iso(as_of: datetime | None = None) -> str:
    dt = as_of or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _load_raw(state_dir: Path, thesis_id: str) -> dict[str, Any]:
    path = _thesis_path(state_dir, thesis_id)
    if not path.is_file():
        raise ThesisStoreError(f"No thesis found for id {thesis_id!r} at {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ThesisStoreError(f"Thesis file is not a YAML mapping: {path}")
    return data


def _write_raw(state_dir: Path, thesis_id: str, data: dict[str, Any]) -> Path:
    path = _thesis_path(state_dir, thesis_id)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    _rebuild_index(state_dir)
    return path


def _next_sequence(state_dir: Path, ticker: str, day: str) -> int:
    prefix = f"th_{ticker}_{day}_"
    existing = sorted(Path(state_dir).glob(f"{prefix}*.yaml"))
    seqs = []
    for p in existing:
        tail = p.stem[len(prefix) :]
        if tail.isdigit():
            seqs.append(int(tail))
    return (max(seqs) + 1) if seqs else 1


def _rebuild_index(state_dir: Path) -> None:
    """Write the lightweight `_index.json` lookup index.

    NOTE (per circuit_breaker_framework.md): this index is a convenience
    lookup only. No consumer should ever use it for P&L or ledger data —
    they read the full `th_*.yaml` files directly for that.
    """
    state_dir = Path(state_dir)
    index: dict[str, Any] = {}
    for path in sorted(state_dir.glob("th_*.yaml")):
        try:
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue
        thesis_id = data.get("thesis_id") or path.stem
        index[thesis_id] = {
            "ticker": data.get("ticker"),
            "status": data.get("status"),
            "thesis_type": data.get("thesis_type"),
            "path": path.name,
        }
    index_path = state_dir / "_index.json"
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, sort_keys=True)


# --------------------------------------------------------------------------- #
# Lifecycle: create
# --------------------------------------------------------------------------- #
def new_thesis(
    state_dir: Path,
    ticker: str,
    *,
    thesis_type: str | None = None,
    mechanism_tag: str | None = None,
    origin_skill: str | None = None,
    screening_grade: str | None = None,
    planned_entry: float | None = None,
    planned_stop: float | None = None,
    planned_target: float | None = None,
    planned_risk_dollars: float | None = None,
    sector: str | None = None,
    note: str | None = None,
    as_of: datetime | None = None,
) -> str:
    """Create a new IDEA-status thesis. Returns the new thesis_id."""
    state_dir = _ensure_state_dir(state_dir)
    ticker = ticker.strip().upper()
    if not ticker:
        raise ThesisStoreError("ticker is required")
    day = (as_of or datetime.now(timezone.utc)).date().isoformat().replace("-", "")
    seq = _next_sequence(state_dir, ticker, day)
    thesis_id = f"th_{ticker}_{day}_{seq:03d}"

    timestamp = _now_iso(as_of)
    data: dict[str, Any] = {
        "thesis_id": thesis_id,
        "ticker": ticker,
        "status": "IDEA",
        "thesis_type": thesis_type,
        "mechanism_tag": mechanism_tag,
        "origin": {"skill": origin_skill, "screening_grade": screening_grade},
        "plan": {
            "planned_entry": planned_entry,
            "planned_stop": planned_stop,
            "planned_target": planned_target,
            "planned_risk_dollars": planned_risk_dollars,
            "entry_in_written_plan": None,
            "stop_predefined": None,
            "size_within_plan": None,
        },
        "entry": {"actual_price": None, "actual_date": None},
        "position": {"shares": None, "shares_open": None, "actual_risk_dollars": None},
        "exit": {"actual_date": None, "stop_loss": None, "exit_reason": None},
        "outcome": {
            "pnl_dollars": None,
            "pnl_pct": None,
            "mae_pct": None,
            "mfe_pct": None,
            "holding_days": None,
        },
        "market_context": {"sector": sector, "market_regime": None},
        "monitoring": {"next_review_date": None, "last_reviewed_at": None},
        "linked_reports": [],
        "status_history": [{"status": "IDEA", "at": timestamp, "note": note}],
        "lessons_learned": None,
    }
    _write_raw(state_dir, thesis_id, data)
    return thesis_id


# --------------------------------------------------------------------------- #
# Lifecycle: transitions
# --------------------------------------------------------------------------- #
def set_entry_ready(
    state_dir: Path,
    thesis_id: str,
    *,
    entry_in_written_plan: bool,
    stop_predefined: bool,
    size_within_plan: bool,
    note: str | None = None,
    as_of: datetime | None = None,
) -> None:
    data = _load_raw(state_dir, thesis_id)
    if data.get("status") not in {"IDEA", "ENTRY_READY"}:
        raise ThesisStoreError(
            f"Cannot mark {thesis_id} ENTRY_READY from status {data.get('status')!r}"
        )
    data["status"] = "ENTRY_READY"
    plan = data.setdefault("plan", {})
    plan["entry_in_written_plan"] = bool(entry_in_written_plan)
    plan["stop_predefined"] = bool(stop_predefined)
    plan["size_within_plan"] = bool(size_within_plan)
    data.setdefault("status_history", []).append(
        {"status": "ENTRY_READY", "at": _now_iso(as_of), "note": note}
    )
    _write_raw(state_dir, thesis_id, data)


def record_entry(
    state_dir: Path,
    thesis_id: str,
    *,
    actual_price: float,
    shares: int,
    actual_risk_dollars: float | None = None,
    actual_date: datetime | None = None,
    note: str | None = None,
) -> None:
    data = _load_raw(state_dir, thesis_id)
    if data.get("status") in TERMINAL_STATUSES:
        raise ThesisStoreError(f"Cannot enter a terminal thesis {thesis_id}")
    data["status"] = "ACTIVE"
    data["entry"] = {
        "actual_price": float(actual_price),
        "actual_date": _now_iso(actual_date),
    }
    data["position"] = {
        "shares": int(shares),
        "shares_open": int(shares),
        "actual_risk_dollars": actual_risk_dollars,
    }
    data.setdefault("status_history", []).append(
        {"status": "ACTIVE", "at": _now_iso(actual_date), "note": note}
    )
    _write_raw(state_dir, thesis_id, data)


def record_trim(
    state_dir: Path,
    thesis_id: str,
    *,
    shares_sold: int,
    price: float,
    at: datetime | None = None,
    note: str | None = None,
) -> float:
    """Record a partial exit. Returns the realized P&L for this trim."""
    data = _load_raw(state_dir, thesis_id)
    if data.get("status") not in {"ACTIVE", "PARTIALLY_CLOSED"}:
        raise ThesisStoreError(f"Cannot trim thesis {thesis_id} from status {data.get('status')!r}")
    entry_price = (data.get("entry") or {}).get("actual_price")
    if entry_price is None:
        raise ThesisStoreError(f"Thesis {thesis_id} has no entry.actual_price to trim against")
    position = data.setdefault("position", {})
    shares_open = position.get("shares_open")
    if shares_open is None:
        shares_open = position.get("shares")
    if shares_open is None or shares_sold > shares_open:
        raise ThesisStoreError(
            f"Cannot trim {shares_sold} shares of {thesis_id}; only {shares_open} open"
        )
    proceeds = round(price * shares_sold, 4)
    realized_pnl = round((price - entry_price) * shares_sold, 4)
    position["shares_open"] = shares_open - shares_sold
    data["status"] = "PARTIALLY_CLOSED"
    data.setdefault("status_history", []).append(
        {
            "status": "PARTIALLY_CLOSED",
            "at": _now_iso(at),
            "note": note,
            "shares_sold": int(shares_sold),
            "price": float(price),
            "proceeds": proceeds,
            "realized_pnl": realized_pnl,
        }
    )
    _write_raw(state_dir, thesis_id, data)
    return realized_pnl


def close_thesis(
    state_dir: Path,
    thesis_id: str,
    *,
    exit_price: float,
    stop_loss: float | None,
    exit_reason: str,
    mae_pct: float | None = None,
    mfe_pct: float | None = None,
    lessons_learned: str | None = None,
    exit_date: datetime | None = None,
    note: str | None = None,
) -> float:
    """Close the remaining open position. Returns total pnl_dollars for the thesis."""
    data = _load_raw(state_dir, thesis_id)
    if data.get("status") in TERMINAL_STATUSES:
        raise ThesisStoreError(f"Thesis {thesis_id} is already terminal")
    entry = data.get("entry") or {}
    entry_price = entry.get("actual_price")
    if entry_price is None:
        raise ThesisStoreError(f"Thesis {thesis_id} has no entry.actual_price to close against")
    position = data.setdefault("position", {})
    shares_open = position.get("shares_open", position.get("shares", 0)) or 0
    total_shares = position.get("shares") or shares_open

    final_leg_pnl = round((exit_price - entry_price) * shares_open, 4) if shares_open else 0.0
    prior_realized = sum(
        event.get("realized_pnl", 0.0) or 0.0
        for event in data.get("status_history", [])
        if event.get("status") == "PARTIALLY_CLOSED"
    )
    pnl_dollars = round(prior_realized + final_leg_pnl, 4)
    pnl_pct = (
        round(pnl_dollars / (entry_price * total_shares) * 100, 4)
        if entry_price and total_shares
        else None
    )
    entry_date = entry.get("actual_date")
    holding_days = None
    exit_date_iso = _now_iso(exit_date)
    if entry_date:
        try:
            holding_days = (
                datetime.fromisoformat(exit_date_iso) - datetime.fromisoformat(entry_date)
            ).days
        except ValueError:
            holding_days = None

    position["shares_open"] = 0
    data["exit"] = {
        "actual_date": exit_date_iso,
        "stop_loss": stop_loss,
        "exit_reason": exit_reason,
    }
    data["outcome"] = {
        "pnl_dollars": pnl_dollars,
        "pnl_pct": pnl_pct,
        "mae_pct": mae_pct,
        "mfe_pct": mfe_pct,
        "holding_days": holding_days,
    }
    if lessons_learned:
        data["lessons_learned"] = lessons_learned
    data["status"] = "CLOSED"
    data.setdefault("status_history", []).append(
        {
            "status": "CLOSED",
            "at": exit_date_iso,
            "note": note,
            "shares_sold": int(shares_open),
            "price": float(exit_price),
            "proceeds": round(exit_price * shares_open, 4) if shares_open else 0.0,
            "realized_pnl": final_leg_pnl,
        }
    )
    _write_raw(state_dir, thesis_id, data)
    return pnl_dollars


def invalidate_thesis(
    state_dir: Path,
    thesis_id: str,
    *,
    reason: str,
    exit_price: float | None = None,
    exit_date: datetime | None = None,
    note: str | None = None,
) -> None:
    """Mark a thesis INVALIDATED. If a position was ever opened, exit_price is required
    to compute pnl_dollars; otherwise the thesis is closed out with no P&L impact."""
    data = _load_raw(state_dir, thesis_id)
    if data.get("status") in TERMINAL_STATUSES:
        raise ThesisStoreError(f"Thesis {thesis_id} is already terminal")
    entry = data.get("entry") or {}
    entry_price = entry.get("actual_price")
    exit_date_iso = _now_iso(exit_date)
    pnl_dollars = None
    event: dict[str, Any] = {"status": "INVALIDATED", "at": exit_date_iso, "note": note or reason}
    if entry_price is not None:
        if exit_price is None:
            raise ThesisStoreError(
                f"Thesis {thesis_id} has an open position; exit_price is required to invalidate"
            )
        position = data.setdefault("position", {})
        shares_open = position.get("shares_open", position.get("shares", 0)) or 0
        prior_realized = sum(
            event.get("realized_pnl", 0.0) or 0.0
            for event in data.get("status_history", [])
            if event.get("status") == "PARTIALLY_CLOSED"
        )
        final_leg_pnl = round((exit_price - entry_price) * shares_open, 4) if shares_open else 0.0
        pnl_dollars = round(prior_realized + final_leg_pnl, 4)
        position["shares_open"] = 0
        data["exit"] = {
            "actual_date": exit_date_iso,
            "stop_loss": (data.get("exit") or {}).get("stop_loss"),
            "exit_reason": "thesis_invalidated",
        }
        data["outcome"] = {**(data.get("outcome") or {}), "pnl_dollars": pnl_dollars}
        event.update(
            {
                "shares_sold": int(shares_open),
                "price": float(exit_price),
                "proceeds": round(exit_price * shares_open, 4) if shares_open else 0.0,
                "realized_pnl": final_leg_pnl,
            }
        )
    data["status"] = "INVALIDATED"
    data["lessons_learned"] = data.get("lessons_learned") or reason
    data.setdefault("status_history", []).append(event)
    _write_raw(state_dir, thesis_id, data)


# --------------------------------------------------------------------------- #
# Cross-skill integration points
# --------------------------------------------------------------------------- #
def link_report(
    state_dir: Path,
    thesis_id: str,
    source_skill: str,
    report_path: str,
    report_date: str,
) -> None:
    """Append a report reference to a thesis's linked_reports list.

    This exact signature is relied on by pre-trade-discipline-gate, which
    loads this file directly via importlib rather than importing it as a
    package — do not change the parameter order or names.
    """
    data = _load_raw(state_dir, thesis_id)
    data.setdefault("linked_reports", []).append(
        {
            "source_skill": source_skill,
            "report_path": report_path,
            "report_date": report_date,
            "linked_at": _now_iso(),
        }
    )
    _write_raw(state_dir, thesis_id, data)


def mark_reviewed(
    state_dir: Path,
    thesis_id: str,
    *,
    next_review_date: str | None = None,
    as_of: datetime | None = None,
) -> None:
    """Advance a thesis's monitoring review timestamps.

    Deliberately never called by pre-trade-discipline-gate (see its
    SKILL.md) — checklist logging must not advance monitoring review dates.
    """
    data = _load_raw(state_dir, thesis_id)
    monitoring = data.setdefault("monitoring", {})
    monitoring["last_reviewed_at"] = _now_iso(as_of)
    if next_review_date is not None:
        monitoring["next_review_date"] = next_review_date
    _write_raw(state_dir, thesis_id, data)


# --------------------------------------------------------------------------- #
# Read helpers
# --------------------------------------------------------------------------- #
def load_thesis(state_dir: Path, thesis_id: str) -> dict[str, Any]:
    return _load_raw(state_dir, thesis_id)


def list_theses(state_dir: Path, *, status: str | None = None) -> list[dict[str, Any]]:
    state_dir = Path(state_dir)
    if not state_dir.is_dir():
        return []
    results = []
    for path in sorted(state_dir.glob("th_*.yaml")):
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            continue
        if status is not None and data.get("status") != status:
            continue
        results.append(data)
    return results


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="trader-memory-core thesis store CLI")
    parser.add_argument("--state-dir", type=Path, default=Path("state/theses"))
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="Create a new IDEA thesis")
    p_new.add_argument("--ticker", required=True)
    p_new.add_argument("--thesis-type")
    p_new.add_argument("--mechanism-tag")
    p_new.add_argument("--origin-skill")
    p_new.add_argument("--screening-grade")
    p_new.add_argument("--planned-entry", type=float)
    p_new.add_argument("--planned-stop", type=float)
    p_new.add_argument("--planned-target", type=float)
    p_new.add_argument("--planned-risk-dollars", type=float)
    p_new.add_argument("--sector")
    p_new.add_argument("--note")

    p_ready = sub.add_parser("entry-ready", help="Mark a thesis ENTRY_READY")
    p_ready.add_argument("--thesis-id", required=True)
    p_ready.add_argument("--entry-in-written-plan", action="store_true")
    p_ready.add_argument("--stop-predefined", action="store_true")
    p_ready.add_argument("--size-within-plan", action="store_true")
    p_ready.add_argument("--note")

    p_enter = sub.add_parser("enter", help="Record the actual fill and activate the thesis")
    p_enter.add_argument("--thesis-id", required=True)
    p_enter.add_argument("--price", type=float, required=True)
    p_enter.add_argument("--shares", type=int, required=True)
    p_enter.add_argument("--risk-dollars", type=float)
    p_enter.add_argument("--date")
    p_enter.add_argument("--note")

    p_trim = sub.add_parser("trim", help="Record a partial exit")
    p_trim.add_argument("--thesis-id", required=True)
    p_trim.add_argument("--shares-sold", type=int, required=True)
    p_trim.add_argument("--price", type=float, required=True)
    p_trim.add_argument("--date")
    p_trim.add_argument("--note")

    p_close = sub.add_parser("close", help="Close the remaining position")
    p_close.add_argument("--thesis-id", required=True)
    p_close.add_argument("--price", type=float, required=True)
    p_close.add_argument("--stop-loss", type=float)
    p_close.add_argument("--exit-reason", required=True)
    p_close.add_argument("--mae-pct", type=float)
    p_close.add_argument("--mfe-pct", type=float)
    p_close.add_argument("--lessons-learned")
    p_close.add_argument("--date")
    p_close.add_argument("--note")

    p_inv = sub.add_parser("invalidate", help="Mark a thesis INVALIDATED")
    p_inv.add_argument("--thesis-id", required=True)
    p_inv.add_argument("--reason", required=True)
    p_inv.add_argument("--price", type=float)
    p_inv.add_argument("--date")
    p_inv.add_argument("--note")

    p_link = sub.add_parser("link-report", help="Attach a report path to a thesis")
    p_link.add_argument("--thesis-id", required=True)
    p_link.add_argument("--source-skill", required=True)
    p_link.add_argument("--report-path", required=True)
    p_link.add_argument("--report-date", required=True)

    p_review = sub.add_parser("mark-reviewed", help="Advance monitoring review timestamps")
    p_review.add_argument("--thesis-id", required=True)
    p_review.add_argument("--next-review-date")

    p_list = sub.add_parser("list", help="List theses, optionally filtered by status")
    p_list.add_argument("--status", choices=sorted(THESIS_STATUSES))

    p_show = sub.add_parser("show", help="Print one thesis as JSON")
    p_show.add_argument("--thesis-id", required=True)

    args = parser.parse_args(argv)

    try:
        if args.command == "new":
            thesis_id = new_thesis(
                args.state_dir,
                args.ticker,
                thesis_type=args.thesis_type,
                mechanism_tag=args.mechanism_tag,
                origin_skill=args.origin_skill,
                screening_grade=args.screening_grade,
                planned_entry=args.planned_entry,
                planned_stop=args.planned_stop,
                planned_target=args.planned_target,
                planned_risk_dollars=args.planned_risk_dollars,
                sector=args.sector,
                note=args.note,
            )
            print(thesis_id)
        elif args.command == "entry-ready":
            set_entry_ready(
                args.state_dir,
                args.thesis_id,
                entry_in_written_plan=args.entry_in_written_plan,
                stop_predefined=args.stop_predefined,
                size_within_plan=args.size_within_plan,
                note=args.note,
            )
        elif args.command == "enter":
            record_entry(
                args.state_dir,
                args.thesis_id,
                actual_price=args.price,
                shares=args.shares,
                actual_risk_dollars=args.risk_dollars,
                actual_date=_parse_date(args.date),
                note=args.note,
            )
        elif args.command == "trim":
            pnl = record_trim(
                args.state_dir,
                args.thesis_id,
                shares_sold=args.shares_sold,
                price=args.price,
                at=_parse_date(args.date),
                note=args.note,
            )
            print(f"realized_pnl: {pnl}")
        elif args.command == "close":
            pnl = close_thesis(
                args.state_dir,
                args.thesis_id,
                exit_price=args.price,
                stop_loss=args.stop_loss,
                exit_reason=args.exit_reason,
                mae_pct=args.mae_pct,
                mfe_pct=args.mfe_pct,
                lessons_learned=args.lessons_learned,
                exit_date=_parse_date(args.date),
                note=args.note,
            )
            print(f"pnl_dollars: {pnl}")
        elif args.command == "invalidate":
            invalidate_thesis(
                args.state_dir,
                args.thesis_id,
                reason=args.reason,
                exit_price=args.price,
                exit_date=_parse_date(args.date),
                note=args.note,
            )
        elif args.command == "link-report":
            link_report(
                args.state_dir,
                args.thesis_id,
                args.source_skill,
                args.report_path,
                args.report_date,
            )
        elif args.command == "mark-reviewed":
            mark_reviewed(args.state_dir, args.thesis_id, next_review_date=args.next_review_date)
        elif args.command == "list":
            for thesis in list_theses(args.state_dir, status=args.status):
                print(
                    f"{thesis.get('thesis_id')}\t{thesis.get('ticker')}\t"
                    f"{thesis.get('status')}\t{thesis.get('thesis_type')}"
                )
        elif args.command == "show":
            print(json.dumps(load_thesis(args.state_dir, args.thesis_id), indent=2, default=str))
    except ThesisStoreError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
