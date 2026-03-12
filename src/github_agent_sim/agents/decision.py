"""Decision module for agents to make decisions."""

import json
import random
from dataclasses import dataclass
from typing import Any

from .base_agent import BaseAgent
from .perception import PerceivedData


@dataclass
class Decision:
    """A decision made by an agent."""

    action: str
    reason: str
    priority: float = 0.5
    target: str | None = None  # Target of the action (e.g., PR number)
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DecisionModule:
    """Module for making decisions based on perception and personality."""

    def __init__(self, agent: BaseAgent):
        """
        Initialize decision module.

        Args:
            agent: Agent instance
        """
        self.agent = agent

    def decide(self, perception: PerceivedData) -> str:
        """
        Decide on next action based on perception.

        Args:
            perception: Perceived data

        Returns:
            Action string (JSON format)
        """
        # Get decision based on current state
        decision = self._get_decision(perception)

        # Apply personality modifiers
        decision = self._apply_personality(decision, perception)

        # Convert to JSON
        return json.dumps({
            "type": decision.action,
            "target": decision.target,
            "reason": decision.reason,
            **decision.metadata,
        })

    def _get_decision(self, perception: PerceivedData) -> Decision:
        """Get raw decision based on state."""
        # Priority order:
        # 1. Respond to mentions
        # 2. Review assigned PRs
        # 3. Work on assigned issues
        # 4. Check own PRs for feedback
        # 5. Continue current work

        # Check for mentions
        if perception.mentions:
            mention = perception.mentions[-1]
            return Decision(
                action="respond_to_mention",
                reason=f"Responding to mention in {mention.channel}",
                priority=0.9,
                target=mention.channel,
                metadata={"message_id": mention.id, "content": mention.content},
            )

        # Check for assigned PRs to review
        if perception.prs_assigned_to_me:
            pr = perception.prs_assigned_to_me[0]
            return Decision(
                action="review_pr",
                reason=f"Reviewing assigned PR #{pr.number}",
                priority=0.8,
                target=str(pr.number),
                metadata={"pr_number": pr.number},
            )

        # Check for open PRs that need attention
        if perception.open_prs and self.agent.role == "reviewer":
            pr = perception.open_prs[0]
            return Decision(
                action="review_pr",
                reason=f"Volunteering to review PR #{pr.number}",
                priority=0.6,
                target=str(pr.number),
                metadata={"pr_number": pr.number},
            )

        # Default: continue working or idle
        return self._get_default_decision(perception)

    def _get_default_decision(self, perception: PerceivedData) -> Decision:
        """Get default decision when no urgent tasks."""
        role = self.agent.role

        if role == "contributor":
            # Contributors should work on code
            if perception.warehouse and perception.warehouse.uncommitted_changes:
                return Decision(
                    action="git_commit",
                    reason="Committing uncommitted changes",
                    priority=0.5,
                    metadata={"message": "WIP: Continuing work"},
                )
            else:
                return Decision(
                    action="create_pr",
                    reason="Creating PR for completed work",
                    priority=0.4,
                    metadata={
                        "title": "WIP: New feature",
                        "body": "Description of changes",
                        "head": "feature-branch",
                        "base": "main",
                    },
                )

        elif role == "maintainer":
            # Maintainers should merge approved PRs
            return Decision(
                action="merge_pr",
                reason="Checking PRs ready for merge",
                priority=0.5,
                metadata={},
            )

        elif role == "reviewer":
            # Reviewers should review code
            return Decision(
                action="review_pr",
                reason="Looking for PRs to review",
                priority=0.5,
                metadata={},
            )

        elif role == "bot":
            # Bots should run CI/CD
            return Decision(
                action="run_tests",
                reason="Running automated tests",
                priority=0.5,
                metadata={},
            )

        else:
            return Decision(
                action="idle",
                reason="No pending tasks",
                priority=0.1,
            )

    def _apply_personality(self, decision: Decision, perception: PerceivedData) -> Decision:
        """
        Apply personality modifiers to decision.

        Args:
            decision: Raw decision
            perception: Perceived data

        Returns:
            Modified decision
        """
        personality = self.agent.personality

        # Response speed affects delay
        # Higher response_speed = faster response
        response_delay = (1.0 - personality.response_speed) * 10  # 0-10 seconds

        # Communication affects message length
        if decision.action == "comment":
            if personality.communication < 0.3:
                # Less communicative = shorter messages
                decision.metadata["max_length"] = 50
            elif personality.communication > 0.7:
                # More communicative = longer messages
                decision.metadata["max_length"] = 500

        # Strictness affects review decisions
        if decision.action == "review_pr":
            if personality.strictness > 0.7:
                # Stricter = more likely to request changes
                decision.metadata["approval_threshold"] = 0.3
            elif personality.strictness < 0.4:
                # More lenient = more likely to approve
                decision.metadata["approval_threshold"] = 0.7

        # Cooperation affects helping behavior
        if perception.mentions:
            if personality.cooperation > 0.7:
                # More cooperative = more helpful
                decision.metadata["offer_help"] = True

        # Add delay based on response speed
        decision.metadata["delay_seconds"] = response_delay

        return decision

    def _should_respond_to_mention(
        self,
        mention_content: str,
        personality: Any,
    ) -> bool:
        """Determine if agent should respond to a mention."""
        # Less communicative agents might ignore some mentions
        if personality.communication < 0.3:
            # Only respond to direct questions
            return "?" in mention_content or "@" in mention_content
        return True

    def _get_review_style(self) -> dict[str, Any]:
        """Get review style based on personality."""
        personality = self.agent.personality

        return {
            "num_comments": int(personality.strictness * 10),
            "tone": "critical" if personality.strictness > 0.7 else "constructive",
            "detailed": personality.formality > 0.5,
            "uses_emojis": personality.emoji_usage > 0.3,
        }
