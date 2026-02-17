"""Combined dashboard (default command)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from statistics import median

from rich.console import Console
from rich.status import Status

from ghscope.core import cache
from ghscope.core.analysis import compute_bus_factor, parse_datetime
from ghscope.core.github import graphql
from ghscope.core.models import HealthReport
from ghscope.core.queries import MERGED_PRS_PAGE, REPO_OVERVIEW
from ghscope.display.json_out import print_json
from ghscope.display.tables import display_overview

console = Console()


def _fetch_overview(ctx) -> dict:
    cache_key = "overview"
    if not ctx.no_cache:
        if ctx.offline:
            cached = cache.get_offline(ctx.repo, cache_key)
        else:
            cached = cache.get(ctx.repo, cache_key)
        if cached is not None:
            return cached

    if ctx.offline:
        return {}

    data = graphql(REPO_OVERVIEW, {"owner": ctx.owner, "name": ctx.name})
    result = data.get("repository", data)
    cache.put(ctx.repo, cache_key, result)
    return result


def run_overview(ctx) -> None:
    """Full repository overview dashboard."""
    with Status(f"Fetching overview for {ctx.repo}...", console=console):
        overview = _fetch_overview(ctx)

        # Also fetch triage and health summaries
        triage = None
        health = None
        try:
            from ghscope.commands.triage import fetch_triage_data
            triage = fetch_triage_data(ctx)
        except Exception:
            pass
        try:
            from ghscope.commands.health import _fetch_commits
            from ghscope.commands.triage import _fetch_pr_data

            commits = _fetch_commits(ctx)
            merged_prs = _fetch_pr_data(ctx, "MERGED", MERGED_PRS_PAGE, "merged_prs")
            weeks = ctx.days / 7
            commits_per_week = len(commits) / weeks if weeks > 0 else 0

            cutoff_30d = datetime.now() - timedelta(days=30)
            active_authors = set()
            for c in commits:
                dt = parse_datetime(c.get("committedDate"))
                if dt and dt.replace(tzinfo=None) > cutoff_30d:
                    author = (c.get("author") or {}).get("user") or {}
                    login = author.get("login")
                    if login:
                        active_authors.add(login)

            bus_factor, _ = compute_bus_factor(merged_prs, days=ctx.days)

            release_cadence = None
            last_release = None
            releases = overview.get("releases", {}).get("nodes", [])
            if releases:
                last_release = releases[0].get("tagName")
                if len(releases) >= 2:
                    dates = [parse_datetime(r["createdAt"]) for r in releases]
                    deltas = [(dates[i] - dates[i + 1]).days for i in range(len(dates) - 1)]
                    release_cadence = median(deltas) if deltas else None

            committer_counts = Counter()
            for c in commits:
                author = (c.get("author") or {}).get("user") or {}
                login = author.get("login", "unknown")
                committer_counts[login] += 1

            health = HealthReport(
                repo=ctx.repo,
                commits_per_week=commits_per_week,
                active_contributors_30d=len(active_authors),
                release_cadence_days=release_cadence,
                last_release=last_release,
                issue_response_time_hours=None,
                bus_factor=bus_factor,
                top_committers=committer_counts.most_common(10),
                weekly_commits=[],
            )
        except Exception:
            pass

    if ctx.json_output:
        result = {"overview": overview}
        if triage:
            result["triage"] = triage
        if health:
            result["health"] = health
        print_json(result)
    else:
        display_overview(ctx.repo, overview, triage, health)
