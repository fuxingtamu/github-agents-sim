"""Bot agent role."""

from typing import Any

from ..base_agent import BaseAgent, PersonalityTraits
from ..perception import PerceivedData


class BotAgent(BaseAgent):
    """
    Bot agent role.

    Responsibilities:
    - Run CI/CD tests
    - Auto-label PRs and issues
    - Update dependencies
    - Report build status
    """

    def __init__(
        self,
        bot_type: str = "ci_bot",
        persona_type: str = "bot",
        personality: PersonalityTraits | None = None,
        simulation_id: str | None = None,
        name: str | None = None,
    ):
        """
        Initialize a Bot agent.

        Args:
            bot_type: Type of bot (ci_bot/dependabot)
            persona_type: Persona type (always "bot")
            personality: Personality traits (ignored for bots)
            simulation_id: Simulation session ID
            name: Agent name
        """
        super().__init__(
            role="bot",
            persona_type=persona_type,
            personality=personality or PersonalityTraits(
                communication=0.5,
                response_speed=1.0,  # Bots respond instantly
            ),
            simulation_id=simulation_id,
            name=name or f"{bot_type}_{self.agent_id}",
        )

        self.bot_type = bot_type

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
            "recent_actions": perceived.recent_actions,
        }

    def decide(self, perception: dict[str, Any]) -> str:
        """Decide on next action."""
        perceived_data = PerceivedData(
            warehouse=perception.get("warehouse"),
            open_prs=perception.get("open_prs", []),
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

    def run_tests(self, pr_number: int | None = None) -> dict[str, Any]:
        """
        Run automated tests.

        Args:
            pr_number: Optional PR number to test

        Returns:
            Action result
        """
        action = f'{{"type": "run_tests", "pr_number": {pr_number}}}'
        return self.action_module.execute(action, {"trigger": "run_tests"})

    def auto_label(self, target: str, labels: list[str]) -> dict[str, Any]:
        """
        Automatically add labels.

        Args:
            target: Target (PR or Issue)
            labels: Labels to add

        Returns:
            Action result
        """
        action = f'{{"type": "auto_label", "target": "{target}", "labels": {labels}}}'
        return self.action_module.execute(action, {})

    def report_status(
        self,
        target: str,
        status: str,
        details: str,
    ) -> dict[str, Any]:
        """
        Report build/test status.

        Args:
            target: Target (PR or commit)
            status: Status (success/failure/pending)
            details: Status details

        Returns:
            Action result
        """
        action = f'{{"type": "report_status", "target": "{target}", "status": "{status}", "details": "{details}"}}'
        return self.action_module.execute(action, {})

    def update_dependencies(self) -> dict[str, Any]:
        """
        Update dependencies.

        Returns:
            Action result
        """
        action = '{"type": "update_deps"}'
        return self.action_module.execute(action, {"trigger": "update_deps"})
