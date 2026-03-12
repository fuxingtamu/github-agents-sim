"""Tests for event bus module."""

import pytest

from github_agent_sim.simulation.event_bus import EventBus, Event, EventTypes, get_event_bus


@pytest.fixture
def event_bus():
    """Create a fresh event bus."""
    bus = EventBus()
    yield bus
    bus.clear_history()


def test_subscribe_and_publish(event_bus):
    """Test basic subscribe and publish."""
    received_events = []

    def callback(event):
        received_events.append(event)

    event_bus.subscribe("test.event", callback)
    event_bus.publish("test.event", "sender", {"data": "value"})

    assert len(received_events) == 1
    assert received_events[0].event_type == "test.event"
    assert received_events[0].source == "sender"


def test_subscribe_multiple(event_bus):
    """Test multiple subscribers for same event."""
    events1 = []
    events2 = []

    def callback1(event):
        events1.append(event)

    def callback2(event):
        events2.append(event)

    event_bus.subscribe("test.event", callback1)
    event_bus.subscribe("test.event", callback2)

    event_bus.publish("test.event", "sender", {})

    assert len(events1) == 1
    assert len(events2) == 1


def test_publish_returns_event(event_bus):
    """Test publish returns the created event."""
    event = event_bus.publish("test.event", "sender", {"key": "value"})

    assert isinstance(event, Event)
    assert event.event_type == "test.event"
    assert event.source == "sender"
    assert event.data == {"key": "value"}


def test_event_history(event_bus):
    """Test event history is maintained."""
    event_bus.publish("event1", "sender1", {})
    event_bus.publish("event2", "sender2", {})
    event_bus.publish("event3", "sender3", {})

    history = event_bus.get_history()

    assert len(history) == 3
    assert history[0].event_type == "event1"
    assert history[2].event_type == "event3"


def test_event_history_filter(event_bus):
    """Test filtering history by event type."""
    event_bus.publish("type_a", "sender", {})
    event_bus.publish("type_b", "sender", {})
    event_bus.publish("type_a", "sender", {})

    history = event_bus.get_history(event_type="type_a")

    assert len(history) == 2
    assert all(e.event_type == "type_a" for e in history)


def test_event_history_limit(event_bus):
    """Test limiting history results."""
    for i in range(50):
        event_bus.publish(f"event{i}", "sender", {})

    history = event_bus.get_history(limit=10)

    assert len(history) == 10
    # Should return most recent
    assert history[0].event_type == "event40"


def test_clear_history(event_bus):
    """Test clearing history."""
    event_bus.publish("event1", "sender", {})
    event_bus.publish("event2", "sender", {})

    event_bus.clear_history()
    history = event_bus.get_history()

    assert len(history) == 0


def test_get_event_bus_singleton():
    """Test get_event_bus returns same instance."""
    get_event_bus.cache_clear() if hasattr(get_event_bus, 'cache_clear') else None

    bus1 = get_event_bus()
    bus2 = get_event_bus()

    assert bus1 is bus2


def test_event_types_constants():
    """Test event type constants are defined."""
    assert EventTypes.COMMIT_CREATED == "commit.created"
    assert EventTypes.PR_CREATED == "pr.created"
    assert EventTypes.REVIEW_APPROVED == "review.approved"


def test_subscriber_error_doesnt_break_bus(event_bus):
    """Test that subscriber errors don't break the bus."""
    def good_callback(event):
        pass

    def bad_callback(event):
        raise Exception("Subscriber error!")

    event_bus.subscribe("test.event", good_callback)
    event_bus.subscribe("test.event", bad_callback)

    # Should not raise
    event = event_bus.publish("test.event", "sender", {})

    assert event is not None
