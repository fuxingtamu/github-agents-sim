"""Behavior extractor for mining developer patterns."""

from dataclasses import dataclass, field
from typing import Any

from .event_parser import (
    IssueCommentEvent,
    ParsedEvent,
    PullRequestEvent,
    PullRequestReviewEvent,
    PushEvent,
)


@dataclass
class DeveloperProfile:
    """Extracted developer profile."""

    login: str
    developer_id: str

    # Activity stats
    total_commits: int = 0
    total_prs: int = 0
    total_reviews: int = 0
    total_comments: int = 0

    # Behavior patterns
    avg_commits_per_day: float = 0.0
    avg_pr_description_length: float = 0.0
    avg_review_length: float = 0.0
    avg_response_hours: float = 24.0

    # Personality traits (0-1 scale)
    strictness: float = 0.5
    communication: float = 0.5
    response_speed: float = 0.5
    cooperation: float = 0.5
    formality: float = 0.5
    emoji_usage: float = 0.0

    # Preferred repos
    repos: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "login": self.login,
            "developer_id": self.developer_id,
            "total_commits": self.total_commits,
            "total_prs": self.total_prs,
            "total_reviews": self.total_reviews,
            "total_comments": self.total_comments,
            "avg_commits_per_day": self.avg_commits_per_day,
            "avg_pr_description_length": self.avg_pr_description_length,
            "avg_review_length": self.avg_review_length,
            "avg_response_hours": self.avg_response_hours,
            "strictness": self.strictness,
            "communication": self.communication,
            "response_speed": self.response_speed,
            "cooperation": self.cooperation,
            "formality": self.formality,
            "emoji_usage": self.emoji_usage,
            "repos": list(self.repos),
        }


class BehaviorExtractor:
    """Extract behavior patterns from parsed events."""

    def __init__(self):
        """Initialize the extractor."""
        self.profiles: dict[str, DeveloperProfile] = {}
        self.event_timestamps: dict[str, list] = {}

    def process_event(self, event: ParsedEvent | PushEvent | PullRequestEvent | PullRequestReviewEvent | IssueCommentEvent) -> None:
        """Process a single event and update profiles."""
        if isinstance(event, PushEvent):
            self._process_push(event)
        elif isinstance(event, PullRequestEvent):
            self._process_pr(event)
        elif isinstance(event, PullRequestReviewEvent):
            self._process_review(event)
        elif isinstance(event, IssueCommentEvent):
            self._process_comment(event)
        else:
            self._process_basic(event)

    def _get_profile(self, actor_id: str, login: str) -> DeveloperProfile:
        """Get or create a profile."""
        if actor_id not in self.profiles:
            self.profiles[actor_id] = DeveloperProfile(
                login=login,
                developer_id=actor_id,
            )
        return self.profiles[actor_id]

    def _process_basic(self, event: ParsedEvent) -> None:
        """Process basic event."""
        profile = self._get_profile(event.actor_id, event.actor_login)
        profile.repos.add(event.repo_name)

    def _process_push(self, event: PushEvent) -> None:
        """Process push event."""
        profile = self._get_profile(
            event.event.actor_id,
            event.event.actor_login,
        )
        profile.total_commits += event.num_commits
        profile.repos.add(event.event.repo_name)

    def _process_pr(self, event: PullRequestEvent) -> None:
        """Process pull request event."""
        profile = self._get_profile(
            event.event.actor_id,
            event.event.actor_login,
        )
        profile.total_prs += 1
        profile.repos.add(event.event.repo_name)

        # Track PR description length
        if event.body:
            profile.avg_pr_description_length = (
                profile.avg_pr_description_length * (profile.total_prs - 1)
                + len(event.body)
            ) / profile.total_prs

    def _process_review(self, event: PullRequestReviewEvent) -> None:
        """Process review event."""
        profile = self._get_profile(
            event.event.actor_id,
            event.event.actor_login,
        )
        profile.total_reviews += 1

        # Track review length
        if event.review_body:
            profile.avg_review_length = (
                profile.avg_review_length * (profile.total_reviews - 1)
                + len(event.review_body)
            ) / profile.total_reviews

        # Update strictness based on review state
        if event.review_state == "changes_requested":
            profile.strictness = min(1.0, profile.strictness + 0.1)
        elif event.review_state == "approved":
            profile.strictness = max(0.0, profile.strictness - 0.05)

    def _process_comment(self, event: IssueCommentEvent) -> None:
        """Process comment event."""
        profile = self._get_profile(
            event.event.actor_id,
            event.event.actor_login,
        )
        profile.total_comments += 1
        profile.repos.add(event.event.repo_name)

        # Track communication
        body = event.comment_body
        if body:
            profile.communication = min(1.0, profile.communication + 0.01)

            # Check for emoji usage
            emojis = sum(1 for c in body if ord(c) > 0x1F000)
            if emojis > 0:
                profile.emoji_usage = min(1.0, profile.emoji_usage + 0.05)

            # Check for @mentions (cooperation indicator)
            if "@" in body:
                profile.cooperation = min(1.0, profile.cooperation + 0.02)

    def calculate_traits(self) -> None:
        """Calculate final personality traits for all profiles."""
        for profile in self.profiles.values():
            # Normalize communication
            profile.communication = min(1.0, profile.communication)

            # Response speed based on activity
            if profile.total_comments > 0:
                profile.response_speed = min(
                    1.0,
                    (profile.total_comments + profile.total_reviews) / 100,
                )

            # Formality based on avg lengths
            if profile.avg_pr_description_length > 200:
                profile.formality = 0.8
            elif profile.avg_pr_description_length > 50:
                profile.formality = 0.5
            else:
                profile.formality = 0.3

    def get_profiles(self) -> list[DeveloperProfile]:
        """Get all profiles."""
        self.calculate_traits()
        return list(self.profiles.values())

    def infer_persona(self, profile: DeveloperProfile) -> str:
        """Infer persona type from profile traits."""
        if profile.strictness > 0.7 and profile.communication < 0.5:
            return "gatekeeper"
        elif profile.cooperation > 0.7 and profile.communication > 0.6:
            return "mentor"
        elif profile.response_speed > 0.7 and profile.communication < 0.3:
            return "ninja"
        elif profile.communication > 0.7 and profile.cooperation > 0.6:
            return "collaborator"
        elif profile.total_reviews > profile.total_prs * 2:
            return "bug_hunter"
        else:
            return "architect"
