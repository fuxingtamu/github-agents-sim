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
    """Run the example simulation with complete PR workflow."""
    print("=" * 60)
    print("GitHub Agent Simulation - Example Runner (Phase 2)")
    print("=" * 60)

    # Initialize settings
    settings = get_settings()
    settings.ensure_directories()

    # Initialize database
    print("\n[1/5] Initializing database...")
    init_database()
    print("  [OK] Database initialized")

    # Create simulation ID
    simulation_id = "sim_phase2_001"

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

    # Create a base feature file for more realistic demo
    sandbox.write_file("main.py", "# Main application\n\ndef main():\n    print('Hello World!')\n\nif __name__ == '__main__':\n    main()\n")
    sandbox.add("main.py")
    sandbox.commit("Add main application")

    # Set sandbox for all agents' action modules
    for agent in agents:
        agent.action_module.sandbox = sandbox

    print("  [OK] Git sandbox ready")

    # Initialize message queue
    print(f"\n[4/5] Setting up communication...")
    message_queue = MessageQueue()
    mention_system = MentionSystem(message_queue)

    # Subscribe agents to channels
    for agent in agents:
        message_queue.subscribe(agent.agent_id, "general")
        mention_system.register_agent(agent.agent_id, agent.name)

    print("  [OK] Communication ready")

    # Initialize event bus
    event_bus = get_event_bus()
    print("  [OK] Event bus ready")

    # Run simulation cycles
    print(f"\n[5/5] Running simulation cycles...")

    # ========== Cycle 1: Contributor creates feature ==========
    print("\n" + "=" * 50)
    print("Cycle 1: Creating Feature Branch")
    print("=" * 50)

    contributor = agents[2]  # Charlie
    print(f"\n[{contributor.name}] Creating feature branch and implementing feature...")

    # Create feature branch
    result = contributor.action_module.create_branch("feature/user-greeting")
    print(f"  Branch created: {result.message if result.success else result.error}")

    # Write feature code
    contributor.action_module.write_file(
        "greeting.py",
        "# User greeting feature\n\ndef greet_user(name: str) -> str:\n    return f'Hello, {name}! Welcome to our app.'\n\ndef greet_with_time(name: str, hour: int) -> str:\n    if hour < 12:\n        greeting = 'Good morning'\n    elif hour < 18:\n        greeting = 'Good afternoon'\n    else:\n        greeting = 'Good evening'\n    return f'{greeting}, {name}!'\n"
    )
    print("  File written: greeting.py")

    # Commit changes
    result = contributor.action_module.commit(
        "Add user greeting feature",
        ["greeting.py"]
    )
    print(f"  Committed: {result.message if result.success else result.error}")

    # ========== Cycle 2: Create PR ==========
    print("\n" + "=" * 50)
    print("Cycle 2: Creating Pull Request")
    print("=" * 50)

    # Create PR using the new Phase 2 functionality
    result = contributor.action_module.create_pr(
        title="Add user greeting feature",
        body="This PR adds a new greeting feature with time-based greetings.\n\nChanges:\n- Added greet_user() function\n- Added greet_with_time() function\n\nCloses issue #1",
        head="feature/user-greeting",
        base="main",
    )
    print(f"\n[{contributor.name}] {result.message if result.success else result.error}")

    if result.error:
        print(f"  Error: {result.error}")

    # ========== Cycle 3: Reviewer reviews PR ==========
    print("\n" + "=" * 50)
    print("Cycle 3: Code Review")
    print("=" * 50)

    reviewer = agents[1]  # Bob
    print(f"\n[{reviewer.name}] Reviewing PR #1...")

    # Reviewer approves the PR
    result = reviewer.action_module.review_pr(
        pr_number=1,
        decision="approved",
        body="LGTM! The code looks clean and well-documented. The time-based greeting is a nice touch.",
        comments=[
            {"line": 5, "comment": "Consider adding type hints"},
        ],
    )
    print(f"  Review submitted: {result.message if result.success else result.error}")

    # ========== Cycle 4: Maintainer merges PR ==========
    print("\n" + "=" * 50)
    print("Cycle 4: Merging PR")
    print("=" * 50)

    maintainer = agents[0]  # Alice
    print(f"\n[{maintainer.name}] Merging PR #1...")

    # Maintainer merges the PR
    result = maintainer.action_module.merge_pr(
        pr_number=1,
        merge_method="merge",
    )
    print(f"  Merge result: {result.message if result.success else result.error}")

    if result.error:
        print(f"  Error: {result.error}")

    # ========== Summary ==========
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
        print(f"  [{msg.channel}] {msg.sender_id}: {msg.content[:60]}...")

    # Print PR status
    print("\nPull Request Status:")
    pr = sandbox.get_pr(1)
    if pr:
        print(f"  PR #{pr.pr_number}: {pr.title}")
        print(f"    Status: {pr.status}")
        print(f"    Branch: {pr.head_branch} -> {pr.base_branch}")
        print(f"    Author: {pr.author_id}")
        if pr.merge_commit_sha:
            print(f"    Merge Commit: {pr.merge_commit_sha}")

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
