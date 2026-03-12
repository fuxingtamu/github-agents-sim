"""Action module for agents to execute actions."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..data_pipeline.storage.database import get_connection
from ..data_pipeline.storage.store import SimActionStore


@dataclass
class ActionResult:
    """Result of an action execution."""

    success: bool
    action_type: str
    data: dict[str, Any]
    message: str = ""
    error: str | None = None


class ActionExecutor(ABC):
    """Base class for action executors."""

    @abstractmethod
    def execute(self, action: str, context: dict[str, Any]) -> ActionResult:
        """
        Execute an action.

        Args:
            action: Action string
            context: Action context

        Returns:
            ActionResult
        """
        pass


class GitActionExecutor(ActionExecutor):
    """Executor for Git-related actions."""

    def __init__(self, sandbox: Any | None = None):
        """
        Initialize Git action executor.

        Args:
            sandbox: GitSandbox instance
        """
        self.sandbox = sandbox

    def execute(self, action: str, context: dict[str, Any]) -> ActionResult:
        """Execute a Git action."""
        # Placeholder - will be implemented with GitSandbox
        return ActionResult(
            success=True,
            action_type="git",
            data={"action": action},
            message=f"Git action executed: {action}",
        )


class CommunicationActionExecutor(ActionExecutor):
    """Executor for communication actions."""

    def __init__(self, agent: Any):
        """
        Initialize communication action executor.

        Args:
            agent: Agent instance
        """
        self.agent = agent

    def execute(self, action: str, context: dict[str, Any]) -> ActionResult:
        """Execute a communication action."""
        # Parse action
        try:
            action_data = json.loads(action)
            action_type = action_data.get("type", "")
            content = action_data.get("content", "")
            channel = action_data.get("channel", "general")
            mentions = action_data.get("mentions", [])

            # Send message
            message = self.agent.send_message(
                content=content,
                channel=channel,
                mentions=mentions,
            )

            return ActionResult(
                success=True,
                action_type="communicate",
                data={"message_id": message.id},
                message=f"Message sent to {channel}",
            )

        except json.JSONDecodeError as e:
            return ActionResult(
                success=False,
                action_type="communicate",
                data={},
                error=f"Invalid action JSON: {e}",
            )


class ActionModule:
    """Module for executing agent actions."""

    def __init__(self, agent: Any, sandbox: Any | None = None):
        """
        Initialize action module.

        Args:
            agent: Agent instance
            sandbox: GitSandbox instance
        """
        self.agent = agent
        self.sandbox = sandbox

        # Initialize executors
        self.git_executor = GitActionExecutor(sandbox)
        self.comm_executor = CommunicationActionExecutor(agent)

    def execute(self, action: str, context: dict[str, Any]) -> ActionResult:
        """
        Execute an action.

        Args:
            action: Action string
            context: Action context

        Returns:
            ActionResult
        """
        # Determine action type
        action_type = self._classify_action(action)

        # Log action
        self._log_action(action_type, action, context)

        # Execute based on type
        if action_type in ["git_commit", "git_branch", "git_merge", "read_file", "write_file", "run_command"]:
            return self.git_executor.execute(action, context)
        elif action_type in ["comment", "mention", "broadcast", "review_pr"]:
            return self.comm_executor.execute(action, context)
        else:
            return ActionResult(
                success=False,
                action_type=action_type,
                data={},
                error=f"Unknown action type: {action_type}",
            )

    def _classify_action(self, action: str) -> str:
        """
        Classify action type.

        Args:
            action: Action string

        Returns:
            Action type
        """
        try:
            action_data = json.loads(action)
            return action_data.get("type", "unknown")
        except json.JSONDecodeError:
            # Plain text action
            if action.startswith("commit"):
                return "git_commit"
            elif action.startswith("branch"):
                return "git_branch"
            elif action.startswith("read"):
                return "read_file"
            elif action.startswith("write"):
                return "write_file"
            elif action.startswith("run"):
                return "run_command"
            elif action.startswith("comment"):
                return "comment"
            else:
                return "unknown"

    def _log_action(
        self,
        action_type: str,
        action: str,
        context: dict[str, Any],
    ) -> None:
        """Log action to database."""
        conn = get_connection()
        try:
            SimActionStore.insert(
                simulation_id=self.agent.simulation_id,
                agent_id=self.agent.agent_id,
                action_type=action_type,
                action_data={"action": action, "context": context},
                trigger=context.get("trigger"),
                conn=conn,
            )
            conn.commit()
        finally:
            if conn:
                conn.close()

    # Convenience methods for common actions

    def commit(self, message: str, files: list[str] | None = None) -> ActionResult:
        """Commit changes."""
        action = json.dumps({
            "type": "git_commit",
            "message": message,
            "files": files,
        })
        return self.execute(action, {"trigger": "commit"})

    def create_branch(self, name: str, from_branch: str = "main") -> ActionResult:
        """Create a new branch."""
        action = json.dumps({
            "type": "git_branch",
            "name": name,
            "from": from_branch,
        })
        return self.execute(action, {"trigger": "create_branch"})

    def read_file(self, path: str) -> ActionResult:
        """Read a file."""
        action = json.dumps({
            "type": "read_file",
            "path": path,
        })
        return self.execute(action, {"trigger": "read_file"})

    def write_file(self, path: str, content: str) -> ActionResult:
        """Write a file."""
        action = json.dumps({
            "type": "write_file",
            "path": path,
            "content": content,
        })
        return self.execute(action, {"trigger": "write_file"})

    def run_command(self, command: str) -> ActionResult:
        """Run a shell command."""
        action = json.dumps({
            "type": "run_command",
            "command": command,
        })
        return self.execute(action, {"trigger": "run_command"})

    def comment(self, content: str, channel: str, mentions: list[str] | None = None) -> ActionResult:
        """Post a comment."""
        action = json.dumps({
            "type": "comment",
            "content": content,
            "channel": channel,
            "mentions": mentions,
        })
        return self.execute(action, {"trigger": "comment"})

    def review_pr(
        self,
        pr_number: int,
        decision: str,
        comments: list[dict],
    ) -> ActionResult:
        """Review a PR."""
        action = json.dumps({
            "type": "review_pr",
            "pr_number": pr_number,
            "decision": decision,  # "approve", "request_changes", "comment"
            "comments": comments,
        })
        return self.execute(action, {"trigger": "review_pr"})

    def create_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> ActionResult:
        """Create a PR."""
        action = json.dumps({
            "type": "create_pr",
            "title": title,
            "body": body,
            "head": head,
            "base": base,
        })
        return self.execute(action, {"trigger": "create_pr"})

    def mention(
        self,
        agent_id: str,
        content: str,
        channel: str,
    ) -> ActionResult:
        """Mention another agent."""
        action = json.dumps({
            "type": "mention",
            "content": content,
            "channel": channel,
            "mentions": [agent_id],
        })
        return self.execute(action, {"trigger": "mention"})
