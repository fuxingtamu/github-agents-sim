"""Perception module for agents to observe the environment."""

from dataclasses import dataclass, field
from typing import Any

from ..data_pipeline.storage.database import get_connection
from ..data_pipeline.storage.store import MessageStore, SimActionStore
from .base_agent import BaseAgent, Message


@dataclass
class WarehouseState:
    """State of the Git warehouse."""

    current_branch: str = "main"
    branches: list[str] = field(default_factory=list)
    uncommitted_changes: bool = False
    last_commit_hash: str | None = None
    last_commit_message: str | None = None


@dataclass
class PRState:
    """State of a Pull Request."""

    number: int
    title: str
    author: str
    status: str  # open, closed, merged
    branch: str
    changes: dict[str, Any] = field(default_factory=dict)
    reviews: list[dict] = field(default_factory=list)
    comments: list[dict] = field(default_factory=list)


@dataclass
class PerceivedData:
    """Data perceived by an agent."""

    # Warehouse state
    warehouse: WarehouseState | None = None

    # PRs
    open_prs: list[PRState] = field(default_factory=list)
    my_prs: list[PRState] = field(default_factory=list)
    prs_assigned_to_me: list[PRState] = field(default_factory=list)

    # Issues
    open_issues: list[dict] = field(default_factory=list)
    my_issues: list[dict] = field(default_factory=list)

    # Messages
    recent_messages: list[Message] = field(default_factory=list)
    mentions: list[Message] = field(default_factory=list)

    # Actions by other agents
    recent_actions: list[dict] = field(default_factory=list)

    # Working memory
    working_memory: dict[str, Any] = field(default_factory=dict)


class PerceptionModule:
    """Module for perceiving environment state."""

    def __init__(self, agent: BaseAgent):
        """
        Initialize perception module.

        Args:
            agent: The agent this module belongs to
        """
        self.agent = agent

    def perceive(self) -> PerceivedData:
        """
        Gather all perceived data.

        Returns:
            PerceivedData object with all perceived information
        """
        return PerceivedData(
            warehouse=self._perceive_warehouse(),
            open_prs=self._perceive_open_prs(),
            my_prs=self._perceive_my_prs(),
            prs_assigned_to_me=self._perceive_assigned_prs(),
            open_issues=self._perceive_open_issues(),
            my_issues=self._perceive_my_issues(),
            recent_messages=self._perceive_messages(),
            mentions=self._get_mentions(),
            recent_actions=self._perceive_recent_actions(),
        )

    def _perceive_warehouse(self) -> WarehouseState:
        """Perceive Git warehouse state."""
        # This will be implemented with GitSandbox
        return WarehouseState()

    def _perceive_open_prs(self) -> list[PRState]:
        """Perceive open PRs in the simulation."""
        # TODO: Query PR state from simulation manager
        return []

    def _perceive_my_prs(self) -> list[PRState]:
        """Perceive PRs created by this agent."""
        # TODO: Query PRs authored by this agent
        return []

    def _perceive_assigned_prs(self) -> list[PRState]:
        """Perceive PRs assigned for this agent to review."""
        # TODO: Query PRs assigned to this agent
        return []

    def _perceive_open_issues(self) -> list[dict]:
        """Perceive open issues."""
        # TODO: Query open issues
        return []

    def _perceive_my_issues(self) -> list[dict]:
        """Perceive issues assigned to this agent."""
        # TODO: Query issues assigned to this agent
        return []

    def _perceive_messages(self) -> list[Message]:
        """Perceive recent messages in channels."""
        conn = get_connection()
        try:
            # Get messages from channels the agent is following
            messages_data = MessageStore.get_by_simulation(
                self.agent.simulation_id,
                conn=conn,
            )

            # Convert to Message objects
            messages = []
            for msg_data in messages_data[-20:]:  # Last 20 messages
                try:
                    msg = Message(
                        id=msg_data["id"],
                        sender_id=msg_data["sender_id"],
                        recipients=[],
                        channel=msg_data["channel"],
                        content=msg_data["content"],
                        timestamp=msg_data["created_at"],
                    )
                    messages.append(msg)
                except (KeyError, ValueError):
                    continue

            return messages
        finally:
            if conn:
                conn.close()

    def _get_mentions(self) -> list[Message]:
        """Get messages that mention this agent."""
        all_messages = self._perceive_messages()
        return [m for m in all_messages if self.agent.agent_id in m.mentions]

    def _perceive_recent_actions(self) -> list[dict]:
        """Perceive recent actions by other agents."""
        conn = get_connection()
        try:
            actions = SimActionStore.get_by_simulation(
                self.agent.simulation_id,
                conn=conn,
            )
            # Filter out own actions and return last 10
            return [
                a for a in actions[-10:]
                if a.get("agent_id") != self.agent.agent_id
            ]
        finally:
            if conn:
                conn.close()

    def observe_pr(self, pr_number: int) -> PRState | None:
        """
        Observe a specific PR.

        Args:
            pr_number: PR number to observe

        Returns:
            PRState or None if not found
        """
        # TODO: Implement with simulation state manager
        return None

    def observe_file(self, file_path: str) -> str | None:
        """
        Observe (read) a file.

        Args:
            file_path: Path to file

        Returns:
            File content or None
        """
        # This will be implemented with GitSandbox
        return None

    def get_context(self, context_type: str) -> Any:
        """
        Get context information.

        Args:
            context_type: Type of context (e.g., "pr_discussion", "issue_thread")

        Returns:
            Context data
        """
        # TODO: Implement context retrieval
        return None
