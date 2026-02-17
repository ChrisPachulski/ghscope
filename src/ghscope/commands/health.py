"""Commit velocity, release cadence, bus factor."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import median

from rich.console import Console
from rich.status import Status

from ghscope.cli import GhscopeContext
from ghscope.core import cache
from ghscope.core.analysis import compute_bus_factor, parse_datetime, parse_pr_node
from ghscope.core.github import graphql, paginated_query
from ghscope.core.models import HealthReport, PRSummary
from ghscope.core.queries import (
    COMMIT_HISTORY, ISSUE_TIMELINE, MERGED_PRS_PAGE, REPO_OVERVIEW,
)
from ghscope.display.json_out import print_json
from ghscope.display.tables import display_health

console = Console()


def _fetch_commits(ctx: GhscopeContext) -> list[dict]:
    cache_key = "commits"
    if not ctx.no_cache:
        if ctx.offline:
            cached = cache.get_offline(ctx.repo, cache_key)
        else:
            cached = cache.get(ctx.repo, cache_key)
        if cached is not None:
            return cached

    if ctx.offline:
        return []

    since = (datetime.now() - timedelta(days=ctx.days)).isoformat() + "Z"
    data = graphql(COMMIT_HISTORY, {"owner": ctx.owner, "name": ctx.name, "since": since})

    branch = data.get("repository", {}).get("defaultBranchRef", {})
    target = branch.get("target", {}) if branch else {}
    history = target.get("history", {})
    edges = history.get("edges", [])
    nodes = [e["node"] for e in edges]
    cache.put(ctx.repo, cache_key, nodes)
    return nodes


def _fetch_issues(ctx: GhscopeContext) -> list[dict]:
    cache_key = "issues"
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
        ISSUE_TIMELINE,
        ["repository", "issues"],
        variables={"owner": ctx.owner, "name": ctx.name},
        limit=min(ctx.limit, 50),
    )
    cache.put(ctx.repo, cache_key, nodes)
    return nodes


def fetch_health_report(ctx: GhscopeContext) -> HealthReport:
    """Fetch and compute health report."""
    from ghscope.commands.triage import _fetch_pr_data

    commits = _fetch_commits(ctx)
    issues = _fetch_issues(ctx)
    merged_prs = _fetch_pr_data(ctx, "MERGED", MERGED_PRS_PAGE, "merged_prs")

    # Overview for releases
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

    weeks = ctx.days / 7
    commits_per_week = len(commits) / weeks if weeks > 0 else 0

    weekly: dict[str, int] = defaultdict(int)
    for c in commits:
        dt = parse_datetime(c.get("committedDate"))
        if dt:
            week_key = dt.strftime("%m/%d")
            weekly[week_key] += 1
    sorted_weeks = sorted(weekly.items())

    cutoff_30d = datetime.now() - timedelta(days=30)
    active_authors = set()
    for c in commits:
        dt = parse_datetime(c.get("committedDate"))
        if dt and dt.replace(tzinfo=None) > cutoff_30d:
            author = (c.get("author") or {}).get("user") or {}
            login = author.get("login")
            if login:
                active_authors.add(login)

    committer_counts = Counter()
    for c in commits:
        author = (c.get("author") or {}).get("user") or {}
        login = author.get("login", "unknown")
        committer_counts[login] += 1
    top_committers = committer_counts.most_common(10)

    release_cadence = None
    last_release = None
    if overview_data:
        releases = overview_data.get("releases", {}).get("nodes", [])
        if releases:
            last_release = releases[0].get("tagName")
            if len(releases) >= 2:
                dates = [parse_datetime(r["createdAt"]) for r in releases]
                deltas = [(dates[i] - dates[i + 1]).days for i in range(len(dates) - 1)]
                release_cadence = median(deltas) if deltas else None

    response_times = []
    for issue in issues:
        created = parse_datetime(issue.get("createdAt"))
        comments = issue.get("comments", {}).get("nodes", [])
        if created and comments:
            first_comment = parse_datetime(comments[0].get("createdAt"))
            issue_author = (issue.get("author") or {}).get("login")
            comment_author = (comments[0].get("author") or {}).get("login")
            if first_comment and comment_author != issue_author:
                hours = (first_comment - created).total_seconds() / 3600
                if hours >= 0:
                    response_times.append(hours)

    issue_response = median(response_times) if response_times else None
    bus_factor, _ = compute_bus_factor(merged_prs, days=ctx.days)

    return HealthReport(
        repo=ctx.repo,
        commits_per_week=commits_per_week,
        active_contributors_30d=len(active_authors),
        release_cadence_days=release_cadence,
        last_release=last_release,
        issue_response_time_hours=issue_response,
        bus_factor=bus_factor,
        top_committers=top_committers,
        weekly_commits=sorted_weeks,
    )


def run_health(ctx: GhscopeContext) -> None:
    with Status(f"Analyzing health for {ctx.repo}...", console=console):
        report = fetch_health_report(ctx)

    if ctx.fmt:
        from ghscope.frames import health_frames, export_tables
        export_tables(health_frames(report), ctx.fmt)
    elif ctx.json_output:
        print_json(report)
    else:
        display_health(report)
