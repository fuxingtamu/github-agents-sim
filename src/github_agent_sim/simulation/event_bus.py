"""Event bus for agent communication."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4


@dataclass
class Event:
    """Event in the system."""

    id: str
    event_type: str
    source: str
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class EventBus:
    """
    Event bus for publish/subscribe communication.

    Allows agents to publish events and subscribe to event types.
    """

    def __init__(self):
        """Initialize event bus."""
        self._subscribers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)
        self._history: list[Event] = []
        self._lock = asyncio.Lock()

    def subscribe(
        self,
        event_type: str,
        callback: Callable[[Event], None],
    ) -> str:
        """
        Subscribe to an event type.

        Args:
            event_type: Event type to subscribe to
            callback: Callback function

        Returns:
            Subscription ID
        """
        subscription_id = str(uuid4())[:8]
        self._subscribers[event_type].append(callback)
        return subscription_id

    def unsubscribe(self, event_type: str, subscription_id: str) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: Event type
            subscription_id: Subscription ID
        """
        # In a real implementation, we'd track subscription IDs
        # For now, this is a placeholder
        pass

    def publish(self, event_type: str, source: str, data: dict[str, Any]) -> Event:
        """
        Publish an event.

        Args:
            event_type: Event type
            source: Source agent ID
            data: Event data

        Returns:
            Published event
        """
        event = Event(
            id=str(uuid4())[:8],
            event_type=event_type,
            source=source,
            data=data,
        )

        # Store in history
        self._history.append(event)

        # Notify subscribers
        for callback in self._subscribers.get(event_type, []):
            try:
                callback(event)
            except Exception:
                pass  # Don't let subscriber errors break the bus

        return event

    def publish_async(self, event_type: str, source: str, data: dict[str, Any]) -> Event:
        """
        Publish an event asynchronously.

        Args:
            event_type: Event type
            source: Source agent ID
            data: Event data

        Returns:
            Published event
        """
        event = Event(
            id=str(uuid4())[:8],
            event_type=event_type,
            source=source,
            data=data,
        )

        # Store in history
        self._history.append(event)

        # Schedule async notifications
        for callback in self._subscribers.get(event_type, []):
            asyncio.create_task(self._notify_async(callback, event))

        return event

    async def _notify_async(
        self,
        callback: Callable[[Event], None],
        event: Event,
    ) -> None:
        """Notify a callback asynchronously."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception:
            pass

    def get_history(
        self,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """
        Get event history.

        Args:
            event_type: Filter by event type
            limit: Maximum events to return

        Returns:
            List of events
        """
        if event_type:
            return [
                e for e in self._history
                if e.event_type == event_type
            ][-limit:]
        return self._history[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()


# Event types
class EventTypes:
    """Standard event types."""

    # Git events
    COMMIT_CREATED = "commit.created"
    BRANCH_CREATED = "branch.created"
    BRANCH_DELETED = "branch.deleted"
    MERGE_STARTED = "merge.started"
    MERGE_COMPLETED = "merge.completed"
    CONFLICT_DETECTED = "conflict.detected"

    # PR events
    PR_CREATED = "pr.created"
    PR_UPDATED = "pr.updated"
    PR_MERGED = "pr.merged"
    PR_CLOSED = "pr.closed"
    PR_ASSIGNED = "pr.assigned"

    # Review events
    REVIEW_STARTED = "review.started"
    REVIEW_SUBMITTED = "review.submitted"
    REVIEW_APPROVED = "review.approved"
    REVIEW_CHANGES_REQUESTED = "review.changes_requested"

    # Comment events
    COMMENT_ADDED = "comment.added"
    MENTION_CREATED = "mention.created"

    # Issue events
    ISSUE_CREATED = "issue.created"
    ISSUE_CLOSED = "issue.closed"
    ISSUE_ASSIGNED = "issue.assigned"
    ISSUE_LABELED = "issue.labeled"

    # CI/CD events
    CI_STARTED = "ci.started"
    CI_COMPLETED = "ci.completed"
    CI_FAILED = "ci.failed"


# Global event bus instance
_global_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus
