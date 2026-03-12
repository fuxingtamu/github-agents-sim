"""Contributor agent role."""

from typing import Any

from ..base_agent import BaseAgent, PersonalityTraits
from ..perception import PerceivedData


class ContributorAgent(BaseAgent):
    """
    Contributor agent role.

    Responsibilities:
    - Create feature branches
    - Develop and commit code
    - Create PRs
    - Respond to review feedback
    - Fix bugs
    """

    def __init__(
        self,
        persona_type: str = "ninja",
        personality: PersonalityTraits | None = None,
        simulation_id: str | None = None,
        name: str | None = None,
    ):
        """
        Initialize a Contributor agent.

        Args:
            persona_type: Persona type (ninja/collaborator/bug_hunter/mentor)
            personality: Personality traits
            simulation_id: Simulation session ID
            name: Agent name
        """
        super().__init__(
            role="contributor",
            persona_type=persona_type,
            personality=personality,
            simulation_id=simulation_id,
            name=name,
        )

        # Import here to avoid circular dependency
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
            "my_prs": perceived.my_prs,
            "recent_messages": perceived.recent_messages,
            "mentions": perceived.mentions,
            "recent_actions": perceived.recent_actions,
        }

    def decide(self, perception: dict[str, Any]) -> str:
        """Decide on next action."""
        perceived_data = PerceivedData(
            warehouse=perception.get("warehouse"),
            open_prs=perception.get("open_prs", []),
            my_prs=perception.get("my_prs", []),
            recent_messages=perception.get("recent_messages", []),
            mentions=perception.get("mentions", []),
            recent_actions=perception.get("recent_actions", []),
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

    def contribute_code(
        self,
        file_path: str,
        content: str,
        commit_message: str,
    ) -> dict[str, Any]:
        """
        Contribute code to the repository.

        Args:
            file_path: Path to the file
            content: New file content
            commit_message: Commit message

        Returns:
            Action result
        """
        # Write file
        write_result = self.action_module.write_file(file_path, content)
        if not write_result.success:
            return {"success": False, "error": write_result.error}

        # Commit
        commit_result = self.action_module.commit(commit_message, [file_path])

        return commit_result

    def create_feature_branch(self, feature_name: str) -> dict[str, Any]:
        """
        Create a feature branch.

        Args:
            feature_name: Name of the feature

        Returns:
            Action result
        """
        branch_name = f"feature/{feature_name}"
        return self.action_module.create_branch(branch_name)

    def submit_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> dict[str, Any]:
        """
        Submit a pull request.

        Args:
            title: PR title
            body: PR description
            head: Source branch
            base: Target branch

        Returns:
            Action result
        """
        return self.action_module.create_pr(title, body, head, base)
