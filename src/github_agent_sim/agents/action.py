"""Action module for agents to execute actions."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..data_pipeline.storage.database import get_connection
from ..data_pipeline.storage.store import (
    PRReviewStore,
    PullRequestStore,
    SimActionStore,
)


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
        if not self.sandbox:
            return ActionResult(
                success=False,
                action_type="git",
                data={},
                error="No sandbox available",
            )

        try:
            action_data = json.loads(action)
            action_type = action_data.get("type", "")

            if action_type == "git_branch":
                name = action_data.get("name", "")
                from_branch = action_data.get("from", "main")
                success = self.sandbox.create_branch(name, from_branch)
                return ActionResult(
                    success=success,
                    action_type="git_branch",
                    data={"branch": name},
                    message=f"Created branch: {name}" if success else f"Failed to create branch: {name}",
                )

            elif action_type == "git_commit":
                message = action_data.get("message", "")
                files = action_data.get("files", [])
                result = self.sandbox.commit(message, files)
                if result:
                    return ActionResult(
                        success=True,
                        action_type="git_commit",
                        data={"commit": result.hash},
                        message=f"Committed: {message}",
                    )
                else:
                    return ActionResult(
                        success=False,
                        action_type="git_commit",
                        data={},
                        error="Commit failed",
                    )

            elif action_type == "write_file":
                path = action_data.get("path", "")
                content = action_data.get("content", "")
                success = self.sandbox.write_file(path, content)
                return ActionResult(
                    success=success,
                    action_type="write_file",
                    data={"path": path},
                    message=f"Written file: {path}" if success else f"Failed to write file: {path}",
                )

            elif action_type == "read_file":
                path = action_data.get("path", "")
                content = self.sandbox.read_file(path)
                if content is not None:
                    return ActionResult(
                        success=True,
                        action_type="read_file",
                        data={"path": path, "content": content},
                        message=f"Read file: {path}",
                    )
                else:
                    return ActionResult(
                        success=False,
                        action_type="read_file",
                        data={},
                        error=f"File not found: {path}",
                    )

            elif action_type == "run_command":
                command = action_data.get("command", "")
                success, stdout, stderr = self.sandbox.run_command(command)
                return ActionResult(
                    success=success,
                    action_type="run_command",
                    data={"stdout": stdout, "stderr": stderr},
                    message=stdout if success else stderr,
                )

            elif action_type == "git_merge":
                branch = action_data.get("branch", "")
                no_ff = action_data.get("no_ff", False)
                success, message = self.sandbox.merge(branch, no_ff)
                return ActionResult(
                    success=success,
                    action_type="git_merge",
                    data={"branch": branch},
                    message=message,
                )

            else:
                return ActionResult(
                    success=False,
                    action_type=action_type,
                    data={},
                    error=f"Unknown Git action type: {action_type}",
                )

        except Exception as e:
            return ActionResult(
                success=False,
                action_type="git",
                data={},
                error=str(e),
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
        self._sandbox = sandbox
        self._pr_counter = 0  # Local PR counter for simulation

        # Initialize executors
        self.git_executor = GitActionExecutor(sandbox)
        self.comm_executor = CommunicationActionExecutor(agent)

    @property
    def sandbox(self) -> Any | None:
        """Get the Git sandbox."""
        return self._sandbox

    @sandbox.setter
    def sandbox(self, sandbox: Any | None) -> None:
        """Set the Git sandbox and update the git executor."""
        self._sandbox = sandbox
        if hasattr(self, 'git_executor'):
            self.git_executor.sandbox = sandbox

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
        elif action_type == "create_pr":
            return self._handle_create_pr(action, context)
        elif action_type == "merge_pr":
            return self._handle_merge_pr(action, context)
        elif action_type == "review_pr":
            return self._handle_review_pr(action, context)
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

    def create_branch(self, name: str, from_branch: str | None = None) -> ActionResult:
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
        comments: list[dict] | None = None,
        body: str | None = None,
    ) -> ActionResult:
        """Review a PR."""
        action = json.dumps({
            "type": "review_pr",
            "pr_number": pr_number,
            "decision": decision,  # "approve", "request_changes", "comment"
            "comments": comments or [],
            "body": body or "",
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

    def _handle_create_pr(self, action: str, context: dict[str, Any]) -> ActionResult:
        """Handle create_pr action."""
        try:
            action_data = json.loads(action)
            title = action_data.get("title", "Untitled PR")
            body = action_data.get("body", "")
            head = action_data.get("head", "feature")
            base = action_data.get("base", "main")

            if not self.sandbox:
                return ActionResult(
                    success=False,
                    action_type="create_pr",
                    data={},
                    error="No sandbox available",
                )

            # Create PR in sandbox
            pr = self.sandbox.create_pr(
                title=title,
                body=body,
                head_branch=head,
                base_branch=base,
                author_id=self.agent.agent_id,
            )

            if not pr:
                return ActionResult(
                    success=False,
                    action_type="create_pr",
                    data={},
                    error=f"Failed to create PR (branch '{head}' may not exist)",
                )

            # Store in database
            conn = get_connection()
            try:
                # Check if PR already exists
                existing_pr = PullRequestStore.get_by_number(
                    self.agent.simulation_id,
                    pr.pr_number,
                    conn=conn,
                )
                if existing_pr:
                    # PR already exists, update sandbox status to match database
                    return ActionResult(
                        success=True,
                        action_type="create_pr",
                        data={
                            "pr_number": pr.pr_number,
                            "title": title,
                            "head": head,
                            "base": base,
                        },
                        message=f"PR #{pr.pr_number} already exists: {title}",
                    )

                PullRequestStore.create(
                    simulation_id=self.agent.simulation_id,
                    pr_number=pr.pr_number,
                    title=title,
                    head_branch=head,
                    base_branch=base,
                    author_id=self.agent.agent_id,
                    body=body,
                    conn=conn,
                )

                # Send broadcast message about new PR
                self.agent.send_message(
                    content=f"Created PR #{pr.pr_number}: {title}",
                    channel="general",
                )

                conn.commit()
            finally:
                conn.close()

            return ActionResult(
                success=True,
                action_type="create_pr",
                data={
                    "pr_number": pr.pr_number,
                    "title": title,
                    "head": head,
                    "base": base,
                },
                message=f"Created PR #{pr.pr_number}: {title}",
            )

        except Exception as e:
            return ActionResult(
                success=False,
                action_type="create_pr",
                data={},
                error=str(e),
            )

    def _handle_merge_pr(self, action: str, context: dict[str, Any]) -> ActionResult:
        """Handle merge_pr action."""
        try:
            action_data = json.loads(action)
            pr_number = action_data.get("pr_number")
            merge_method = action_data.get("merge_method", "merge")

            if pr_number is None:
                return ActionResult(
                    success=False,
                    action_type="merge_pr",
                    data={},
                    error="pr_number is required",
                )

            if not self.sandbox:
                return ActionResult(
                    success=False,
                    action_type="merge_pr",
                    data={},
                    error="No sandbox available",
                )

            # Check PR reviews (optional - can be skipped for simulation)
            conn = get_connection()
            try:
                review_status = PRReviewStore.get_pr_status(
                    self.agent.simulation_id,
                    pr_number,
                    conn=conn,
                )

                # Warn if no approvals (but still allow merge for simulation)
                if review_status["approvals"] == 0:
                    print(f"Warning: Merging PR #{pr_number} without approvals")

            finally:
                conn.close()

            # Merge PR in sandbox
            success, message = self.sandbox.merge_pr(pr_number, merge_method)

            if success:
                # Update database
                conn = get_connection()
                try:
                    PullRequestStore.update_status(
                        self.agent.simulation_id,
                        pr_number,
                        status="merged",
                        conn=conn,
                    )
                    conn.commit()
                finally:
                    conn.close()

                # Send broadcast message
                self.agent.send_message(
                    content=f"Merged PR #{pr_number}",
                    channel="general",
                )

                return ActionResult(
                    success=True,
                    action_type="merge_pr",
                    data={"pr_number": pr_number},
                    message=message,
                )
            else:
                return ActionResult(
                    success=False,
                    action_type="merge_pr",
                    data={},
                    error=message,
                )

        except Exception as e:
            return ActionResult(
                success=False,
                action_type="merge_pr",
                data={},
                error=str(e),
            )

    def _handle_review_pr(self, action: str, context: dict[str, Any]) -> ActionResult:
        """Handle review_pr action."""
        try:
            action_data = json.loads(action)
            pr_number = action_data.get("pr_number")
            decision = action_data.get("decision", "commented")
            comments = action_data.get("comments", [])
            body = action_data.get("body", "")

            if pr_number is None:
                return ActionResult(
                    success=False,
                    action_type="review_pr",
                    data={},
                    error="pr_number is required",
                )

            # Map decision to review_type
            review_type_map = {
                "approve": "approved",
                "approved": "approved",
                "request_changes": "changes_requested",
                "changes_requested": "changes_requested",
                "comment": "commented",
                "commented": "commented",
            }
            review_type = review_type_map.get(decision.lower(), "commented")

            if not self.sandbox:
                return ActionResult(
                    success=False,
                    action_type="review_pr",
                    data={},
                    error="No sandbox available",
                )

            # Add review to PR
            review = self.sandbox.add_pr_review(
                pr_number=pr_number,
                reviewer_id=self.agent.agent_id,
                review_type=review_type,
                body=body or f"Review: {decision}",
                comments=comments,
            )

            if not review:
                return ActionResult(
                    success=False,
                    action_type="review_pr",
                    data={},
                    error=f"PR #{pr_number} not found",
                )

            # Store in database
            conn = get_connection()
            try:
                PRReviewStore.create(
                    simulation_id=self.agent.simulation_id,
                    pr_number=pr_number,
                    reviewer_id=self.agent.agent_id,
                    review_type=review_type,
                    body=body,
                    comments=comments,
                    conn=conn,
                )
                conn.commit()
            finally:
                conn.close()

            # Send message to PR channel
            emoji = {"approved": "✅", "changes_requested": "❌", "commented": "💬"}
            self.agent.send_message(
                content=f"{emoji.get(review_type, '')} Review on PR #{pr_number}: {body}",
                channel=f"PR #{pr_number}",
            )

            return ActionResult(
                success=True,
                action_type="review_pr",
                data={
                    "pr_number": pr_number,
                    "review_type": review_type,
                },
                message=f"Submitted {review_type} review for PR #{pr_number}",
            )

        except Exception as e:
            return ActionResult(
                success=False,
                action_type="review_pr",
                data={},
                error=str(e),
            )

    def merge_pr(
        self,
        pr_number: int,
        merge_method: str = "merge",
    ) -> ActionResult:
        """Merge a PR."""
        action = json.dumps({
            "type": "merge_pr",
            "pr_number": pr_number,
            "merge_method": merge_method,
        })
        return self.execute(action, {"trigger": "merge_pr"})
