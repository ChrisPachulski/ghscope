"""Statistical logic — merge times, batch detection, similarity, probability."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import median, quantiles

from ghscope.core.models import (
    BatchCluster, ContributorStats, MaintainerStats, PRAssessment, PRSummary,
)


def parse_datetime(s: str | None) -> datetime | None:
    if not s:
        return None
    # GitHub ISO format: 2024-01-15T10:30:00Z
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def parse_pr_node(node: dict, state: str) -> PRSummary:
    """Convert a GraphQL PR node to PRSummary."""
    author = (node.get("author") or {}).get("login", "ghost")
    labels = [l["name"] for l in (node.get("labels", {}).get("nodes", []))]
    created = parse_datetime(node["createdAt"])
    merged = parse_datetime(node.get("mergedAt"))
    closed = parse_datetime(node.get("closedAt"))
    merged_by = (node.get("mergedBy") or {}).get("login")

    pr = PRSummary(
        number=node["number"],
        title=node["title"],
        author=author,
        state=state,
        created_at=created,
        merged_at=merged,
        closed_at=closed,
        merged_by=merged_by,
        labels=labels,
        additions=node.get("additions", 0),
        deletions=node.get("deletions", 0),
        changed_files=node.get("changedFiles", 0),
        review_count=node.get("reviews", {}).get("totalCount", 0),
    )
    pr.category = categorize_pr(pr.title, pr.labels)
    if pr.merged_at and pr.created_at:
        pr.time_to_merge_hours = (pr.merged_at - pr.created_at).total_seconds() / 3600
    return pr


def categorize_pr(title: str, labels: list[str]) -> str:
    """Categorize a PR from title prefixes, labels, and keywords."""
    title_lower = title.lower().strip()
    labels_lower = [l.lower() for l in labels]

    # Check conventional commit prefixes
    for prefix, cat in [
        ("fix", "fix"), ("bug", "fix"),
        ("feat", "feat"), ("feature", "feat"),
        ("doc", "docs"), ("readme", "docs"),
        ("dep", "deps"), ("bump", "deps"), ("upgrade", "deps"), ("chore(deps)", "deps"),
        ("refactor", "refactor"), ("cleanup", "refactor"), ("clean up", "refactor"),
        ("test", "test"), ("ci", "ci"), ("chore", "chore"),
    ]:
        if title_lower.startswith(prefix):
            return cat

    # Check labels
    for label in labels_lower:
        if "bug" in label or "fix" in label:
            return "fix"
        if "feature" in label or "enhancement" in label:
            return "feat"
        if "documentation" in label or "docs" in label:
            return "docs"
        if "dependencies" in label or "deps" in label:
            return "deps"

    # Check title keywords
    if re.search(r"\bdependabot\b|\brenovate\b|\bbump\b", title_lower):
        return "deps"
    if re.search(r"\bfix(es|ed)?\b", title_lower):
        return "fix"
    if re.search(r"\badd(s|ed)?\b|\bimplement\b", title_lower):
        return "feat"

    return "other"


def compute_merge_times(prs: list[PRSummary]) -> tuple[float, float, float]:
    """Compute median, p25, p75 merge times in hours. Returns (0, 0, 0) if no data."""
    times = [pr.time_to_merge_hours for pr in prs if pr.time_to_merge_hours is not None]
    if not times:
        return 0.0, 0.0, 0.0
    if len(times) == 1:
        return times[0], times[0], times[0]
    med = median(times)
    if len(times) < 4:
        return med, min(times), max(times)
    q = quantiles(times, n=4)
    return med, q[0], q[2]


def detect_batch_merges(prs: list[PRSummary], window_minutes: int = 30) -> list[BatchCluster]:
    """Cluster merges by time proximity + same merger."""
    merged = [p for p in prs if p.merged_at and p.merged_by]
    merged.sort(key=lambda p: p.merged_at)

    clusters: list[BatchCluster] = []
    if not merged:
        return clusters

    current_group = [merged[0]]
    for pr in merged[1:]:
        prev = current_group[-1]
        same_merger = pr.merged_by == prev.merged_by
        within_window = (pr.merged_at - prev.merged_at).total_seconds() < window_minutes * 60
        if same_merger and within_window:
            current_group.append(pr)
        else:
            if len(current_group) >= 3:
                clusters.append(BatchCluster(
                    merger=current_group[0].merged_by,
                    count=len(current_group),
                    start_time=current_group[0].merged_at,
                    end_time=current_group[-1].merged_at,
                    prs=[p.number for p in current_group],
                ))
            current_group = [pr]

    if len(current_group) >= 3:
        clusters.append(BatchCluster(
            merger=current_group[0].merged_by,
            count=len(current_group),
            start_time=current_group[0].merged_at,
            end_time=current_group[-1].merged_at,
            prs=[p.number for p in current_group],
        ))

    return clusters


def compute_maintainer_stats(prs: list[PRSummary]) -> list[MaintainerStats]:
    """Stats per merger: count and average merge time."""
    by_merger: dict[str, list[PRSummary]] = defaultdict(list)
    for pr in prs:
        if pr.merged_by and pr.state == "MERGED":
            by_merger[pr.merged_by].append(pr)

    stats = []
    for login, merged_prs in by_merger.items():
        times = [p.time_to_merge_hours for p in merged_prs if p.time_to_merge_hours is not None]
        avg_time = sum(times) / len(times) if times else 0
        stats.append(MaintainerStats(login=login, merge_count=len(merged_prs), avg_merge_time_hours=avg_time))

    stats.sort(key=lambda s: s.merge_count, reverse=True)
    return stats


def category_breakdown(merged: list[PRSummary], closed: list[PRSummary]) -> dict[str, dict]:
    """Per-category: count, merge rate, median merge time."""
    cats: dict[str, dict] = {}

    merged_by_cat = defaultdict(list)
    closed_by_cat = defaultdict(int)

    for pr in merged:
        merged_by_cat[pr.category].append(pr)
    for pr in closed:
        closed_by_cat[pr.category] += 1

    all_cats = set(merged_by_cat.keys()) | set(closed_by_cat.keys())
    for cat in sorted(all_cats):
        m_list = merged_by_cat.get(cat, [])
        c_count = closed_by_cat.get(cat, 0)
        total = len(m_list) + c_count
        rate = len(m_list) / total * 100 if total > 0 else 0
        times = [p.time_to_merge_hours for p in m_list if p.time_to_merge_hours is not None]
        med = median(times) if times else 0
        cats[cat] = {"count": total, "merged": len(m_list), "merge_rate": round(rate, 1), "median_hours": round(med, 1)}

    return cats


def compute_merge_probability(
    target: PRSummary,
    merged: list[PRSummary],
    closed: list[PRSummary],
) -> tuple[int, list[str]]:
    """Score 0-100 merge probability for an open PR."""
    factors: list[str] = []
    score = 50.0  # base

    # 1. Base merge rate
    total = len(merged) + len(closed)
    if total > 0:
        base_rate = len(merged) / total
        adj = (base_rate - 0.5) * 30
        score += adj
        factors.append(f"Base merge rate: {base_rate:.0%}")

    # 2. Category-specific rate
    cat_merged = [p for p in merged if p.category == target.category]
    cat_closed = [p for p in closed if p.category == target.category]
    cat_total = len(cat_merged) + len(cat_closed)
    if cat_total >= 3:
        cat_rate = len(cat_merged) / cat_total
        adj = (cat_rate - 0.5) * 15
        score += adj
        factors.append(f"{target.category} merge rate: {cat_rate:.0%}")

    # 3. Author history
    author_merged = [p for p in merged if p.author == target.author]
    author_closed = [p for p in closed if p.author == target.author]
    if author_merged:
        factors.append(f"Author has {len(author_merged)} merged PR(s)")
        score += min(len(author_merged) * 3, 15)
    if author_closed:
        score -= min(len(author_closed) * 2, 10)

    # 4. Size factor — smaller PRs merge more often
    size_bonus = {"XS": 8, "S": 5, "M": 0, "L": -5, "XL": -10}
    score += size_bonus.get(target.size, 0)
    factors.append(f"Size: {target.size} ({target.additions}+/{target.deletions}-)")

    # 5. Has reviews
    if target.review_count > 0:
        score += 10
        factors.append(f"Has {target.review_count} review(s)")
    else:
        score -= 5
        factors.append("No reviews yet")

    # 6. Age penalty — very old open PRs are less likely
    age_days = target.age_hours / 24
    if age_days > 60:
        score -= 15
        factors.append(f"Open for {age_days:.0f} days (stale)")
    elif age_days > 30:
        score -= 8
        factors.append(f"Open for {age_days:.0f} days")
    elif age_days < 7:
        factors.append(f"Open for {age_days:.1f} days (recent)")

    return max(0, min(100, int(score))), factors


def find_similar_prs(target: PRSummary, candidates: list[PRSummary], top_n: int = 3) -> list[PRSummary]:
    """Find similar PRs by Jaccard similarity on title tokens + category + size."""
    target_tokens = set(re.findall(r'\w+', target.title.lower()))

    scored = []
    for pr in candidates:
        pr_tokens = set(re.findall(r'\w+', pr.title.lower()))
        if not target_tokens or not pr_tokens:
            jaccard = 0.0
        else:
            jaccard = len(target_tokens & pr_tokens) / len(target_tokens | pr_tokens)
        # Bonus for same category and size
        bonus = 0.0
        if pr.category == target.category:
            bonus += 0.2
        if pr.size == target.size:
            bonus += 0.1
        scored.append((jaccard + bonus, pr))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [pr for _, pr in scored[:top_n]]


def detect_spam_prs(prs: list[PRSummary]) -> list[PRSummary]:
    """Detect likely spam: closed <5min, generic titles, zero merges from author."""
    spam = []
    # Count merges per author to find authors with zero merges
    merged_authors = {p.author for p in prs if p.state == "MERGED"}

    generic_patterns = re.compile(
        r'^(update|edit|patch|change)\s+(readme|file|code)', re.IGNORECASE
    )

    for pr in prs:
        if pr.state != "CLOSED":
            continue
        # Closed very quickly
        if pr.closed_at and pr.created_at:
            minutes = (pr.closed_at - pr.created_at).total_seconds() / 60
            if minutes < 5 and pr.author not in merged_authors:
                spam.append(pr)
                continue
        # Generic title + no merges
        if generic_patterns.match(pr.title) and pr.author not in merged_authors:
            spam.append(pr)

    return spam


def compute_contributor_stats(
    merged: list[PRSummary],
    closed: list[PRSummary],
    open_prs: list[PRSummary],
) -> list[ContributorStats]:
    """Per-contributor stats."""
    authors: dict[str, dict] = defaultdict(lambda: {"merged": 0, "closed": 0, "open": 0, "first": None})

    for pr in merged:
        d = authors[pr.author]
        d["merged"] += 1
        if d["first"] is None or pr.created_at < d["first"]:
            d["first"] = pr.created_at
    for pr in closed:
        d = authors[pr.author]
        d["closed"] += 1
        if d["first"] is None or pr.created_at < d["first"]:
            d["first"] = pr.created_at
    for pr in open_prs:
        d = authors[pr.author]
        d["open"] += 1
        if d["first"] is None or pr.created_at < d["first"]:
            d["first"] = pr.created_at

    stats = []
    for login, d in authors.items():
        total = d["merged"] + d["closed"]
        rate = d["merged"] / total if total > 0 else 0
        stats.append(ContributorStats(
            login=login,
            merged_count=d["merged"],
            closed_count=d["closed"],
            open_count=d["open"],
            first_contribution=d["first"],
            merge_rate=round(rate * 100, 1),
        ))

    stats.sort(key=lambda s: s.merged_count, reverse=True)
    return stats


def compute_bus_factor(prs: list[PRSummary], days: int = 90) -> tuple[int, list[tuple[str, int]]]:
    """People responsible for >50% of merges. Returns (bus_factor, top_mergers)."""
    cutoff = datetime.now() - timedelta(days=days)
    # Use timezone-naive comparison
    recent = [p for p in prs if p.merged_at and p.merged_by and p.merged_at.replace(tzinfo=None) > cutoff]
    if not recent:
        return 0, []

    merger_counts = Counter(p.merged_by for p in recent)
    total = sum(merger_counts.values())
    sorted_mergers = merger_counts.most_common()

    cumulative = 0
    bus_factor = 0
    for login, count in sorted_mergers:
        cumulative += count
        bus_factor += 1
        if cumulative / total >= 0.5:
            break

    return bus_factor, sorted_mergers[:10]
