"""Public Python API — returns ibis tables for programmatic use.

Usage:
    import ghscope.api as gs

    # Scorecard — single ibis.Table (signal/value/read)
    gs.scorecard("mtgjson/mtgjson").to_polars()

    # Individual reports — dict[str, ibis.Table]
    tables = gs.review("mtgjson/mtgjson")
    tables["reviewers"].to_polars()
    tables["summary"].to_pandas()

    # All: gs.triage(), gs.review(), gs.contribs(), gs.health(), gs.assess()
"""

from __future__ import annotations

import ibis

from ghscope.cli import GhscopeContext
from ghscope.core.github import check_gh_cli


def _ctx(repo: str, *, limit: int = 100, days: int = 90,
         no_cache: bool = False, offline: bool = False) -> GhscopeContext:
    if "/" not in repo:
        raise ValueError("repo must be owner/repo format (e.g. facebook/react)")
    if not offline:
        check_gh_cli()
    return GhscopeContext(repo, json_output=False, no_cache=no_cache,
                          offline=offline, limit=limit, days=days,
                          verbose=False)


def triage(repo: str, **kwargs) -> dict[str, ibis.Table]:
    """PR merge patterns & maintainer responsiveness."""
    ctx = _ctx(repo, **kwargs)
    from ghscope.commands.triage import fetch_triage_data
    from ghscope.frames import triage_frames
    return triage_frames(fetch_triage_data(ctx))


def assess(repo: str, **kwargs) -> dict[str, ibis.Table]:
    """Your open PRs' merge likelihood."""
    ctx = _ctx(repo, **kwargs)
    from ghscope.commands.assess import fetch_assess_report
    from ghscope.frames import assess_frames
    return assess_frames(fetch_assess_report(ctx))


def contribs(repo: str, **kwargs) -> dict[str, ibis.Table]:
    """Contributor dynamics & first-timer retention."""
    ctx = _ctx(repo, **kwargs)
    from ghscope.commands.contribs import fetch_contribs_report
    from ghscope.frames import contribs_frames
    return contribs_frames(fetch_contribs_report(ctx))


def review(repo: str, **kwargs) -> dict[str, ibis.Table]:
    """Review bottlenecks & reviewer stats."""
    ctx = _ctx(repo, **kwargs)
    from ghscope.commands.review import fetch_review_report
    from ghscope.frames import review_frames
    return review_frames(fetch_review_report(ctx))


def health(repo: str, **kwargs) -> dict[str, ibis.Table]:
    """Commit velocity, release cadence, bus factor."""
    ctx = _ctx(repo, **kwargs)
    from ghscope.commands.health import fetch_health_report
    from ghscope.frames import health_frames
    return health_frames(fetch_health_report(ctx))


def scorecard(repo: str, **kwargs) -> ibis.Table:
    """Synthesized signal/value/read scorecard from all reports."""
    ctx = _ctx(repo, **kwargs)
    from ghscope.commands.overview import _fetch_all_reports
    from ghscope.frames import scorecard_frame
    t, c, r, h = _fetch_all_reports(ctx)
    return scorecard_frame(t, c, r, h)
