# CLAUDE.md — ghscope

## Git Rules
- NEVER add Co-Authored-By, co-authored-by, or any attribution to Claude/Anthropic in commit messages
- NEVER include any evidence of AI assistance in commits, PRs, or code comments
- All commits must appear as solely authored by the repo owner

## Project
- Python 3.13 at `/opt/homebrew/opt/python@3.13/bin/python3.13`
- Install: `pip3.13 install --break-system-packages -e .`
- Entry point: `ghscope.cli:main`

## Output Preferences
- Default CLI output: terminal scorecard (signal/value/read via Rich)
- `--fmt md` for markdown tables
- Python API: `import ghscope.api as gs` → ibis tables → `.to_polars()`
- When showing results in chat, always render as markdown table so it doesn't collapse
