"""Rich table formatters per command."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ghscope.core.models import (
    AssessmentReport, ContributorReport, HealthReport, ReviewReport,
    TriageReport,
)
from ghscope.display.charts import sparkline

console = Console()


def format_hours(hours: float) -> str:
    if hours < 1:
        return f"{hours * 60:.0f}m"
    elif hours < 24:
        return f"{hours:.1f}h"
    else:
        return f"{hours / 24:.1f}d"


def display_triage(report: TriageReport) -> None:
    console.print()
    console.print(Panel(
        f"[bold]{report.repo}[/] — PR Triage Analysis",
        subtitle=f"Merged: {report.total_merged}  Closed: {report.total_closed}  Open: {report.total_open}",
    ))

    # Summary stats
    table = Table(title="Merge Statistics", show_header=False, border_style="dim")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Merge Rate", f"{report.merge_rate:.1f}%")
    table.add_row("Median Merge Time", format_hours(report.median_merge_hours))
    table.add_row("P25 (Fast)", format_hours(report.p25_merge_hours))
    table.add_row("P75 (Slow)", format_hours(report.p75_merge_hours))
    console.print(table)

    # Maintainer stats
    if report.maintainer_stats:
        mt = Table(title="Top Mergers", border_style="dim")
        mt.add_column("Maintainer", style="cyan")
        mt.add_column("Merges", justify="right")
        mt.add_column("Avg Time", justify="right")
        for ms in report.maintainer_stats[:5]:
            mt.add_row(ms.login, str(ms.merge_count), format_hours(ms.avg_merge_time_hours))
        console.print(mt)

    # Category breakdown
    if report.category_breakdown:
        ct = Table(title="PR Categories", border_style="dim")
        ct.add_column("Category", style="yellow")
        ct.add_column("Total", justify="right")
        ct.add_column("Merged", justify="right")
        ct.add_column("Merge Rate", justify="right")
        ct.add_column("Median Time", justify="right")
        for cat, data in sorted(report.category_breakdown.items(), key=lambda x: x[1]["count"], reverse=True):
            ct.add_row(
                cat, str(data["count"]), str(data["merged"]),
                f"{data['merge_rate']}%", format_hours(data["median_hours"]),
            )
        console.print(ct)

    # Batch merges
    if report.batch_clusters:
        bt = Table(title="Batch Merge Patterns", border_style="dim")
        bt.add_column("Merger", style="cyan")
        bt.add_column("Count", justify="right")
        bt.add_column("Window")
        bt.add_column("PRs")
        for bc in report.batch_clusters[:5]:
            window = format_hours((bc.end_time - bc.start_time).total_seconds() / 3600)
            pr_nums = ", ".join(f"#{n}" for n in bc.prs[:5])
            if len(bc.prs) > 5:
                pr_nums += f" +{len(bc.prs) - 5} more"
            bt.add_row(bc.merger, str(bc.count), window, pr_nums)
        console.print(bt)

    console.print()


def display_assess(report: AssessmentReport) -> None:
    console.print()
    console.print(Panel(
        f"[bold]{report.repo}[/] — PR Assessment for [cyan]{report.user}[/]",
    ))

    if not report.assessments:
        console.print("[yellow]No open PRs found for this user.[/]")
        return

    for a in report.assessments:
        # Color the probability
        prob = a.probability
        if prob >= 70:
            prob_style = "green bold"
        elif prob >= 40:
            prob_style = "yellow"
        else:
            prob_style = "red"

        console.print(f"\n[bold]#{a.pr.number}[/] {a.pr.title}")
        console.print(f"  Merge probability: [{prob_style}]{prob}%[/]")
        console.print(f"  Size: {a.pr.size} | Category: {a.pr.category} | Reviews: {a.pr.review_count}")

        for factor in a.factors:
            console.print(f"    [dim]• {factor}[/]")

        if a.similar_merged:
            console.print("  [green]Similar merged:[/]")
            for sp in a.similar_merged[:3]:
                console.print(f"    [dim]#{sp.number} {sp.title} ({format_hours(sp.time_to_merge_hours or 0)})[/]")
        if a.similar_closed:
            console.print("  [red]Similar closed:[/]")
            for sp in a.similar_closed[:3]:
                console.print(f"    [dim]#{sp.number} {sp.title}[/]")

    console.print()


def display_contribs(report: ContributorReport) -> None:
    console.print()
    console.print(Panel(
        f"[bold]{report.repo}[/] — Contributor Dynamics",
        subtitle=f"Total: {report.total_contributors}  Repeat: {report.repeat_contributors}  One-time: {report.one_time_contributors}",
    ))

    if report.top_contributors:
        ct = Table(title="Top Contributors", border_style="dim")
        ct.add_column("Author", style="cyan")
        ct.add_column("Merged", justify="right")
        ct.add_column("Closed", justify="right")
        ct.add_column("Open", justify="right")
        ct.add_column("Merge Rate", justify="right")
        for c in report.top_contributors[:15]:
            ct.add_row(
                c.login, str(c.merged_count), str(c.closed_count),
                str(c.open_count), f"{c.merge_rate}%",
            )
        console.print(ct)

    # First-timer stats
    if report.first_timers > 0:
        ft = Table(title="First-Timer Retention", border_style="dim")
        ft.add_column("Metric", style="bold")
        ft.add_column("Value")
        ft.add_row("New Contributors", str(report.first_timers))
        ft.add_row("First-Timer Merge Rate", f"{report.first_timer_merge_rate}%")
        if report.first_timer_median_merge_hours is not None:
            ft.add_row("First-Timer Median Merge", format_hours(report.first_timer_median_merge_hours))
        if report.repeat_median_merge_hours is not None:
            ft.add_row("Repeat Contributor Median", format_hours(report.repeat_median_merge_hours))
        ft.add_row("Retained (2+ PRs)", str(report.retained_first_timers))
        ft.add_row("Retention Rate", f"{report.retention_rate}%")
        console.print(ft)

    if report.spam_prs:
        console.print(f"\n[red bold]Potential Spam PRs ({len(report.spam_prs)}):[/]")
        for pr in report.spam_prs[:10]:
            console.print(f"  [dim]#{pr.number} {pr.title} by {pr.author}[/]")

    console.print()


def display_review(report: ReviewReport) -> None:
    console.print()
    console.print(Panel(
        f"[bold]{report.repo}[/] — Review Bottleneck Analysis",
        subtitle=f"Reviewed: {report.total_reviewed_prs}  Unreviewed merges: {report.total_unreviewed_merged}",
    ))

    # Summary stats
    table = Table(title="Review Coverage", show_header=False, border_style="dim")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Review Coverage", f"{report.review_coverage:.1f}%")
    if report.median_first_review_hours is not None:
        table.add_row("Median Time to First Review", format_hours(report.median_first_review_hours))
    if report.median_review_to_merge_hours is not None:
        table.add_row("Median Review → Merge", format_hours(report.median_review_to_merge_hours))
    table.add_row("Reviewer Concentration", f"{report.reviewer_concentration} reviewer(s) cover 50% of reviews")
    console.print(table)

    # Top reviewers
    if report.reviewer_stats:
        rt = Table(title="Top Reviewers", border_style="dim")
        rt.add_column("Reviewer", style="cyan")
        rt.add_column("Reviews", justify="right")
        rt.add_column("Avg Turnaround", justify="right")
        rt.add_column("Approved", justify="right")
        rt.add_column("Changes Req.", justify="right")
        rt.add_column("Comments", justify="right")
        for rs in report.reviewer_stats[:10]:
            rt.add_row(
                rs.login,
                str(rs.review_count),
                format_hours(rs.avg_turnaround_hours),
                str(rs.approval_count),
                str(rs.changes_requested_count),
                str(rs.comment_only_count),
            )
        console.print(rt)

    # Unreviewed open PRs
    if report.unreviewed_open_prs:
        console.print(f"\n[yellow bold]Open PRs Awaiting Review ({len(report.unreviewed_open_prs)}):[/]")
        for pr in report.unreviewed_open_prs[:10]:
            age = format_hours(pr.age_hours)
            style = "red" if pr.age_hours > 7 * 24 else "dim"
            console.print(f"  [{style}]#{pr.number} {pr.title} by {pr.author} ({age})[/]")

    # Stale PRs
    if report.stale_review_prs:
        console.print(f"\n[red bold]Stale (>7 days, no review): {len(report.stale_review_prs)}[/]")

    console.print()


def display_health(report: HealthReport) -> None:
    console.print()
    console.print(Panel(
        f"[bold]{report.repo}[/] — Repository Health",
    ))

    table = Table(show_header=False, border_style="dim")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Commits/Week", f"{report.commits_per_week:.1f}")
    table.add_row("Active Contributors (30d)", str(report.active_contributors_30d))
    table.add_row("Bus Factor", str(report.bus_factor))

    if report.release_cadence_days is not None:
        table.add_row("Release Cadence", f"{report.release_cadence_days:.0f} days")
    if report.last_release:
        table.add_row("Last Release", report.last_release)
    if report.issue_response_time_hours is not None:
        table.add_row("Issue Response Time", format_hours(report.issue_response_time_hours))

    console.print(table)

    # Commit sparkline
    if report.weekly_commits:
        values = [c for _, c in report.weekly_commits]
        labels = [w for w, _ in report.weekly_commits]
        console.print(f"\n  Commits: {sparkline(values)}  ({labels[0]} → {labels[-1]})")

    # Top committers
    if report.top_committers:
        ct = Table(title="Top Committers", border_style="dim")
        ct.add_column("Author", style="cyan")
        ct.add_column("Commits", justify="right")
        for login, count in report.top_committers[:10]:
            ct.add_row(login, str(count))
        console.print(ct)

    console.print()


def display_overview(repo: str, overview: dict, triage: TriageReport | None,
                     health: HealthReport | None) -> None:
    """Combined dashboard."""
    console.print()
    info = overview
    lang = (info.get("primaryLanguage") or {}).get("name", "?")
    license_id = (info.get("licenseInfo") or {}).get("spdxId", "?")

    console.print(Panel(
        f"[bold]{info.get('owner', {}).get('login', '')}/{info['name']}[/]"
        f"  {info.get('description', '') or ''}",
        subtitle=f"{lang} | {license_id} | {'Archived' if info.get('isArchived') else 'Active'}",
    ))

    # Quick stats
    st = Table(show_header=False, border_style="dim", title="Quick Stats")
    st.add_column("Metric", style="bold")
    st.add_column("Value")
    st.add_row("Stars", f"{info.get('stargazerCount', 0):,}")
    st.add_row("Forks", f"{info.get('forkCount', 0):,}")
    st.add_row("Open PRs", str(info.get("openPRs", {}).get("totalCount", 0)))
    st.add_row("Merged PRs", str(info.get("mergedPRs", {}).get("totalCount", 0)))
    st.add_row("Open Issues", str(info.get("openIssues", {}).get("totalCount", 0)))
    console.print(st)

    # Releases
    releases = info.get("releases", {}).get("nodes", [])
    if releases:
        console.print("\n[bold]Recent Releases:[/]")
        for r in releases[:3]:
            console.print(f"  {r['tagName']}  [dim]{r['createdAt'][:10]}[/]")

    # Triage summary
    if triage:
        console.print(f"\n[bold]PR Triage:[/] Merge rate {triage.merge_rate:.1f}% | "
                       f"Median {format_hours(triage.median_merge_hours)} | "
                       f"Top merger: {triage.maintainer_stats[0].login if triage.maintainer_stats else '?'}")

    # Health summary
    if health:
        console.print(f"[bold]Health:[/] {health.commits_per_week:.1f} commits/wk | "
                       f"Bus factor: {health.bus_factor} | "
                       f"{health.active_contributors_30d} active contributors")

    console.print()
