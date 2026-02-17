"""Convert report dataclasses to ibis memtables and render output.

Per-report functions return dict[str, ibis.Table].
scorecard_frame() synthesizes all reports into a single signal/value/read table.
Tables can be materialized to any backend:

    tables["reviewers"].to_polars()
    scorecard_frame(...).to_pandas()
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


def _fmt_hours(h: float | None) -> str:
    """Format hours into human-readable string."""
    if h is None:
        return "null"
    if h < 1:
        return f"{h * 60:.0f}m"
    elif h < 24:
        return f"{h:.1f}h"
    else:
        return f"{h / 24:.1f}d"


def scorecard_frame(
    triage: TriageReport | None,
    contribs: ContributorReport | None,
    review: ReviewReport | None,
    health: HealthReport | None,
) -> ibis.Table:
    """Synthesize all reports into a single signal/value/read scorecard."""
    rows: list[dict[str, str]] = []

    def add(signal: str, value: str, read: str) -> None:
        rows.append({"signal": signal, "value": value, "read": read})

    # --- Review signals ---
    if review:
        cov = review.review_coverage
        total = review.total_reviewed_prs + review.total_unreviewed_merged
        if cov < 30:
            read = f"{review.total_unreviewed_merged}/{total} merges go in blind"
        elif cov < 70:
            read = "partial coverage — room to improve"
        else:
            read = "most PRs reviewed before merge"
        add("review_coverage", f"{cov:.0f}%", read)

        if review.reviewer_stats:
            top = review.reviewer_stats[0]
            n = review.reviewer_concentration
            if n <= 1:
                read = f"sole gatekeeper · {_fmt_hours(top.avg_turnaround_hours)} avg turnaround"
            else:
                read = f"{n} reviewers cover 50%+ of reviews"
            add("reviewer_spread", f"{n} ({top.login})", read)

    # --- Health signals ---
    if health:
        add("active_contributors", str(health.active_contributors_30d),
            "only 1 person active in last 30d" if health.active_contributors_30d <= 1
            else f"{health.active_contributors_30d} people active in last 30d")

        if health.bus_factor == 0:
            read = "no merges in lookback · can't compute"
        elif health.bus_factor == 1:
            read = "single point of failure"
        else:
            read = f"{health.bus_factor} people cover 50%+ of merges"
        add("bus_factor", str(health.bus_factor), read)

        if health.top_committers:
            top_name, top_n = health.top_committers[0]
            total_c = sum(c for _, c in health.top_committers)
            pct = round(top_n / total_c * 100) if total_c else 0
            read = f"{top_name} dominates ({top_n}/{total_c}, {pct}%)"
        else:
            read = "no commit data"
        add("commit_velocity", f"{health.commits_per_week:.1f}/wk", read)

        if health.release_cadence_days is not None:
            add("release_cadence", f"{health.release_cadence_days:.0f}d",
                f"last: {health.last_release}" if health.last_release else "has releases")
        else:
            add("release_cadence", "—",
                "no releases ever" if not health.last_release else f"only 1 release: {health.last_release}")

        if health.issue_response_time_hours is not None:
            if health.issue_response_time_hours < 24:
                qual = "fast · under 24h"
            elif health.issue_response_time_hours < 168:
                qual = "slow · over a day"
            else:
                qual = "very slow · over a week"
            add("issue_response", _fmt_hours(health.issue_response_time_hours), qual)
        else:
            add("issue_response", "—", "no issue responses to measure")

    # --- Triage signals ---
    if triage:
        add("merge_rate", f"{triage.merge_rate:.1f}%",
            f"median {_fmt_hours(triage.median_merge_hours)} · p75 {_fmt_hours(triage.p75_merge_hours)}")

        if triage.maintainer_stats:
            top = triage.maintainer_stats[0]
            if len(triage.maintainer_stats) == 1:
                read = f"{top.login} is the sole merger"
            else:
                read = f"{top.login} leads · {top.merge_count} merges"
            add("top_merger", f"{top.login} ({top.merge_count})", read)

    # --- Contributor signals ---
    if contribs:
        if contribs.first_timers == 0:
            read = "zero new contributors in window"
        else:
            read = f"{contribs.first_timer_merge_rate:.0f}% merge rate · {contribs.retention_rate:.0f}% retention"
        add("first_timers", str(contribs.first_timers), read)

        if contribs.top_contributors:
            top = contribs.top_contributors[0]
            add("top_contributor", f"{top.login} ({top.merged_count})",
                f"{top.merge_rate:.0f}% merge rate")

    # --- Unreviewed open PRs ---
    if review and review.unreviewed_open_prs:
        n = len(review.unreviewed_open_prs)
        stale = len(review.stale_review_prs)
        oldest = max(pr.age_hours for pr in review.unreviewed_open_prs)
        add("unreviewed_prs", str(n),
            f"{stale} stale · oldest waiting {_fmt_hours(oldest)}")

    return ibis.memtable(rows) if rows else ibis.memtable(
        {"signal": [], "value": [], "read": []})


def display_scorecard(repo: str, table: ibis.Table) -> None:
    """Render the scorecard as clean aligned text."""
    from rich.console import Console

    console = Console()
    df = table.to_polars()
    rows = list(df.iter_rows(named=True))

    sig_w = max(len(r["signal"]) for r in rows)
    val_w = max(len(r["value"]) for r in rows)

    console.print()
    console.print(f"  [bold]{repo}[/bold] by the numbers")
    console.print(f"  [dim]{'─' * (sig_w + val_w + 30)}[/dim]")
    console.print()
    for r in rows:
        sig = r["signal"].ljust(sig_w)
        val = r["value"].rjust(val_w)
        console.print(f"  [cyan]{sig}[/]  [bold white]{val}[/]  [dim]│[/] {r['read']}")
    console.print()


def display_scorecard_md(repo: str, table: ibis.Table) -> None:
    """Render the scorecard as a markdown table."""
    df = table.to_polars()
    rows = list(df.iter_rows(named=True))

    sig_w = max(len(r["signal"]) for r in rows + [{"signal": "signal"}])
    val_w = max(len(r["value"]) for r in rows + [{"value": "value"}])
    read_w = max(len(r["read"]) for r in rows + [{"read": "read"}])

    def row_str(s: str, v: str, r: str) -> str:
        return f"| {s.ljust(sig_w)} | {v.rjust(val_w)} | {r.ljust(read_w)} |"

    print(f"\n**{repo} by the numbers**\n")
    print(row_str("signal", "value", "read"))
    print(f"|{'-' * (sig_w + 2)}|{'-' * (val_w + 2)}:|{'-' * (read_w + 2)}|")
    for r in rows:
        print(row_str(r["signal"], r["value"], r["read"]))
    print()


def display_polars(tables: dict[str, ibis.Table]) -> None:
    """Default output — print all tables as polars DataFrames."""
    for name, table in tables.items():
        header = name.upper().replace("_", " ")
        print(f"\n=== {header} ===")
        df = table.to_polars()
        if name == "summary":
            print(df.unpivot())
        else:
            print(df)
    print()


def export_tables(tables: dict[str, ibis.Table], fmt: str) -> None:
    """Export ibis tables to stdout (csv), files (parquet), or Rich."""
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
