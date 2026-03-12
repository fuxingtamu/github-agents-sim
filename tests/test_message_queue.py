"""Tests for message queue module."""

import pytest

from github_agent_sim.agents.base_agent import Message
from github_agent_sim.simulation.message_queue import MessageQueue, MentionSystem


@pytest.fixture
def message_queue():
    """Create a fresh message queue."""
    mq = MessageQueue()
    yield mq


@pytest.fixture
def mention_system(message_queue):
    """Create a mention system."""
    ms = MentionSystem(message_queue)
    # Register some test agents
    ms.register_agent("agent1", "Alice")
    ms.register_agent("agent2", "Bob")
    ms.register_agent("agent3", "Charlie")
    yield ms


def test_subscribe(message_queue):
    """Test subscribing to a channel."""
    message_queue.subscribe("agent1", "general")

    # Should be in subscriptions
    assert "general" in message_queue._subscriptions["agent1"]


def test_unsubscribe(message_queue):
    """Test unsubscribing from a channel."""
    message_queue.subscribe("agent1", "general")
    message_queue.unsubscribe("agent1", "general")

    assert "general" not in message_queue._subscriptions["agent1"]


def test_publish_broadcast(message_queue):
    """Test broadcasting a message."""
    message_queue.subscribe("agent1", "general")
    message_queue.subscribe("agent2", "general")

    message = Message(
        id="msg1",
        sender_id="sender",
        recipients=[],
        channel="general",
        content="Hello everyone!",
    )

    result = message_queue.publish(message, broadcast=True)

    # Both agents should receive the message
    messages1 = message_queue.get_messages("agent1")
    messages2 = message_queue.get_messages("agent2")

    assert len(messages1) == 1
    assert len(messages2) == 1
    assert messages1[0].content == "Hello everyone!"


def test_publish_direct(message_queue):
    """Test sending a direct message."""
    message = Message(
        id="msg1",
        sender_id="sender",
        recipients=["agent1"],
        channel="general",
        content="Hello Alice!",
    )

    message_queue.publish(message)

    messages = message_queue.get_messages("agent1")

    assert len(messages) == 1
    assert messages[0].content == "Hello Alice!"


def test_get_messages_unread_only(message_queue):
    """Test getting only unread messages."""
    message_queue.subscribe("agent1", "general")

    # Send and mark as read
    msg1 = Message(id="msg1", sender_id="s", recipients=[], channel="general", content="1")
    msg2 = Message(id="msg2", sender_id="s", recipients=[], channel="general", content="2")

    message_queue.publish(msg1)
    message_queue.publish(msg2)

    # Mark first as read
    message_queue.mark_read("agent1", ["msg1"])

    # Should only return unread
    unread = message_queue.get_messages("agent1", unread_only=True)

    assert len(unread) == 1
    assert unread[0].id == "msg2"


def test_mark_read(message_queue):
    """Test marking messages as read."""
    message_queue.subscribe("agent1", "general")

    msg = Message(id="msg1", sender_id="s", recipients=[], channel="general", content="1")
    message_queue.publish(msg)

    count = message_queue.mark_read("agent1", ["msg1"])

    assert count == 1

    # Should not appear in unread
    unread = message_queue.get_messages("agent1", unread_only=True)
    assert len(unread) == 0


def test_clear_read(message_queue):
    """Test clearing read messages from queue."""
    message_queue.subscribe("agent1", "general")

    msg1 = Message(id="msg1", sender_id="s", recipients=[], channel="general", content="1")
    msg2 = Message(id="msg2", sender_id="s", recipients=[], channel="general", content="2")

    message_queue.publish(msg1)
    message_queue.publish(msg2)

    message_queue.mark_read("agent1", ["msg1"])

    cleared = message_queue.clear_read("agent1")

    assert cleared == 1

    # Only unread should remain
    remaining = message_queue.get_messages("agent1", unread_only=True)
    assert len(remaining) == 1


def test_message_history(message_queue):
    """Test message history."""
    msg1 = Message(id="msg1", sender_id="s", recipients=[], channel="general", content="1")
    msg2 = Message(id="msg2", sender_id="s", recipients=[], channel="general", content="2")

    message_queue.publish(msg1)
    message_queue.publish(msg2)

    history = message_queue.get_history()

    assert len(history) == 2
    assert history[0].content == "1"


def test_mention_parse(mention_system):
    """Test parsing mentions from content."""
    content = "Hello @Alice and @Bob!"

    mentions = mention_system.parse_mentions(content)

    assert "agent1" in mentions
    assert "agent2" in mentions


def test_mention_create_message(mention_system):
    """Test creating a message with mentions."""
    content = "Hey @Alice, check this out!"

    message = mention_system.create_mention_message(
        sender_id="agent2",
        content=content,
        channel="general",
    )

    assert "agent1" in message.mentions
    assert message.content == content


def test_mention_send(mention_system):
    """Test sending a mention message."""
    mention_system.send_mention(
        sender_id="agent2",
        target_agent_id="agent1",
        content="@Alice can you review this?",
        channel="PR #42",
    )

    messages = mention_system.message_queue.get_messages("agent1")

    assert len(messages) == 1
    assert messages[0].content == "@Alice can you review this?"


def test_get_agent_id_by_name(mention_system):
    """Test getting agent ID by name."""
    agent_id = mention_system.get_agent_id_by_name("Alice")

    assert agent_id == "agent1"


def test_get_agent_id_case_insensitive(mention_system):
    """Test case insensitive name lookup."""
    agent_id = mention_system.get_agent_id_by_name("alice")

    assert agent_id == "agent1"


def test_agent_registration(mention_system):
    """Test registering and unregistering agents."""
    mention_system.unregister_agent("agent1")

    agent_id = mention_system.get_agent_id_by_name("Alice")
    assert agent_id is None
