"""Maintainer agent role."""

from typing import Any

from ..base_agent import BaseAgent, PersonalityTraits
from ..perception import PerceivedData


class MaintainerAgent(BaseAgent):
    """
    Maintainer agent role.

    Responsibilities:
    - Approve and merge PRs
    - Manage issues and labels
    - Assign tasks
    - Plan releases
    - Resolve merge conflicts
    """

    def __init__(
        self,
        persona_type: str = "mentor",
        personality: PersonalityTraits | None = None,
        simulation_id: str | None = None,
        name: str | None = None,
    ):
        """Initialize a Maintainer agent."""
        super().__init__(
            role="maintainer",
            persona_type=persona_type,
            personality=personality,
            simulation_id=simulation_id,
            name=name,
        )

        from ..action import ActionModule
        from ..decision import DecisionModule
        from ..perception import PerceptionModule

        self.perception_module = PerceptionModule(self)
        self.decision_module = DecisionModule(self)
        self.action_module = ActionModule(self)

    def perceive(self) -> dict[str, Any]:
        """Perceive the environment."""
        perceived = self.perception_module.perceive()
        return {
            "warehouse": perceived.warehouse,
            "open_prs": perceived.open_prs,
            "prs_assigned_to_me": perceived.prs_assigned_to_me,
            "open_issues": perceived.open_issues,
            "recent_messages": perceived.recent_messages,
            "mentions": perceived.mentions,
        }

    def decide(self, perception: dict[str, Any]) -> str:
        """Decide on next action."""
        perceived_data = PerceivedData(
            warehouse=perception.get("warehouse"),
            open_prs=perception.get("open_prs", []),
            prs_assigned_to_me=perception.get("prs_assigned_to_me", []),
            open_issues=perception.get("open_issues", []),
            recent_messages=perception.get("recent_messages", []),
            mentions=perception.get("mentions", []),
        )
        return self.decision_module.decide(perceived_data)

    def act(self, action: str) -> dict[str, Any]:
        """Execute an action."""
        result = self.action_module.execute(action, {})
        return {
            "success": result.success,
            "action_type": result.action_type,
            "message": result.message,
            "error": result.error,
        }

    def merge_pr(self, pr_number: int, method: str = "merge") -> dict[str, Any]:
        """
        Merge a pull request.

        Args:
            pr_number: PR number
            method: Merge method (merge/squash/rebase)

        Returns:
            Action result
        """
        action = f'{{"type": "merge_pr", "pr_number": {pr_number}, "method": "{method}"}}'
        return self.action_module.execute(action, {})

    def add_label(self, target: str, labels: list[str]) -> dict[str, Any]:
        """
        Add labels to an issue or PR.

        Args:
            target: Target (e.g., "PR #42" or "Issue #10")
            labels: Labels to add

        Returns:
            Action result
        """
        action = f'{{"type": "add_label", "target": "{target}", "labels": {labels}}}'
        return self.action_module.execute(action, {})

    def assign_task(self, target: str, assignee_id: str) -> dict[str, Any]:
        """
        Assign a task to someone.

        Args:
            target: Target (PR or Issue)
            assignee_id: Agent ID to assign

        Returns:
            Action result
        """
        action = f'{{"type": "assign_task", "target": "{target}", "assignee": "{assignee_id}"}}'
        return self.action_module.execute(action, {})

    def close_issue(self, issue_number: int) -> dict[str, Any]:
        """
        Close an issue.

        Args:
            issue_number: Issue number

        Returns:
            Action result
        """
        action = f'{{"type": "close_issue", "issue_number": {issue_number}}}'
        return self.action_module.execute(action, {})
