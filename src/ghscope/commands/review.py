"""Review bottleneck analysis — who reviews, turnaround, coverage."""

from __future__ import annotations

from rich.console import Console
from rich.status import Status

from ghscope.cli import GhscopeContext
from ghscope.core import cache
from ghscope.core.analysis import compute_review_analysis
from ghscope.core.github import paginated_query
from ghscope.core.queries import MERGED_PRS_WITH_REVIEWS, OPEN_PRS_WITH_REVIEWS
from ghscope.display.json_out import print_json
from ghscope.display.tables import display_review

console = Console()


def _fetch_review_nodes(ctx: GhscopeContext, state: str, query: str,
                        cache_key: str) -> list[dict]:
    """Fetch raw PR nodes with review data, using cache."""
    if not ctx.no_cache:
        if ctx.offline:
            cached = cache.get_offline(ctx.repo, cache_key)
        else:
            cached = cache.get(ctx.repo, cache_key)
        if cached is not None:
            return cached

    if ctx.offline:
        return []

    nodes = paginated_query(
        query,
        ["repository", "pullRequests"],
        variables={"owner": ctx.owner, "name": ctx.name},
        limit=ctx.limit,
    )
    cache.put(ctx.repo, cache_key, nodes)
    return nodes


def fetch_review_report(ctx: GhscopeContext) -> 'ReviewReport':
    """Fetch and compute review report."""
    merged_nodes = _fetch_review_nodes(
        ctx, "MERGED", MERGED_PRS_WITH_REVIEWS, "merged_prs_reviews")
    open_nodes = _fetch_review_nodes(
        ctx, "OPEN", OPEN_PRS_WITH_REVIEWS, "open_prs_reviews")
    return compute_review_analysis(merged_nodes, open_nodes, ctx.repo)


def run_review(ctx: GhscopeContext) -> None:
    with Status(f"Analyzing reviews for {ctx.repo}...", console=console):
        report = fetch_review_report(ctx)

    if ctx.json_output:
        print_json(report)
    elif ctx.fmt == "rich":
        display_review(report)
    elif ctx.fmt in ("csv", "parquet"):
        from ghscope.frames import review_frames, export_tables
        export_tables(review_frames(report), ctx.fmt)
    else:
        from ghscope.frames import review_frames, display_polars
        display_polars(review_frames(report))
