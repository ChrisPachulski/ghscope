"""Contributor dynamics, spam detection."""

from __future__ import annotations

from rich.console import Console
from rich.status import Status

from ghscope.cli import GhscopeContext
from ghscope.core.analysis import (
    compute_contributor_stats, compute_first_timer_stats,
    detect_spam_prs, parse_pr_node,
)
from ghscope.core.models import ContributorReport, PRSummary
from ghscope.core.queries import CLOSED_PRS_PAGE, MERGED_PRS_PAGE, OPEN_PRS_PAGE
from ghscope.display.json_out import print_json
from ghscope.display.tables import display_contribs

console = Console()


def fetch_contribs_report(ctx: GhscopeContext) -> ContributorReport:
    """Fetch and compute contributor report."""
    from ghscope.commands.triage import _fetch_pr_data

    merged = _fetch_pr_data(ctx, "MERGED", MERGED_PRS_PAGE, "merged_prs")
    closed = _fetch_pr_data(ctx, "CLOSED", CLOSED_PRS_PAGE, "closed_prs")
    open_prs = _fetch_pr_data(ctx, "OPEN", OPEN_PRS_PAGE, "open_prs")

    all_prs = merged + closed + open_prs
    contrib_stats = compute_contributor_stats(merged, closed, open_prs)
    spam = detect_spam_prs(all_prs)

    repeat = sum(1 for c in contrib_stats if c.merged_count >= 2)
    one_time = sum(1 for c in contrib_stats if c.merged_count == 1)

    ft = compute_first_timer_stats(contrib_stats, merged, days=ctx.days)

    return ContributorReport(
        repo=ctx.repo,
        total_contributors=len(contrib_stats),
        top_contributors=contrib_stats,
        repeat_contributors=repeat,
        one_time_contributors=one_time,
        spam_prs=spam,
        first_timers=ft["first_timers"],
        first_timer_merge_rate=ft["merge_rate"],
        first_timer_median_merge_hours=ft["median_merge_hours"],
        repeat_median_merge_hours=ft["repeat_median_hours"],
        retained_first_timers=ft["retained"],
        retention_rate=ft["retention_rate"],
    )


def run_contribs(ctx: GhscopeContext) -> None:
    with Status(f"Analyzing contributors for {ctx.repo}...", console=console):
        report = fetch_contribs_report(ctx)

    if ctx.fmt:
        from ghscope.frames import contribs_frames, export_tables
        export_tables(contribs_frames(report), ctx.fmt)
    elif ctx.json_output:
        print_json(report)
    else:
        display_contribs(report)
