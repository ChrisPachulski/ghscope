"""Data models as dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PRSummary:
    number: int
    title: str
    author: str
    state: str  # MERGED, CLOSED, OPEN
    created_at: datetime
    merged_at: datetime | None = None
    closed_at: datetime | None = None
    merged_by: str | None = None
    labels: list[str] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    review_count: int = 0
    category: str = "other"
    time_to_merge_hours: float | None = None

    @property
    def size(self) -> str:
        total = self.additions + self.deletions
        if total <= 10:
            return "XS"
        elif total <= 50:
            return "S"
        elif total <= 200:
            return "M"
        elif total <= 500:
            return "L"
        else:
            return "XL"

    @property
    def age_hours(self) -> float:
        end = self.merged_at or self.closed_at or datetime.now(timezone.utc)
        # Ensure both are naive for comparison
        end_naive = end.replace(tzinfo=None) if end.tzinfo else end
        created_naive = self.created_at.replace(tzinfo=None) if self.created_at.tzinfo else self.created_at
        return (end_naive - created_naive).total_seconds() / 3600


@dataclass
class MaintainerStats:
    login: str
    merge_count: int
    avg_merge_time_hours: float


@dataclass
class BatchCluster:
    merger: str
    count: int
    start_time: datetime
    end_time: datetime
    prs: list[int]  # PR numbers


@dataclass
class TriageReport:
    repo: str
    total_merged: int
    total_closed: int
    total_open: int
    merge_rate: float
    median_merge_hours: float
    p25_merge_hours: float
    p75_merge_hours: float
    maintainer_stats: list[MaintainerStats]
    batch_clusters: list[BatchCluster]
    category_breakdown: dict[str, dict[str, int | float]]
    # category -> { count, merge_rate, median_hours }


@dataclass
class PRAssessment:
    pr: PRSummary
    probability: int  # 0-100
    factors: list[str]
    similar_merged: list[PRSummary]
    similar_closed: list[PRSummary]


@dataclass
class AssessmentReport:
    repo: str
    user: str
    assessments: list[PRAssessment]


@dataclass
class ContributorStats:
    login: str
    merged_count: int
    closed_count: int
    open_count: int
    first_contribution: datetime
    merge_rate: float


@dataclass
class ContributorReport:
    repo: str
    total_contributors: int
    top_contributors: list[ContributorStats]
    repeat_contributors: int  # 2+ merged PRs
    one_time_contributors: int
    spam_prs: list[PRSummary]
    first_timers: int = 0
    first_timer_merge_rate: float = 0.0
    first_timer_median_merge_hours: float | None = None
    repeat_median_merge_hours: float | None = None
    retained_first_timers: int = 0
    retention_rate: float = 0.0


@dataclass
class ReviewerStats:
    login: str
    review_count: int
    avg_turnaround_hours: float
    approval_count: int
    changes_requested_count: int
    comment_only_count: int


@dataclass
class ReviewReport:
    repo: str
    total_reviewed_prs: int
    total_unreviewed_merged: int
    review_coverage: float  # % of merged PRs with at least 1 review
    median_first_review_hours: float | None
    median_review_to_merge_hours: float | None
    reviewer_stats: list[ReviewerStats]
    reviewer_concentration: int  # how many reviewers cover 50% of reviews
    unreviewed_open_prs: list[PRSummary]  # open PRs with 0 reviews
    stale_review_prs: list[PRSummary]  # open PRs waiting >7 days for review


@dataclass
class HealthReport:
    repo: str
    commits_per_week: float
    active_contributors_30d: int
    release_cadence_days: float | None
    last_release: str | None
    issue_response_time_hours: float | None
    bus_factor: int
    top_committers: list[tuple[str, int]]
    weekly_commits: list[tuple[str, int]]  # (week_label, count) for sparkline
