"""Event parser for GH Archive events."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ParsedEvent:
    """Parsed event data."""

    id: str
    type: str
    actor: dict
    repo: dict
    public: bool
    created_at: datetime
    payload: dict = field(default_factory=dict)

    @property
    def actor_login(self) -> str:
        return self.actor.get("login", "unknown")

    @property
    def actor_id(self) -> str:
        return str(self.actor.get("id", "unknown"))

    @property
    def repo_name(self) -> str:
        return self.repo.get("name", "unknown")

    @property
    def repo_id(self) -> str:
        return str(self.repo.get("id", "unknown"))


@dataclass
class PushEvent:
    """Parsed PushEvent."""

    event: ParsedEvent
    ref: str
    head: str
    commits: list[dict]
    size: int

    @property
    def branch(self) -> str:
        if self.ref.startswith("refs/heads/"):
            return self.ref[11:]
        return self.ref

    @property
    def num_commits(self) -> int:
        return len(self.commits)

    @property
    def additions(self) -> int:
        return sum(c.get("added", 0) for c in self.commits)

    @property
    def deletions(self) -> int:
        return sum(c.get("removed", 0) for c in self.commits)


@dataclass
class PullRequestEvent:
    """Parsed PullRequestEvent."""

    event: ParsedEvent
    action: str
    number: int
    pr: dict

    @property
    def pr_id(self) -> int:
        return self.pr.get("id", 0)

    @property
    def title(self) -> str:
        return self.pr.get("title", "")

    @property
    def body(self) -> str:
        return self.pr.get("body", "")

    @property
    def state(self) -> str:
        return self.pr.get("state", "open")

    @property
    def merged(self) -> bool:
        return self.pr.get("merged", False)

    @property
    def additions(self) -> int:
        return self.pr.get("additions", 0)

    @property
    def deletions(self) -> int:
        return self.pr.get("deletions", 0)

    @property
    def changed_files(self) -> int:
        return self.pr.get("changed_files", 0)


@dataclass
class PullRequestReviewEvent:
    """Parsed PullRequestReviewEvent."""

    event: ParsedEvent
    action: str
    review: dict
    pr: dict

    @property
    def review_state(self) -> str:
        return self.review.get("state", "")

    @property
    def review_body(self) -> str:
        return self.review.get("body", "")

    @property
    def pr_number(self) -> int:
        return self.pr.get("number", 0)


@dataclass
class IssueCommentEvent:
    """Parsed IssueCommentEvent."""

    event: ParsedEvent
    action: str
    comment: dict
    issue: dict | None = None

    @property
    def comment_body(self) -> str:
        return self.comment.get("body", "")

    @property
    def comment_id(self) -> int:
        return self.comment.get("id", 0)

    @property
    def issue_number(self) -> int:
        if self.issue:
            return self.issue.get("number", 0)
        return 0


class EventParser:
    """Parser for GH Archive events."""

    def parse(self, raw_event: dict) -> ParsedEvent | None:
        """Parse a raw event into a ParsedEvent."""
        try:
            return ParsedEvent(
                id=str(raw_event.get("id", "")),
                type=raw_event.get("type", ""),
                actor=raw_event.get("actor", {}),
                repo=raw_event.get("repo", {}),
                public=raw_event.get("public", False),
                created_at=datetime.fromisoformat(
                    raw_event.get("created_at", "").replace("Z", "+00:00")
                ),
                payload=raw_event.get("payload", {}),
            )
        except (KeyError, ValueError):
            return None

    def parse_push_event(self, raw_event: dict) -> PushEvent | None:
        """Parse a PushEvent."""
        parsed = self.parse(raw_event)
        if not parsed:
            return None

        payload = parsed.payload
        return PushEvent(
            event=parsed,
            ref=payload.get("ref", ""),
            head=payload.get("head", ""),
            commits=payload.get("commits", []),
            size=payload.get("size", 0),
        )

    def parse_pull_request_event(self, raw_event: dict) -> PullRequestEvent | None:
        """Parse a PullRequestEvent."""
        parsed = self.parse(raw_event)
        if not parsed:
            return None

        payload = parsed.payload
        return PullRequestEvent(
            event=parsed,
            action=payload.get("action", ""),
            number=payload.get("number", 0),
            pr=payload.get("pull_request", {}),
        )

    def parse_pull_request_review_event(
        self, raw_event: dict
    ) -> PullRequestReviewEvent | None:
        """Parse a PullRequestReviewEvent."""
        parsed = self.parse(raw_event)
        if not parsed:
            return None

        payload = parsed.payload
        return PullRequestReviewEvent(
            event=parsed,
            action=payload.get("action", ""),
            review=payload.get("review", {}),
            pr=payload.get("pull_request", {}),
        )

    def parse_issue_comment_event(self, raw_event: dict) -> IssueCommentEvent | None:
        """Parse an IssueCommentEvent."""
        parsed = self.parse(raw_event)
        if not parsed:
            return None

        payload = parsed.payload
        return IssueCommentEvent(
            event=parsed,
            action=payload.get("action", ""),
            comment=payload.get("comment", {}),
            issue=payload.get("issue"),
        )

    def parse_any(self, raw_event: dict) -> ParsedEvent | PushEvent | PullRequestEvent | None:
        """Parse any event type."""
        event_type = raw_event.get("type", "")

        if event_type == "PushEvent":
            return self.parse_push_event(raw_event)
        elif event_type == "PullRequestEvent":
            return self.parse_pull_request_event(raw_event)
        elif event_type == "PullRequestReviewEvent":
            return self.parse_pull_request_review_event(raw_event)
        elif event_type == "IssueCommentEvent":
            return self.parse_issue_comment_event(raw_event)
        else:
            return self.parse(raw_event)
