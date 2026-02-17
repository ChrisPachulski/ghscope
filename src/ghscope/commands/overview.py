"""Combined scorecard — synthesized intelligence from all reports."""

from __future__ import annotations

from rich.console import Console
from rich.status import Status

from ghscope.cli import GhscopeContext
from ghscope.display.json_out import print_json

console = Console()


def _fetch_all_reports(ctx: GhscopeContext):
    """Fetch all 4 reports, returning None for any that fail."""
    triage = contribs = review = health = None

    try:
        from ghscope.commands.triage import fetch_triage_data
        triage = fetch_triage_data(ctx)
    except Exception:
        pass

    try:
        from ghscope.commands.contribs import fetch_contribs_report
        contribs = fetch_contribs_report(ctx)
    except Exception:
        pass

    try:
        from ghscope.commands.review import fetch_review_report
        review = fetch_review_report(ctx)
    except Exception:
        pass

    try:
        from ghscope.commands.health import fetch_health_report
        health = fetch_health_report(ctx)
    except Exception:
        pass

    return triage, contribs, review, health


def run_overview(ctx: GhscopeContext) -> None:
    """Full repository scorecard — synthesized from all reports."""
    with Status(f"Building scorecard for {ctx.repo}...", console=console):
        triage, contribs, review, health = _fetch_all_reports(ctx)

    if ctx.json_output:
        result = {}
        if triage:
            result["triage"] = triage
        if contribs:
            result["contribs"] = contribs
        if review:
            result["review"] = review
        if health:
            result["health"] = health
        print_json(result)
    elif ctx.fmt in ("csv", "parquet"):
        from ghscope.frames import scorecard_frame, export_tables
        table = scorecard_frame(triage, contribs, review, health)
        export_tables({"scorecard": table}, ctx.fmt)
    elif ctx.fmt == "rich":
        from ghscope.display.tables import display_overview
        display_overview(ctx.repo, {}, triage, health)
    else:
        import polars as pl
        from ghscope.frames import scorecard_frame
        table = scorecard_frame(triage, contribs, review, health)
        print(f"\n=== {ctx.repo} SCORECARD ===")
        with pl.Config(tbl_width_chars=120, fmt_str_lengths=80, tbl_rows=-1):
            print(table.to_polars())
        print()
