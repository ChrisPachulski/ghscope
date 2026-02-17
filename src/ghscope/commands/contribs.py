"""Contributor dynamics, spam detection."""

from __future__ import annotations

from rich.console import Console
from rich.status import Status

from ghscope.cli import GhscopeContext
from ghscope.core.analysis import (
    compute_contributor_stats, detect_spam_prs, parse_pr_node,
)
from ghscope.core.models import ContributorReport, PRSummary
from ghscope.core.queries import CLOSED_PRS_PAGE, MERGED_PRS_PAGE, OPEN_PRS_PAGE
from ghscope.display.json_out import print_json
from ghscope.display.tables import display_contribs

console = Console()


def run_contribs(ctx: GhscopeContext) -> None:
    from ghscope.commands.triage import _fetch_pr_data

    with Status(f"Analyzing contributors for {ctx.repo}...", console=console):
        merged = _fetch_pr_data(ctx, "MERGED", MERGED_PRS_PAGE, "merged_prs")
        closed = _fetch_pr_data(ctx, "CLOSED", CLOSED_PRS_PAGE, "closed_prs")
        open_prs = _fetch_pr_data(ctx, "OPEN", OPEN_PRS_PAGE, "open_prs")

        all_prs = merged + closed + open_prs
        contrib_stats = compute_contributor_stats(merged, closed, open_prs)
        spam = detect_spam_prs(all_prs)

        repeat = sum(1 for c in contrib_stats if c.merged_count >= 2)
        one_time = sum(1 for c in contrib_stats if c.merged_count == 1)

        report = ContributorReport(
            repo=ctx.repo,
            total_contributors=len(contrib_stats),
            top_contributors=contrib_stats,
            repeat_contributors=repeat,
            one_time_contributors=one_time,
            spam_prs=spam,
        )

    if ctx.json_output:
        print_json(report)
    else:
        display_contribs(report)
