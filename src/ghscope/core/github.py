"""GraphQL executor via `gh` subprocess + pagination."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any


class GitHubAPIError(Exception):
    pass


def check_gh_cli() -> None:
    """Verify gh CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            print("Error: gh CLI is not authenticated. Run: gh auth login", file=sys.stderr)
            sys.exit(1)
    except FileNotFoundError:
        print("Error: gh CLI not found. Install: brew install gh", file=sys.stderr)
        sys.exit(1)


def graphql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a GraphQL query via gh api graphql."""
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    if variables:
        for key, value in variables.items():
            if isinstance(value, (int, float, bool)):
                cmd.extend(["-F", f"{key}={value}"])
            else:
                cmd.extend(["-f", f"{key}={value}"])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise GitHubAPIError(f"GraphQL query failed: {stderr}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise GitHubAPIError(f"Invalid JSON response: {e}")

    if "errors" in data:
        msgs = "; ".join(e.get("message", str(e)) for e in data["errors"])
        raise GitHubAPIError(f"GraphQL errors: {msgs}")

    return data.get("data", data)


def paginated_query(
    query_template: str,
    path: list[str],
    variables: dict[str, Any] | None = None,
    limit: int = 100,
    page_size: int = 50,
) -> list[dict[str, Any]]:
    """Auto-paginate a GraphQL connection query.

    query_template must contain $cursor variable and use `after: $cursor`.
    path is the dot-path to the connection (e.g. ["repository", "pullRequests"]).
    """
    all_nodes: list[dict[str, Any]] = []
    cursor: str | None = None
    variables = dict(variables or {})

    while len(all_nodes) < limit:
        remaining = min(page_size, limit - len(all_nodes))
        variables["first"] = remaining

        if cursor is None:
            # First page: remove cursor variable declaration and usage
            import re
            actual_query = re.sub(r',?\s*\$cursor:\s*String!', '', query_template)
            actual_query = actual_query.replace("after: $cursor,", "")
            actual_query = actual_query.replace("after: $cursor", "")
            vars_to_send = {k: v for k, v in variables.items() if k != "cursor"}
        else:
            actual_query = query_template
            variables["cursor"] = cursor
            vars_to_send = variables

        data = graphql(actual_query, vars_to_send)

        # Navigate to the connection
        connection = data
        for key in path:
            connection = connection[key]

        nodes = [edge["node"] for edge in connection.get("edges", [])]
        all_nodes.extend(nodes)

        page_info = connection.get("pageInfo", {})
        if not page_info.get("hasNextPage", False):
            break
        cursor = page_info.get("endCursor")
        if cursor is None:
            break

    return all_nodes[:limit]


def get_viewer_login() -> str:
    """Get the authenticated user's login."""
    data = graphql("query { viewer { login } }")
    return data["viewer"]["login"]
