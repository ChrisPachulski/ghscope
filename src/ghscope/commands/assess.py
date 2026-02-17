"""User's open PRs, merge probability, similar PRs."""

from __future__ import annotations

from rich.console import Console
from rich.status import Status

from ghscope.cli import GhscopeContext
from ghscope.core import cache
from ghscope.core.analysis import (
    compute_merge_probability, find_similar_prs, parse_pr_node,
)
from ghscope.core.github import get_viewer_login, graphql, paginated_query
from ghscope.core.models import AssessmentReport, PRAssessment, PRSummary
from ghscope.core.queries import CLOSED_PRS_PAGE, MERGED_PRS_PAGE, USER_OPEN_PRS
from ghscope.display.json_out import print_json
from ghscope.display.tables import display_assess

console = Console()


def _fetch_user_open_prs(ctx: GhscopeContext, user: str) -> list[PRSummary]:
    """Fetch user's open PRs in the repo."""
    cache_key = f"user_open_prs_{user}"
    if not ctx.no_cache:
        if ctx.offline:
            cached = cache.get_offline(ctx.repo, cache_key)
        else:
            cached = cache.get(ctx.repo, cache_key)
        if cached is not None:
            return [parse_pr_node(n, "OPEN") for n in cached]

    if ctx.offline:
        return []

    query_str = f"repo:{ctx.repo} author:{user} is:pr is:open"
    data = graphql(USER_OPEN_PRS, {"searchQuery": query_str})
    nodes = data.get("search", {}).get("nodes", [])
    # Filter to actual PRs (search can return other types)
    pr_nodes = [n for n in nodes if n.get("number")]
    cache.put(ctx.repo, cache_key, pr_nodes)
    return [parse_pr_node(n, "OPEN") for n in pr_nodes]


def _fetch_historical(ctx: GhscopeContext) -> tuple[list[PRSummary], list[PRSummary]]:
    """Fetch merged and closed PRs for comparison."""
    from ghscope.commands.triage import _fetch_pr_data
    merged = _fetch_pr_data(ctx, "MERGED", MERGED_PRS_PAGE, "merged_prs")
    closed = _fetch_pr_data(ctx, "CLOSED", CLOSED_PRS_PAGE, "closed_prs")
    return merged, closed


def fetch_assess_report(ctx: GhscopeContext) -> AssessmentReport:
    """Fetch and compute assessment report."""
    user = get_viewer_login()
    user_prs = _fetch_user_open_prs(ctx, user)
    merged, closed = _fetch_historical(ctx)

    assessments = []
    for pr in user_prs:
        prob, factors = compute_merge_probability(pr, merged, closed)
        sim_merged = find_similar_prs(pr, merged)
        sim_closed = find_similar_prs(pr, closed)
        assessments.append(PRAssessment(
            pr=pr, probability=prob, factors=factors,
            similar_merged=sim_merged, similar_closed=sim_closed,
        ))

    assessments.sort(key=lambda a: a.probability, reverse=True)
    return AssessmentReport(repo=ctx.repo, user=user, assessments=assessments)


def run_assess(ctx: GhscopeContext) -> None:
    with Status(f"Assessing PRs for {ctx.repo}...", console=console):
        report = fetch_assess_report(ctx)

    if ctx.json_output:
        print_json(report)
    elif ctx.fmt == "rich":
        display_assess(report)
    elif ctx.fmt in ("csv", "parquet"):
        from ghscope.frames import assess_frames, export_tables
        export_tables(assess_frames(report), ctx.fmt)
    else:
        from ghscope.frames import assess_frames, display_polars
        display_polars(assess_frames(report))
