#!/usr/bin/env python3
"""
Example simulation runner.

This script demonstrates how to run a basic multi-agent simulation.
"""

import json
import os
from pathlib import Path

# Fix Windows console encoding
os.system('')  # Enable ANSI escape codes on Windows

from github_agent_sim.agents import (
    BotAgent,
    ContributorAgent,
    MaintainerAgent,
    ReviewerAgent,
)
from github_agent_sim.config.settings import get_settings
from github_agent_sim.data_pipeline.storage.database import init_database
from github_agent_sim.simulation.event_bus import EventTypes, get_event_bus
from github_agent_sim.simulation.git_sandbox import GitSandbox
from github_agent_sim.simulation.message_queue import MessageQueue, MentionSystem


# Use ASCII checkmarks for Windows compatibility
OK = '[OK]'


def create_agents(simulation_id: str) -> list:
    """
    Create a team of agents for simulation.

    Args:
        simulation_id: Simulation session ID

    Returns:
        List of agent instances
    """
    agents = [
        # Maintainer - mentor type
        MaintainerAgent(
            persona_type="mentor",
            simulation_id=simulation_id,
            name="Maintainer_Alice",
        ),
        # Reviewer - gatekeeper type
        ReviewerAgent(
            persona_type="gatekeeper",
            simulation_id=simulation_id,
            name="Reviewer_Bob",
        ),
        # Contributor - ninja type
        ContributorAgent(
            persona_type="ninja",
            simulation_id=simulation_id,
            name="Contributor_Charlie",
        ),
        # Contributor - collaborator type
        ContributorAgent(
            persona_type="collaborator",
            simulation_id=simulation_id,
            name="Contributor_Diana",
        ),
        # CI Bot
        BotAgent(
            bot_type="ci_bot",
            simulation_id=simulation_id,
            name="CI_Bot",
        ),
    ]

    return agents


def run_simulation_cycle(agents: list, sandbox: GitSandbox, message_queue: MessageQueue) -> None:
    """
    Run one simulation cycle.

    Each agent gets a chance to perceive, decide, and act.

    Args:
        agents: List of agents
        sandbox: Git sandbox
        message_queue: Message queue
    """
    print("\n=== Simulation Cycle ===\n")

    for agent in agents:
        print(f"[{agent.name}] ({agent.role}) - thinking...")

        # Perceive
        perception = agent.perceive()

        # Decide
        action = agent.decide(perception)

        # Act
        result = agent.act(action)

        print(f"    -> Action: {result.get('action_type', 'unknown')}")
        print(f"    -> Result: {result.get('message', 'no message')}")

        if result.get('error'):
            print(f"    -> Error: {result['error']}")

        print()


def main():
    """Run the example simulation."""
    print("=" * 60)
    print("GitHub Agent Simulation - Example Runner")
    print("=" * 60)

    # Initialize settings
    settings = get_settings()
    settings.ensure_directories()

    # Initialize database
    print("\n[1/5] Initializing database...")
    init_database()
    print("  [OK] Database initialized")

    # Create simulation ID
    simulation_id = "sim_example_001"

    # Create agents
    print(f"\n[2/5] Creating agents for simulation: {simulation_id}")
    agents = create_agents(simulation_id)

    for agent in agents:
        print(f"  [OK] {agent.name} ({agent.role}, {agent.persona_type})")

    # Initialize Git sandbox
    print(f"\n[3/5] Initializing Git sandbox...")
    sandbox = GitSandbox(create=True)

    # Create initial commit
    sandbox.write_file("README.md", "# Test Project\n\nThis is a test repository.\n")
    sandbox.add("README.md")
    sandbox.commit("Initial commit")
    print("  [OK] Git sandbox ready")

    # Initialize message queue
    print(f"\n[4/5] Setting up communication...")
    message_queue = MessageQueue()
    mention_system = MentionSystem(message_queue)

    # Subscribe agents to channels
    for agent in agents:
        message_queue.subscribe(agent.agent_id, "general")
        message_queue.subscribe(agent.agent_id, "PR #1")
        mention_system.register_agent(agent.agent_id, agent.name)

    print("  [OK] Communication ready")

    # Initialize event bus
    event_bus = get_event_bus()
    print("  [OK] Event bus ready")

    # Run simulation cycles
    print(f"\n[5/5] Running simulation cycles...")

    # Cycle 1: Contributor creates feature
    print("\n--- Cycle 1: Creating Feature ---")
    contributor = agents[2]  # Charlie
    contributor.action_module.create_branch("feature/new-feature")
    contributor.action_module.write_file("feature.py", "# New feature\n\ndef hello():\n    print('Hello!')\n")
    contributor.action_module.commit("Add new feature", ["feature.py"])

    run_simulation_cycle(agents, sandbox, message_queue)

    # Cycle 2: Contributor creates PR
    print("\n--- Cycle 2: Creating PR ---")
    contributor.send_message(
        content="Created PR #1 with new feature. @Reviewer_Bob can you review?",
        channel="general",
        mentions=[agents[1].agent_id],  # Mention Bob
    )

    run_simulation_cycle(agents, sandbox, message_queue)

    # Cycle 3: Reviewer reviews
    print("\n--- Cycle 3: Review Process ---")
    run_simulation_cycle(agents, sandbox, message_queue)

    # Print summary
    print("\n" + "=" * 60)
    print("Simulation Complete!")
    print("=" * 60)

    # Print agent states
    print("\nFinal Agent States:")
    for agent in agents:
        print(f"  {agent.name}: {agent.state.status}")
        if agent.state.last_action:
            print(f"    Last action: {agent.state.last_action}")

    # Print message history
    print("\nMessage History:")
    history = message_queue.get_history(limit=10)
    for msg in history:
        print(f"  [{msg.channel}] {msg.sender_id}: {msg.content[:50]}...")

    # Print event history
    print("\nEvent History:")
    events = event_bus.get_history(limit=5)
    for event in events:
        print(f"  {event.event_type}: {event.source}")

    # Cleanup
    print("\nCleaning up...")
    sandbox.cleanup()

    print("\nDone!")


if __name__ == "__main__":
    main()
