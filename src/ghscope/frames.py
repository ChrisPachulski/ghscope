"""Convert report dataclasses to ibis memtables.

Each function returns dict[str, ibis.Table] — one table per logical entity.
Tables can be materialized to any backend:

    tables["reviewers"].to_polars()
    tables["reviewers"].to_pandas()
"""

from __future__ import annotations

import sys

import ibis

from ghscope.core.models import (
    AssessmentReport,
    ContributorReport,
    HealthReport,
    PRSummary,
    ReviewReport,
    TriageReport,
)


def _mt(rows: list[dict]) -> ibis.Table | None:
    """Create a memtable from rows, or None if empty."""
    if not rows:
        return None
    return ibis.memtable(rows)


def _pr_row(pr: PRSummary) -> dict:
    """Flatten a PRSummary to a dict for ibis."""
    return {
        "number": pr.number,
        "title": pr.title,
        "author": pr.author,
        "state": pr.state,
        "category": pr.category,
        "size": pr.size,
        "additions": pr.additions,
        "deletions": pr.deletions,
        "changed_files": pr.changed_files,
        "review_count": pr.review_count,
        "created_at": pr.created_at,
        "merged_at": pr.merged_at,
        "closed_at": pr.closed_at,
        "merged_by": pr.merged_by,
        "age_hours": round(pr.age_hours, 1),
        "time_to_merge_hours": round(pr.time_to_merge_hours, 1) if pr.time_to_merge_hours else None,
    }


def triage_frames(report: TriageReport) -> dict[str, ibis.Table]:
    tables: dict[str, ibis.Table] = {}

    tables["summary"] = ibis.memtable([{
        "repo": report.repo,
        "total_merged": report.total_merged,
        "total_closed": report.total_closed,
        "total_open": report.total_open,
        "merge_rate": round(report.merge_rate, 1),
        "median_merge_hours": round(report.median_merge_hours, 1),
        "p25_merge_hours": round(report.p25_merge_hours, 1),
        "p75_merge_hours": round(report.p75_merge_hours, 1),
    }])

    rows = [
        {"login": m.login, "merge_count": m.merge_count,
         "avg_merge_time_hours": round(m.avg_merge_time_hours, 1)}
        for m in report.maintainer_stats
    ]
    t = _mt(rows)
    if t is not None:
        tables["maintainers"] = t

    cat_rows = [
        {"category": cat, "count": d["count"], "merged": d["merged"],
         "merge_rate": d["merge_rate"], "median_hours": d["median_hours"]}
        for cat, d in report.category_breakdown.items()
    ]
    t = _mt(cat_rows)
    if t is not None:
        tables["categories"] = t

    return tables


def assess_frames(report: AssessmentReport) -> dict[str, ibis.Table]:
    tables: dict[str, ibis.Table] = {}

    rows = [
        {"pr_number": a.pr.number, "pr_title": a.pr.title,
         "author": a.pr.author, "probability": a.probability,
         "size": a.pr.size, "category": a.pr.category,
         "review_count": a.pr.review_count,
         "age_hours": round(a.pr.age_hours, 1),
         "factors": "; ".join(a.factors)}
        for a in report.assessments
    ]
    t = _mt(rows)
    if t is not None:
        tables["assessments"] = t

    return tables


def contribs_frames(report: ContributorReport) -> dict[str, ibis.Table]:
    tables: dict[str, ibis.Table] = {}

    tables["summary"] = ibis.memtable([{
        "repo": report.repo,
        "total_contributors": report.total_contributors,
        "repeat_contributors": report.repeat_contributors,
        "one_time_contributors": report.one_time_contributors,
        "first_timers": report.first_timers,
        "first_timer_merge_rate": report.first_timer_merge_rate,
        "first_timer_median_merge_hours": report.first_timer_median_merge_hours,
        "repeat_median_merge_hours": report.repeat_median_merge_hours,
        "retained_first_timers": report.retained_first_timers,
        "retention_rate": report.retention_rate,
    }])

    rows = [
        {"login": c.login, "merged_count": c.merged_count,
         "closed_count": c.closed_count, "open_count": c.open_count,
         "first_contribution": c.first_contribution,
         "merge_rate": c.merge_rate}
        for c in report.top_contributors
    ]
    t = _mt(rows)
    if t is not None:
        tables["contributors"] = t

    spam_rows = [_pr_row(p) for p in report.spam_prs]
    t = _mt(spam_rows)
    if t is not None:
        tables["spam_prs"] = t

    return tables


def review_frames(report: ReviewReport) -> dict[str, ibis.Table]:
    tables: dict[str, ibis.Table] = {}

    tables["summary"] = ibis.memtable([{
        "repo": report.repo,
        "total_reviewed_prs": report.total_reviewed_prs,
        "total_unreviewed_merged": report.total_unreviewed_merged,
        "review_coverage": round(report.review_coverage, 1),
        "median_first_review_hours": (
            round(report.median_first_review_hours, 2)
            if report.median_first_review_hours else None
        ),
        "median_review_to_merge_hours": (
            round(report.median_review_to_merge_hours, 2)
            if report.median_review_to_merge_hours else None
        ),
        "reviewer_concentration": report.reviewer_concentration,
    }])

    rows = [
        {"login": r.login, "review_count": r.review_count,
         "avg_turnaround_hours": round(r.avg_turnaround_hours, 1),
         "approval_count": r.approval_count,
         "changes_requested_count": r.changes_requested_count,
         "comment_only_count": r.comment_only_count}
        for r in report.reviewer_stats
    ]
    t = _mt(rows)
    if t is not None:
        tables["reviewers"] = t

    unreviewed_rows = [_pr_row(p) for p in report.unreviewed_open_prs]
    t = _mt(unreviewed_rows)
    if t is not None:
        tables["unreviewed_open_prs"] = t

    stale_rows = [_pr_row(p) for p in report.stale_review_prs]
    t = _mt(stale_rows)
    if t is not None:
        tables["stale_prs"] = t

    return tables


def health_frames(report: HealthReport) -> dict[str, ibis.Table]:
    tables: dict[str, ibis.Table] = {}

    tables["summary"] = ibis.memtable([{
        "repo": report.repo,
        "commits_per_week": round(report.commits_per_week, 1),
        "active_contributors_30d": report.active_contributors_30d,
        "bus_factor": report.bus_factor,
        "release_cadence_days": (
            round(report.release_cadence_days, 0)
            if report.release_cadence_days else None
        ),
        "last_release": report.last_release,
        "issue_response_time_hours": (
            round(report.issue_response_time_hours, 1)
            if report.issue_response_time_hours else None
        ),
    }])

    rows = [
        {"login": login, "commits": count}
        for login, count in report.top_committers
    ]
    t = _mt(rows)
    if t is not None:
        tables["top_committers"] = t

    week_rows = [
        {"week": week, "commits": count}
        for week, count in report.weekly_commits
    ]
    t = _mt(week_rows)
    if t is not None:
        tables["weekly_commits"] = t

    return tables


def export_tables(tables: dict[str, ibis.Table], fmt: str) -> None:
    """Export ibis tables to stdout (csv) or files (parquet)."""
    if fmt == "csv":
        for name, table in tables.items():
            sys.stdout.write(f"# {name}\n")
            table.to_pandas().to_csv(sys.stdout, index=False)
            sys.stdout.write("\n")
    elif fmt == "parquet":
        for name, table in tables.items():
            path = f"{name}.parquet"
            table.to_pandas().to_parquet(path)
            sys.stderr.write(f"Wrote {path}\n")
