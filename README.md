# ghscope

GitHub repository intelligence from your terminal.

Quickly understand any GitHub repo's PR patterns, contributor dynamics, and project health — all from the command line using the `gh` CLI you already have installed.

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

## Usage

```
ghscope <owner/repo>                 Full overview dashboard (default)
ghscope triage <owner/repo>          PR merge patterns & maintainer responsiveness
ghscope assess <owner/repo>          Likelihood your open PRs get merged
ghscope contribs <owner/repo>        Contributor dynamics & spam detection
ghscope health <owner/repo>          Commit velocity, release cadence, bus factor
```

### Example

```
$ ghscope triage facebook/react

╭─────────────────────────────────────────╮
│ facebook/react — PR Triage Analysis     │
╰─ Merged: 87  Closed: 34  Open: 12 ─────╯

       Merge Statistics
┌──────────────────┬────────┐
│ Merge Rate       │ 71.9%  │
│ Median Merge Time│ 2.3d   │
│ P25 (Fast)       │ 4.2h   │
│ P75 (Slow)       │ 8.1d   │
└──────────────────┴────────┘

         Top Mergers
┌────────────┬────────┬──────────┐
│ Maintainer │ Merges │ Avg Time │
├────────────┼────────┼──────────┤
│ rickhanlonii│    23 │ 1.8d     │
│ acdlite    │    19 │ 3.2d     │
│ eps1lon    │    15 │ 1.1d     │
└────────────┴────────┴──────────┘
```

## Flags

| Flag | Description |
|------|-------------|
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
