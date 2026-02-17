"""CLI entry point — click group with global options and subcommand routing."""

from __future__ import annotations

import sys

import click
from rich.console import Console

from ghscope.core.github import check_gh_cli

console = Console()

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

SUBCOMMANDS = {"triage", "assess", "contribs", "health", "review"}


class GhscopeContext:
    """Shared context passed to all commands."""

    def __init__(self, repo: str, json_output: bool, no_cache: bool,
                 offline: bool, limit: int, days: int, verbose: bool,
                 fmt: str | None = None):
        self.repo = repo
        self.owner, self.name = repo.split("/", 1)
        self.json_output = json_output
        self.no_cache = no_cache
        self.offline = offline
        self.limit = limit
        self.days = days
        self.verbose = verbose
        self.fmt = fmt


class GhscopeGroup(click.Group):
    """Custom group that allows `ghscope <repo>` and `ghscope <cmd> <repo>`."""

    def parse_args(self, ctx, args):
        # If first arg looks like owner/repo (contains / and not a flag),
        # treat it as the default overview command
        if args and "/" in args[0] and not args[0].startswith("-"):
            # `ghscope owner/repo [flags]` -> insert "overview" command
            args = ["overview"] + args
        return super().parse_args(ctx, args)


def _repo_argument(f):
    """Common REPO argument decorator."""
    return click.argument("repo")(f)


def _global_options(f):
    """Common global options decorator."""
    f = click.option("--json", "json_output", is_flag=True, help="Output as JSON")(f)
    f = click.option("--fmt", type=click.Choice(["csv", "parquet", "rich", "md"]), default=None,
                     help="Output format: csv, parquet, rich, or md (default: terminal scorecard)")(f)
    f = click.option("--no-cache", is_flag=True, help="Bypass cache")(f)
    f = click.option("--offline", is_flag=True, help="Use cached data only")(f)
    f = click.option("--limit", "-l", default=100, show_default=True, help="Max items to fetch")(f)
    f = click.option("--days", "-d", default=90, show_default=True, help="Lookback period in days")(f)
    f = click.option("--verbose", "-v", is_flag=True, help="Verbose output")(f)
    return f


def _make_context(repo, json_output, no_cache, offline, limit, days, verbose,
                  fmt=None):
    if "/" not in repo:
        console.print("[red]Error:[/] REPO must be owner/repo format (e.g. facebook/react)")
        sys.exit(1)
    if not offline:
        check_gh_cli()
    return GhscopeContext(repo, json_output, no_cache, offline, limit, days,
                          verbose, fmt=fmt)


@click.group(cls=GhscopeGroup, context_settings=CONTEXT_SETTINGS)
def main():
    """GitHub repository intelligence from your terminal.

    \b
    Usage:
      ghscope <owner/repo>               Scorecard overview (default)
      ghscope triage <owner/repo>         PR merge patterns
      ghscope review <owner/repo>         Review bottlenecks & reviewer stats
      ghscope contribs <owner/repo>       Contributor dynamics & first-timer retention
      ghscope health <owner/repo>         Commit velocity & bus factor
      ghscope assess <owner/repo>         Your open PRs' merge likelihood
    """
    pass


@main.command("overview")
@_repo_argument
@_global_options
def overview_cmd(repo, json_output, fmt, no_cache, offline, limit, days, verbose):
    """Scorecard overview — synthesized intelligence (default)."""
    ctx = _make_context(repo, json_output, no_cache, offline, limit, days, verbose, fmt=fmt)
    from ghscope.commands.overview import run_overview
    run_overview(ctx)


@main.command("triage")
@_repo_argument
@_global_options
def triage_cmd(repo, json_output, fmt, no_cache, offline, limit, days, verbose):
    """PR merge patterns & maintainer responsiveness."""
    ctx = _make_context(repo, json_output, no_cache, offline, limit, days, verbose, fmt=fmt)
    from ghscope.commands.triage import run_triage
    run_triage(ctx)


@main.command("assess")
@_repo_argument
@_global_options
def assess_cmd(repo, json_output, fmt, no_cache, offline, limit, days, verbose):
    """Likelihood your open PRs get merged."""
    ctx = _make_context(repo, json_output, no_cache, offline, limit, days, verbose, fmt=fmt)
    from ghscope.commands.assess import run_assess
    run_assess(ctx)


@main.command("contribs")
@_repo_argument
@_global_options
def contribs_cmd(repo, json_output, fmt, no_cache, offline, limit, days, verbose):
    """Contributor dynamics & first-timer retention."""
    ctx = _make_context(repo, json_output, no_cache, offline, limit, days, verbose, fmt=fmt)
    from ghscope.commands.contribs import run_contribs
    run_contribs(ctx)


@main.command("review")
@_repo_argument
@_global_options
def review_cmd(repo, json_output, fmt, no_cache, offline, limit, days, verbose):
    """Review bottlenecks & reviewer stats."""
    ctx = _make_context(repo, json_output, no_cache, offline, limit, days, verbose, fmt=fmt)
    from ghscope.commands.review import run_review
    run_review(ctx)


@main.command("health")
@_repo_argument
@_global_options
def health_cmd(repo, json_output, fmt, no_cache, offline, limit, days, verbose):
    """Commit velocity, release cadence, bus factor."""
    ctx = _make_context(repo, json_output, no_cache, offline, limit, days, verbose, fmt=fmt)
    from ghscope.commands.health import run_health
    run_health(ctx)
