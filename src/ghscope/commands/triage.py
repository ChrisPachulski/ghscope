"""PR volume, merge rates, merge times, batch detection."""

from __future__ import annotations

from rich.console import Console
from rich.status import Status

from ghscope.cli import GhscopeContext
from ghscope.core import cache
from ghscope.core.analysis import (
    category_breakdown, compute_maintainer_stats, compute_merge_times,
    detect_batch_merges, parse_pr_node,
)
from ghscope.core.github import graphql, paginated_query
from ghscope.core.models import PRSummary, TriageReport
from ghscope.core.queries import CLOSED_PRS_PAGE, MERGED_PRS_PAGE, REPO_OVERVIEW
from ghscope.display.json_out import print_json
from ghscope.display.tables import display_triage

console = Console()


def _fetch_pr_data(ctx: GhscopeContext, state: str, query: str, cache_key: str) -> list[PRSummary]:
    """Fetch PRs for a given state, using cache if available."""
    if not ctx.no_cache:
        if ctx.offline:
            cached = cache.get_offline(ctx.repo, cache_key)
        else:
            cached = cache.get(ctx.repo, cache_key)
        if cached is not None:
            return [parse_pr_node(n, state) for n in cached]

    if ctx.offline:
        return []

    nodes = paginated_query(
        query,
        ["repository", "pullRequests"],
        variables={"owner": ctx.owner, "name": ctx.name},
        limit=ctx.limit,
    )
    cache.put(ctx.repo, cache_key, nodes)
    return [parse_pr_node(n, state) for n in nodes]


def fetch_triage_data(ctx: GhscopeContext) -> TriageReport:
    """Fetch and compute triage report."""
    merged = _fetch_pr_data(ctx, "MERGED", MERGED_PRS_PAGE, "merged_prs")
    closed = _fetch_pr_data(ctx, "CLOSED", CLOSED_PRS_PAGE, "closed_prs")

    # Get counts from overview
    overview_data = None
    if not ctx.no_cache:
        if ctx.offline:
            overview_data = cache.get_offline(ctx.repo, "overview")
        else:
            overview_data = cache.get(ctx.repo, "overview")

    if overview_data is None and not ctx.offline:
        overview_data = graphql(REPO_OVERVIEW, {"owner": ctx.owner, "name": ctx.name})
        overview_data = overview_data.get("repository", overview_data)
        cache.put(ctx.repo, "overview", overview_data)

    total_open = 0
    if overview_data:
        total_open = overview_data.get("openPRs", {}).get("totalCount", 0)

    total_m = len(merged)
    total_c = len(closed)
    total = total_m + total_c
    rate = (total_m / total * 100) if total > 0 else 0

    med, p25, p75 = compute_merge_times(merged)
    maintainers = compute_maintainer_stats(merged)
    batches = detect_batch_merges(merged)
    cats = category_breakdown(merged, closed)

    return TriageReport(
        repo=ctx.repo,
        total_merged=total_m,
        total_closed=total_c,
        total_open=total_open,
        merge_rate=rate,
        median_merge_hours=med,
        p25_merge_hours=p25,
        p75_merge_hours=p75,
        maintainer_stats=maintainers,
        batch_clusters=batches,
        category_breakdown=cats,
    )


def run_triage(ctx: GhscopeContext) -> None:
    with Status(f"Analyzing PRs for {ctx.repo}...", console=console):
        report = fetch_triage_data(ctx)

    if ctx.json_output:
        print_json(report)
    elif ctx.fmt == "rich":
        display_triage(report)
    elif ctx.fmt in ("csv", "parquet"):
        from ghscope.frames import triage_frames, export_tables
        export_tables(triage_frames(report), ctx.fmt)
    else:
        from ghscope.frames import triage_frames, display_polars
        display_polars(triage_frames(report))
