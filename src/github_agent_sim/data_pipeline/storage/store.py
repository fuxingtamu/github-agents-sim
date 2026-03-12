"""SQLite storage layer for developers and behaviors."""

import json
import sqlite3
from datetime import datetime
from typing import Any

from ..processors.behavior_extractor import DeveloperProfile
from ..processors.event_parser import (
    IssueCommentEvent,
    ParsedEvent,
    PullRequestEvent,
    PullRequestReviewEvent,
    PushEvent,
)
from .database import get_connection, init_database


class DeveloperStore:
    """Storage operations for developers."""

    @staticmethod
    def insert_or_update(profile: DeveloperProfile, conn: sqlite3.Connection | None = None) -> None:
        """Insert or update a developer profile."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO developers (
                    id, login, total_commits, total_prs, total_reviews,
                    strictness, communication, response_speed, cooperation,
                    role, persona_type, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    login = excluded.login,
                    total_commits = excluded.total_commits,
                    total_prs = excluded.total_prs,
                    total_reviews = excluded.total_reviews,
                    strictness = excluded.strictness,
                    communication = excluded.communication,
                    response_speed = excluded.response_speed,
                    cooperation = excluded.cooperation,
                    role = excluded.role,
                    persona_type = excluded.persona_type,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    profile.developer_id,
                    profile.login,
                    profile.total_commits,
                    profile.total_prs,
                    profile.total_reviews,
                    profile.strictness,
                    profile.communication,
                    profile.response_speed,
                    profile.cooperation,
                    "contributor",  # Default role
                    None,  # Persona type to be inferred
                ),
            )
            conn.commit()
        finally:
            if close:
                conn.close()

    @staticmethod
    def get_by_id(developer_id: str, conn: sqlite3.Connection | None = None) -> DeveloperProfile | None:
        """Get a developer by ID."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM developers WHERE id = ?",
                (developer_id,),
            )
            row = cursor.fetchone()

            if row:
                return DeveloperProfile(
                    login=row["login"],
                    developer_id=row["id"],
                    total_commits=row["total_commits"] or 0,
                    total_prs=row["total_prs"] or 0,
                    total_reviews=row["total_reviews"] or 0,
                    strictness=row["strictness"] or 0.5,
                    communication=row["communication"] or 0.5,
                    response_speed=row["response_speed"] or 0.5,
                    cooperation=row["cooperation"] or 0.5,
                    formality=0.5,  # Not stored
                    emoji_usage=0.0,  # Not stored
                )
            return None
        finally:
            if close:
                conn.close()

    @staticmethod
    def get_all(conn: sqlite3.Connection | None = None) -> list[DeveloperProfile]:
        """Get all developers."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM developers")
            rows = cursor.fetchall()

            profiles = []
            for row in rows:
                profiles.append(
                    DeveloperProfile(
                        login=row["login"],
                        developer_id=row["id"],
                        total_commits=row["total_commits"] or 0,
                        total_prs=row["total_prs"] or 0,
                        total_reviews=row["total_reviews"] or 0,
                        strictness=row["strictness"] or 0.5,
                        communication=row["communication"] or 0.5,
                        response_speed=row["response_speed"] or 0.5,
                        cooperation=row["cooperation"] or 0.5,
                    )
                )
            return profiles
        finally:
            if close:
                conn.close()


class BehaviorStore:
    """Storage operations for behaviors."""

    @staticmethod
    def insert(
        developer_id: str,
        repo: str,
        behavior_type: str,
        content: dict[str, Any],
        text_content: str | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> int:
        """Insert a behavior record."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO behaviors (developer_id, repo, behavior_type, content, text_content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    developer_id,
                    repo,
                    behavior_type,
                    json.dumps(content),
                    text_content,
                ),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            if close:
                conn.close()

    @staticmethod
    def insert_parsed_event(
        event: ParsedEvent | PushEvent | PullRequestEvent | PullRequestReviewEvent | IssueCommentEvent,
        conn: sqlite3.Connection | None = None,
    ) -> int | None:
        """Insert a parsed event as a behavior."""
        if isinstance(event, PushEvent):
            return BehaviorStore.insert(
                developer_id=event.event.actor_id,
                repo=event.event.repo_name,
                behavior_type="push",
                content={
                    "ref": event.ref,
                    "head": event.head,
                    "commits": event.commits,
                    "size": event.size,
                },
                conn=conn,
            )
        elif isinstance(event, PullRequestEvent):
            return BehaviorStore.insert(
                developer_id=event.event.actor_id,
                repo=event.event.repo_name,
                behavior_type="pr",
                content={
                    "action": event.action,
                    "number": event.number,
                    "pr_id": event.pr_id,
                    "state": event.state,
                    "merged": event.merged,
                    "additions": event.additions,
                    "deletions": event.deletions,
                },
                text_content=event.body,
                conn=conn,
            )
        elif isinstance(event, PullRequestReviewEvent):
            return BehaviorStore.insert(
                developer_id=event.event.actor_id,
                repo=event.event.repo_name,
                behavior_type="review",
                content={
                    "action": event.action,
                    "review_state": event.review_state,
                    "pr_number": event.pr_number,
                },
                text_content=event.review_body,
                conn=conn,
            )
        elif isinstance(event, IssueCommentEvent):
            return BehaviorStore.insert(
                developer_id=event.event.actor_id,
                repo=event.event.repo_name,
                behavior_type="comment",
                content={
                    "action": event.action,
                    "comment_id": event.comment_id,
                    "issue_number": event.issue_number,
                },
                text_content=event.comment_body,
                conn=conn,
            )
        else:
            return BehaviorStore.insert(
                developer_id=event.actor_id,
                repo=event.repo_name,
                behavior_type=event.type,
                content={},
                conn=conn,
            )

    @staticmethod
    def get_by_developer(
        developer_id: str,
        behavior_type: str | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]:
        """Get behaviors for a developer."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            if behavior_type:
                cursor.execute(
                    """
                    SELECT * FROM behaviors
                    WHERE developer_id = ? AND behavior_type = ?
                    ORDER BY timestamp DESC
                    """,
                    (developer_id, behavior_type),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM behaviors
                    WHERE developer_id = ?
                    ORDER BY timestamp DESC
                    """,
                    (developer_id,),
                )

            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "developer_id": row["developer_id"],
                    "repo": row["repo"],
                    "behavior_type": row["behavior_type"],
                    "content": json.loads(row["content"]),
                    "timestamp": row["timestamp"],
                    "text_content": row["text_content"],
                }
                for row in rows
            ]
        finally:
            if close:
                conn.close()


class AgentStore:
    """Storage operations for agents."""

    @staticmethod
    def insert(
        agent_id: str,
        simulation_id: str,
        name: str,
        role: str,
        persona_type: str,
        personality: str | None = None,
        status: str = "active",
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Insert an agent record."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO agents (id, simulation_id, name, role, persona_type, personality, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (agent_id, simulation_id, name, role, persona_type, personality, status),
            )
            conn.commit()
        finally:
            if close:
                conn.close()

    @staticmethod
    def get_by_id(agent_id: str, conn: sqlite3.Connection | None = None) -> dict | None:
        """Get an agent by ID."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agents WHERE id = ?",
                (agent_id,),
            )
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None
        finally:
            if close:
                conn.close()

    @staticmethod
    def get_by_simulation(simulation_id: str, conn: sqlite3.Connection | None = None) -> list[dict]:
        """Get all agents for a simulation."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agents WHERE simulation_id = ?",
                (simulation_id,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            if close:
                conn.close()


class SimulationStore:
    """Storage operations for simulations."""

    @staticmethod
    def insert(
        simulation_id: str,
        name: str,
        config: dict | None = None,
        status: str = "running",
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Insert a simulation record."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO simulations (id, name, config, status)
                VALUES (?, ?, ?, ?)
                """,
                (simulation_id, name, json.dumps(config) if config else None, status),
            )
            conn.commit()
        finally:
            if close:
                conn.close()

    @staticmethod
    def update_status(
        simulation_id: str,
        status: str,
        ended_at: datetime | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Update simulation status."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            if ended_at:
                cursor.execute(
                    """
                    UPDATE simulations
                    SET status = ?, ended_at = ?
                    WHERE id = ?
                    """,
                    (status, ended_at, simulation_id),
                )
            else:
                cursor.execute(
                    "UPDATE simulations SET status = ? WHERE id = ?",
                    (status, simulation_id),
                )
            conn.commit()
        finally:
            if close:
                conn.close()

    @staticmethod
    def get_by_id(simulation_id: str, conn: sqlite3.Connection | None = None) -> dict | None:
        """Get a simulation by ID."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM simulations WHERE id = ?",
                (simulation_id,),
            )
            row = cursor.fetchone()

            if row:
                result = dict(row)
                if result.get("config"):
                    result["config"] = json.loads(result["config"])
                return result
            return None
        finally:
            if close:
                conn.close()


class MessageStore:
    """Storage operations for messages."""

    @staticmethod
    def insert(
        message_id: str,
        simulation_id: str,
        sender_id: str,
        channel: str,
        content: str,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Insert a message record."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO messages (id, simulation_id, sender_id, channel, content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, simulation_id, sender_id, channel, content),
            )
            conn.commit()
        finally:
            if close:
                conn.close()

    @staticmethod
    def get_by_channel(
        simulation_id: str,
        channel: str,
        conn: sqlite3.Connection | None = None,
    ) -> list[dict]:
        """Get messages for a channel."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM messages
                WHERE simulation_id = ? AND channel = ?
                ORDER BY created_at ASC
                """,
                (simulation_id, channel),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            if close:
                conn.close()

    @staticmethod
    def get_by_simulation(simulation_id: str, conn: sqlite3.Connection | None = None) -> list[dict]:
        """Get all messages for a simulation."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM messages
                WHERE simulation_id = ?
                ORDER BY created_at ASC
                """,
                (simulation_id,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            if close:
                conn.close()


class SimActionStore:
    """Storage operations for simulation actions."""

    @staticmethod
    def insert(
        simulation_id: str,
        agent_id: str,
        action_type: str,
        action_data: dict | None = None,
        trigger: str | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> int:
        """Insert a simulation action record."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sim_actions (simulation_id, agent_id, action_type, action_data, trigger)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    simulation_id,
                    agent_id,
                    action_type,
                    json.dumps(action_data) if action_data else None,
                    trigger,
                ),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            if close:
                conn.close()

    @staticmethod
    def get_by_simulation(
        simulation_id: str,
        agent_id: str | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> list[dict]:
        """Get actions for a simulation."""
        if conn is None:
            conn = get_connection()
            close = True
        else:
            close = False

        try:
            cursor = conn.cursor()
            if agent_id:
                cursor.execute(
                    """
                    SELECT * FROM sim_actions
                    WHERE simulation_id = ? AND agent_id = ?
                    ORDER BY timestamp ASC
                    """,
                    (simulation_id, agent_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM sim_actions
                    WHERE simulation_id = ?
                    ORDER BY timestamp ASC
                    """,
                    (simulation_id,),
                )

            rows = cursor.fetchall()
            result = []
            for row in rows:
                data = dict(row)
                if data.get("action_data"):
                    data["action_data"] = json.loads(data["action_data"])
                result.append(data)
            return result
        finally:
            if close:
                conn.close()


def process_events_to_storage(
    events: list[dict],
    conn: sqlite3.Connection | None = None,
) -> tuple[int, int]:
    """
    Process raw events and store to database.

    Returns:
        Tuple of (num_developers, num_behaviors)
    """
    from ..processors.event_parser import EventParser
    from .behavior_extractor import BehaviorExtractor

    parser = EventParser()
    extractor = BehaviorExtractor()

    if conn is None:
        conn = get_connection()
        close = True
    else:
        close = False

    try:
        # First pass: extract profiles
        for raw_event in events:
            parsed = parser.parse_any(raw_event)
            if parsed:
                extractor.process_event(parsed)

        # Save developer profiles
        for profile in extractor.get_profiles():
            DeveloperStore.insert_or_update(profile, conn=conn)

        # Second pass: save behaviors
        behavior_count = 0
        for raw_event in events:
            parsed = parser.parse_any(raw_event)
            if parsed:
                BehaviorStore.insert_parsed_event(parsed, conn=conn)
                behavior_count += 1

        return len(extractor.get_profiles()), behavior_count

    finally:
        if close:
            conn.close()
