"""Reviewer agent role."""

from typing import Any

from ..base_agent import BaseAgent, PersonalityTraits
from ..perception import PerceivedData


class ReviewerAgent(BaseAgent):
    """
    Reviewer agent role.

    Responsibilities:
    - Review PR code quality
    - Provide constructive feedback
    - Approve or request changes
    - Participate in technical discussions
    """

    def __init__(
        self,
        persona_type: str = "gatekeeper",
        personality: PersonalityTraits | None = None,
        simulation_id: str | None = None,
        name: str | None = None,
    ):
        """Initialize a Reviewer agent."""
        super().__init__(
            role="reviewer",
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
            "recent_messages": perceived.recent_messages,
            "mentions": perceived.mentions,
        }

    def decide(self, perception: dict[str, Any]) -> str:
        """Decide on next action."""
        perceived_data = PerceivedData(
            warehouse=perception.get("warehouse"),
            open_prs=perception.get("open_prs", []),
            prs_assigned_to_me=perception.get("prs_assigned_to_me", []),
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

    def review_pr(
        self,
        pr_number: int,
        decision: str,
        comments: list[dict],
    ) -> dict[str, Any]:
        """
        Review a pull request.

        Args:
            pr_number: PR number
            decision: "approve", "request_changes", or "comment"
            comments: List of comment objects with line/content

        Returns:
            Action result
        """
        return self.action_module.review_pr(pr_number, decision, comments)

    def approve_pr(self, pr_number: int, comment: str | None = None) -> dict[str, Any]:
        """
        Approve a PR.

        Args:
            pr_number: PR number
            comment: Optional comment

        Returns:
            Action result
        """
        comments = []
        if comment:
            comments.append({"type": "general", "content": comment})
        return self.review_pr(pr_number, "approve", comments)

    def request_changes(
        self,
        pr_number: int,
        comments: list[dict],
    ) -> dict[str, Any]:
        """
        Request changes on a PR.

        Args:
            pr_number: PR number
            comments: List of change requests

        Returns:
            Action result
        """
        return self.review_pr(pr_number, "request_changes", comments)
