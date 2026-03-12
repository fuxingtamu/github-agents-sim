"""Base agent class with state management and tool calling."""

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..config.settings import Settings, get_settings
from ..data_pipeline.storage.database import get_connection
from ..data_pipeline.storage.store import AgentStore, SimulationStore
from .prompts.role_templates import generate_role_prompt


@dataclass
class PersonalityTraits:
    """Agent personality traits."""

    strictness: float = 0.5
    communication: float = 0.5
    response_speed: float = 0.5
    cooperation: float = 0.5
    formality: float = 0.5
    emoji_usage: float = 0.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "strictness": self.strictness,
            "communication": self.communication,
            "response_speed": self.response_speed,
            "cooperation": self.cooperation,
            "formality": self.formality,
            "emoji_usage": self.emoji_usage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "PersonalityTraits":
        """Create from dictionary."""
        return cls(
            strictness=data.get("strictness", 0.5),
            communication=data.get("communication", 0.5),
            response_speed=data.get("response_speed", 0.5),
            cooperation=data.get("cooperation", 0.5),
            formality=data.get("formality", 0.5),
            emoji_usage=data.get("emoji_usage", 0.0),
        )


@dataclass
class AgentState:
    """Agent current state."""

    agent_id: str
    role: str
    persona_type: str
    personality: PersonalityTraits
    simulation_id: str
    name: str
    status: str = "active"
    current_goal: str | None = None
    working_branch: str | None = None
    assigned_issues: list[int] = field(default_factory=list)
    last_action: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """Message for agent communication."""

    id: str
    sender_id: str
    recipients: list[str]  # Empty = broadcast
    channel: str
    content: str
    mentions: list[str] = field(default_factory=list)
    in_reply_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "recipients": self.recipients,
            "channel": self.channel,
            "content": self.content,
            "mentions": self.mentions,
            "in_reply_to": self.in_reply_to,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            sender_id=data["sender_id"],
            recipients=data.get("recipients", []),
            channel=data["channel"],
            content=data["content"],
            mentions=data.get("mentions", []),
            in_reply_to=data.get("in_reply_to"),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(
        self,
        role: str,
        persona_type: str,
        personality: PersonalityTraits | None = None,
        simulation_id: str | None = None,
        name: str | None = None,
        settings: Settings | None = None,
    ):
        """
        Initialize an agent.

        Args:
            role: Agent role (maintainer/contributor/reviewer/bot)
            persona_type: Agent persona type
            personality: Personality traits
            simulation_id: Simulation session ID
            name: Agent name
            settings: Application settings
        """
        self.agent_id = str(uuid.uuid4())[:8]
        self.role = role
        self.persona_type = persona_type
        self.personality = personality or PersonalityTraits()
        self.simulation_id = simulation_id or str(uuid.uuid4())[:8]
        self.name = name or f"{role}_{self.agent_id}"
        self.settings = settings or get_settings()

        # State
        self.state = AgentState(
            agent_id=self.agent_id,
            role=self.role,
            persona_type=self.persona_type,
            personality=self.personality,
            simulation_id=self.simulation_id,
            name=self.name,
        )

        # System prompt
        self.system_prompt = generate_role_prompt(role, persona_type)

        # Message inbox
        self.inbox: list[Message] = []

        # Register agent in database
        self._register()

    def _register(self) -> None:
        """Register agent in database."""
        conn = get_connection()
        try:
            AgentStore.insert(
                agent_id=self.agent_id,
                simulation_id=self.simulation_id,
                name=self.name,
                role=self.role,
                persona_type=self.persona_type,
                personality=json.dumps(self.personality.to_dict()),
                conn=conn,
            )
            conn.commit()
        finally:
            conn.close()

    @abstractmethod
    def perceive(self) -> dict[str, Any]:
        """
        Perceive the environment.

        Returns:
            Dictionary of perceived information
        """
        pass

    @abstractmethod
    def decide(self, perception: dict[str, Any]) -> str:
        """
        Decide on next action.

        Args:
            perception: Information from perceive()

        Returns:
            Action to take
        """
        pass

    @abstractmethod
    def act(self, action: str) -> dict[str, Any]:
        """
        Execute an action.

        Args:
            action: Action string from decide()

        Returns:
            Action result
        """
        pass

    def step(self) -> dict[str, Any]:
        """
        Execute one agent step.

        Returns:
            Step result
        """
        perception = self.perceive()
        action = self.decide(perception)
        result = self.act(action)

        # Update state
        self.state.last_action = datetime.now()

        return result

    def send_message(
        self,
        content: str,
        channel: str,
        recipients: list[str] | None = None,
        mentions: list[str] | None = None,
        in_reply_to: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """
        Send a message.

        Args:
            content: Message content
            channel: Channel name (e.g., "PR #42", "general")
            recipients: Specific recipients (empty = broadcast)
            mentions: Mentioned agent IDs
            in_reply_to: Reply to message ID
            metadata: Additional metadata

        Returns:
            Sent message
        """
        message = Message(
            id=str(uuid.uuid4())[:8],
            sender_id=self.agent_id,
            recipients=recipients or [],
            channel=channel,
            content=content,
            mentions=mentions or [],
            in_reply_to=in_reply_to,
            metadata=metadata or {},
        )

        # Store message in database
        conn = get_connection()
        try:
            from ..data_pipeline.storage.store import MessageStore

            MessageStore.insert(
                message_id=message.id,
                simulation_id=self.simulation_id,
                sender_id=self.agent_id,
                channel=channel,
                content=content,
                conn=conn,
            )
            conn.commit()
        finally:
            conn.close()

        return message

    def receive_message(self, message: Message) -> None:
        """
        Receive a message.

        Args:
            message: Message to receive
        """
        # Check if message is for this agent
        if message.recipients and self.agent_id not in message.recipients:
            return

        # Check if mentioned
        if self.agent_id in message.mentions:
            self.inbox.append(message)

    def get_inbox(self) -> list[Message]:
        """Get unread messages."""
        messages = self.inbox.copy()
        self.inbox.clear()
        return messages

    def to_dict(self) -> dict[str, Any]:
        """Convert agent to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "persona_type": self.persona_type,
            "personality": self.personality.to_dict(),
            "simulation_id": self.simulation_id,
            "status": self.state.status,
            "current_goal": self.state.current_goal,
            "last_action": self.state.last_action.isoformat() if self.state.last_action else None,
        }
