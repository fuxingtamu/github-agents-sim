"""SQLite database initialization and schema management."""

import sqlite3
from pathlib import Path

from ...config.settings import Settings, get_settings


def get_connection(settings: Settings | None = None) -> sqlite3.Connection:
    """Get a database connection with PRAGMA optimizations."""
    if settings is None:
        settings = get_settings()

    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.row_factory = sqlite3.Row

    return conn


def init_database(conn: sqlite3.Connection | None = None) -> None:
    """Initialize database schema."""
    if conn is None:
        conn = get_connection()
        close = True
    else:
        close = False

    try:
        cursor = conn.cursor()

        # Developers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS developers (
                id              TEXT PRIMARY KEY,
                login           TEXT UNIQUE NOT NULL,

                -- Basic stats
                total_commits   INTEGER DEFAULT 0,
                total_prs       INTEGER DEFAULT 0,
                total_reviews   INTEGER DEFAULT 0,

                -- Personality traits
                strictness      REAL DEFAULT 0.5,
                communication   REAL DEFAULT 0.5,
                response_speed  REAL DEFAULT 0.5,
                cooperation     REAL DEFAULT 0.5,

                -- Role and persona
                role            TEXT,
                persona_type    TEXT,

                -- Metadata
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Behaviors table (unified design)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS behaviors (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                developer_id    TEXT NOT NULL,
                repo            TEXT NOT NULL,
                behavior_type   TEXT NOT NULL,
                content         TEXT NOT NULL,
                timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                text_content    TEXT,

                FOREIGN KEY (developer_id) REFERENCES developers(id)
            )
        """)

        # Simulations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulations (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                config          TEXT,
                started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at        TIMESTAMP,
                status          TEXT DEFAULT 'running'
            )
        """)

        # Agents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id              TEXT PRIMARY KEY,
                simulation_id   TEXT NOT NULL,
                name            TEXT NOT NULL,
                role            TEXT NOT NULL,
                persona_type    TEXT NOT NULL,
                personality     TEXT,
                status          TEXT DEFAULT 'active',

                FOREIGN KEY (simulation_id) REFERENCES simulations(id)
            )
        """)

        # Simulation actions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sim_actions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id   TEXT NOT NULL,
                agent_id        TEXT NOT NULL,
                timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action_type     TEXT NOT NULL,
                action_data     TEXT,
                trigger         TEXT,

                FOREIGN KEY (simulation_id) REFERENCES simulations(id),
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id              TEXT PRIMARY KEY,
                simulation_id   TEXT NOT NULL,
                sender_id       TEXT NOT NULL,
                channel         TEXT NOT NULL,
                content         TEXT NOT NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (simulation_id) REFERENCES simulations(id),
                FOREIGN KEY (sender_id) REFERENCES agents(id)
            )
        """)

        # Behavior vectors table (for RAG)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS behavior_vectors (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                behavior_id     INTEGER NOT NULL,
                vector          BLOB,
                metadata        TEXT,

                FOREIGN KEY (behavior_id) REFERENCES behaviors(id)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_behaviors_dev
            ON behaviors(developer_id, behavior_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_behaviors_time
            ON behaviors(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sim_actions_session
            ON sim_actions(simulation_id, timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(simulation_id)
        """)

        # Create trigger for auto-cleanup of old simulations
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS cleanup_old_simulations
            AFTER INSERT ON simulations
            BEGIN
                DELETE FROM simulations
                WHERE id IN (
                    SELECT id FROM simulations
                    ORDER BY started_at DESC
                    LIMIT -1 OFFSET 50
                );
            END
        """)

        conn.commit()

    finally:
        if close:
            conn.close()


def vacuum_database(conn: sqlite3.Connection | None = None) -> None:
    """Vacuum database to reclaim space."""
    if conn is None:
        conn = get_connection()
        close = True
    else:
        close = False

    try:
        conn.execute("VACUUM")
        conn.commit()
    finally:
        if close:
            conn.close()


def get_storage_usage(settings: Settings | None = None) -> dict:
    """Get storage usage statistics."""
    if settings is None:
        settings = get_settings()

    db_path = settings.db_path
    if not db_path.exists():
        return {"total_gb": 0, "percentage": 0}

    total_bytes = db_path.stat().st_size
    total_gb = total_bytes / (1024 ** 3)
    percentage = (total_gb / settings.max_storage_gb) * 100

    return {
        "total_gb": round(total_gb, 2),
        "max_gb": settings.max_storage_gb,
        "percentage": round(percentage, 1),
    }


if __name__ == "__main__":
    # Initialize database when run directly
    init_database()
    print("Database initialized successfully!")
    print(f"Storage usage: {get_storage_usage()}")
