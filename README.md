# ghscope

GitHub repository intelligence from your terminal.

Quickly understand any GitHub repo's review bottlenecks, contributor dynamics, merge patterns, and project health — all from the command line using the `gh` CLI you already have installed.

## Requirements

- Python 3.12+
- [`gh` CLI](https://cli.github.com/) installed and authenticated (`gh auth login`)

## Install

```bash
pip install ghscope
```

Or install from source:

```bash
git clone https://github.com/ChrisPachulski/ghscope.git
cd ghscope
pip install -e .
```

## Quick start

```bash
ghscope mtgjson/mtgjson
```

```
  mtgjson/mtgjson by the numbers
  ────────────────────────────────────────────────────────────────

  review_coverage                  31%  │ partial coverage — room to improve
  reviewer_spread        1 (ZeldaZach)  │ sole gatekeeper · 11.7h avg turnaround
  active_contributors                4  │ 4 people active in last 30d
  bus_factor                         1  │ single point of failure
  commit_velocity               7.8/wk  │ ZeldaZach dominates (51/100, 51%)
  release_cadence                 376d  │ last: 5.3.0
  issue_response                 15.5d  │ very slow · over a week
  merge_rate                     60.2%  │ median 32m · p75 7.4h
  top_merger           ZeldaZach (100)  │ ZeldaZach is the sole merger
  first_timers                       4  │ 75% merge rate · 25% retention
  top_contributor       ZeldaZach (41)  │ 77% merge rate
  unreviewed_prs                     1  │ 0 stale · oldest waiting 5.2h
```

The default scorecard synthesizes review, health, triage, and contributor signals into a single signal/value/read table.

## Commands

```
ghscope <owner/repo>               Scorecard overview (default)
ghscope triage <owner/repo>        PR merge patterns & maintainer responsiveness
ghscope review <owner/repo>        Review bottlenecks & reviewer stats
ghscope contribs <owner/repo>      Contributor dynamics & first-timer retention
ghscope health <owner/repo>        Commit velocity, release cadence, bus factor
ghscope assess <owner/repo>        Likelihood your open PRs get merged
```

### triage

Merge rates, merge time distributions (median/p25/p75), maintainer stats, batch merge detection, and category breakdown.

### review

Review coverage, reviewer concentration, turnaround times, approval/changes-requested/comment-only breakdown, stale PRs, and unreviewed open PRs.

### contribs

Total/repeat/one-time contributors, first-timer merge rate and retention, top contributors by merge count, and spam PR detection.

### health

Commits per week, active contributors (30d), bus factor, release cadence, issue response time, and top committers.

### assess

For each of your open PRs in a repo, estimates merge probability based on historical patterns — size, category, review count, and age.

## Output formats

| Flag | Format | Use case |
|------|--------|----------|
| *(default)* | Terminal scorecard | Human-readable terminal output |
| `--fmt md` | Markdown table | GitHub READMEs, Notion, chat |
| `--fmt csv` | CSV to stdout | Pipe into other tools |
| `--fmt parquet` | Parquet files | Data analysis workflows |
| `--fmt rich` | Rich tables | Decorated terminal tables |
| `--json` | JSON | Programmatic consumption |

## Python API

Every command is available as a Python function returning ibis tables — materialize to polars or pandas:

```python
import ghscope.api as gs

# Scorecard — single ibis.Table
scorecard = gs.scorecard("mtgjson/mtgjson")
scorecard.to_polars()

# Individual reports — dict[str, ibis.Table]
tables = gs.review("mtgjson/mtgjson")
tables["reviewers"].to_polars()
tables["summary"].to_pandas()

# All commands: gs.triage(), gs.review(), gs.contribs(), gs.health(), gs.assess()
# All accept: repo, limit=100, days=90, no_cache=False, offline=False
```

## Flags

| Flag | Description |
|------|-------------|
| `--fmt` | Output format: `csv`, `parquet`, `rich`, or `md` |
| `--json` | Output as JSON |
| `--no-cache` | Bypass cache, fetch fresh data |
| `--offline` | Use cached data only (no API calls) |
| `--limit`, `-l` | Max items to fetch (default: 100) |
| `--days`, `-d` | Lookback period in days (default: 90) |
| `-v`, `--verbose` | Verbose output |

## How it works

ghscope uses GitHub's GraphQL API via the `gh` CLI — no API tokens to manage. Query results are cached in a SQLite database at `~/.ghscope/` so repeat queries are instant and you can use `--offline` for air-gapped analysis.

## License

MIT
