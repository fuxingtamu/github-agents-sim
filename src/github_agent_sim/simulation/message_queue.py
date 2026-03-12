"""Message queue for agent communication."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from ..agents.base_agent import Message


@dataclass
class QueuedMessage:
    """Message in the queue."""

    id: str
    message: Message
    delivered: bool = False
    created_at: datetime = field(default_factory=datetime.now)


class MessageQueue:
    """
    Message queue for agent communication.

    Supports broadcast and direct messages.
    """

    def __init__(self):
        """Initialize message queue."""
        self._queues: dict[str, list[QueuedMessage]] = defaultdict(list)
        self._subscriptions: dict[str, list[str]] = defaultdict(list)  # agent_id -> channels
        self._history: list[QueuedMessage] = []
        self._lock = asyncio.Lock()

    def subscribe(self, agent_id: str, channel: str) -> None:
        """
        Subscribe an agent to a channel.

        Args:
            agent_id: Agent ID
            channel: Channel name
        """
        if channel not in self._subscriptions[agent_id]:
            self._subscriptions[agent_id].append(channel)

    def unsubscribe(self, agent_id: str, channel: str) -> None:
        """
        Unsubscribe an agent from a channel.

        Args:
            agent_id: Agent ID
            channel: Channel name
        """
        if channel in self._subscriptions[agent_id]:
            self._subscriptions[agent_id].remove(channel)

    def publish(
        self,
        message: Message,
        broadcast: bool = False,
    ) -> QueuedMessage:
        """
        Publish a message.

        Args:
            message: Message to publish
            broadcast: If True, send to all subscribers of the channel

        Returns:
            QueuedMessage
        """
        queued = QueuedMessage(
            id=str(uuid4())[:8],
            message=message,
        )

        if broadcast or not message.recipients:
            # Broadcast to channel subscribers
            channel = message.channel
            for agent_id, channels in self._subscriptions.items():
                if channel in channels or message.recipients is None:
                    self._queues[agent_id].append(queued)
        else:
            # Direct message to specific recipients
            for recipient_id in message.recipients:
                self._queues[recipient_id].append(queued)

        # Store in history
        self._history.append(queued)

        return queued

    def get_messages(
        self,
        agent_id: str,
        unread_only: bool = True,
    ) -> list[Message]:
        """
        Get messages for an agent.

        Args:
            agent_id: Agent ID
            unread_only: If True, only return unread messages

        Returns:
            List of messages
        """
        queue = self._queues.get(agent_id, [])

        if unread_only:
            messages = [qm.message for qm in queue if not qm.delivered]
        else:
            messages = [qm.message for qm in queue]

        return messages

    def mark_read(self, agent_id: str, message_ids: list[str]) -> int:
        """
        Mark messages as read.

        Args:
            agent_id: Agent ID
            message_ids: Message IDs to mark

        Returns:
            Number of messages marked
        """
        count = 0
        for qm in self._queues.get(agent_id, []):
            if qm.id in message_ids and not qm.delivered:
                qm.delivered = True
                count += 1
        return count

    def clear_read(self, agent_id: str) -> int:
        """
        Clear read messages from queue.

        Args:
            agent_id: Agent ID

        Returns:
            Number of messages cleared
        """
        queue = self._queues.get(agent_id, [])
        original_len = len(queue)
        self._queues[agent_id] = [qm for qm in queue if not qm.delivered]
        return original_len - len(self._queues[agent_id])

    def get_history(
        self,
        channel: str | None = None,
        limit: int = 100,
    ) -> list[Message]:
        """
        Get message history.

        Args:
            channel: Filter by channel
            limit: Maximum messages to return

        Returns:
            List of messages
        """
        if channel:
            return [
                qm.message for qm in self._history
                if qm.message.channel == channel
            ][-limit:]
        return [qm.message for qm in self._history][-limit:]


class MentionSystem:
    """
    System for handling @mentions.

    Allows agents to mention each other in messages.
    """

    def __init__(self, message_queue: MessageQueue):
        """
        Initialize mention system.

        Args:
            message_queue: Message queue instance
        """
        self.message_queue = message_queue
        self._agent_names: dict[str, str] = {}  # id -> name

    def register_agent(self, agent_id: str, name: str) -> None:
        """
        Register an agent.

        Args:
            agent_id: Agent ID
            name: Agent name
        """
        self._agent_names[agent_id] = name

    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent.

        Args:
            agent_id: Agent ID
        """
        if agent_id in self._agent_names:
            del self._agent_names[agent_id]

    def parse_mentions(self, content: str) -> list[str]:
        """
        Parse @mentions from content.

        Args:
            content: Message content

        Returns:
            List of mentioned agent IDs
        """
        import re

        mentions = []
        # Find @name patterns
        for match in re.findall(r"@(\w+)", content):
            # Find matching agent ID
            for agent_id, name in self._agent_names.items():
                if name.lower() == match.lower() or agent_id == match:
                    mentions.append(agent_id)
                    break

        return mentions

    def create_mention_message(
        self,
        sender_id: str,
        content: str,
        channel: str,
    ) -> Message:
        """
        Create a message with mentions.

        Args:
            sender_id: Sender agent ID
            content: Message content
            channel: Channel name

        Returns:
            Message with parsed mentions
        """
        mentions = self.parse_mentions(content)

        return Message(
            id=str(uuid4())[:8],
            sender_id=sender_id,
            recipients=[],  # Broadcast to channel
            channel=channel,
            content=content,
            mentions=mentions,
        )

    def send_mention(
        self,
        sender_id: str,
        target_agent_id: str,
        content: str,
        channel: str,
    ) -> Message:
        """
        Send a message that mentions another agent.

        Args:
            sender_id: Sender agent ID
            target_agent_id: Mentioned agent ID
            content: Message content
            channel: Channel name

        Returns:
            Sent message
        """
        message = Message(
            id=str(uuid4())[:8],
            sender_id=sender_id,
            recipients=[target_agent_id],
            channel=channel,
            content=content,
            mentions=[target_agent_id],
        )

        self.message_queue.publish(message)

        return message

    def get_agent_id_by_name(self, name: str) -> str | None:
        """
        Get agent ID by name.

        Args:
            name: Agent name

        Returns:
            Agent ID or None
        """
        for agent_id, agent_name in self._agent_names.items():
            if agent_name.lower() == name.lower():
                return agent_id
        return None
