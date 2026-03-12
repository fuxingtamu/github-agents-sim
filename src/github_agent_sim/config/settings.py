"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Project paths
    project_root: Path = Field(
        default=Path(__file__).parent.parent.parent.parent,
        description="Project root directory",
    )
    data_dir: Path = Field(
        default=None,
        description="Data storage directory",
    )

    # LLM Configuration
    llm_api_base: str = Field(
        default="https://your-llm-proxy.com/v1",
        description="LLM API base URL",
    )
    llm_api_key: str = Field(
        default="",
        description="LLM API key",
    )
    llm_model: str = Field(
        default="claude-sonnet-4-6-20250929",
        description="LLM model name",
    )

    # Storage Configuration
    max_storage_gb: float = Field(
        default=5.0,
        description="Maximum storage size in GB",
    )

    # Database Configuration
    database_url: str = Field(
        default=None,
        description="SQLite database URL",
    )

    # ChromaDB Configuration
    chroma_persist_dir: Optional[Path] = Field(
        default=None,
        description="ChromaDB persistence directory",
    )

    # Simulation Configuration
    default_agent_count: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Default number of agents",
    )
    max_agent_count: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of agents",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: str = Field(
        default="json",
        description="Logging format",
    )

    # GitHub API (optional)
    github_token: Optional[str] = Field(
        default=None,
        description="GitHub API token",
    )

    # Retry Configuration
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts",
    )
    retry_backoff: float = Field(
        default=2.0,
        ge=1.0,
        description="Retry backoff multiplier",
    )

    @field_validator("project_root", "data_dir", mode="before")
    @classmethod
    def resolve_path(cls, v: Optional[str | Path]) -> Path:
        """Resolve path values to absolute paths."""
        if v is None:
            v = Path.cwd()
        path = Path(v).resolve()
        return path

    @field_validator("database_url", mode="before")
    @classmethod
    def set_default_database_url(cls, v: Optional[str], info) -> str:
        """Set default database URL if not provided."""
        if v:
            return v
        # Get data_dir from values or use default
        data_dir = info.data.get("data_dir")
        if data_dir is None:
            data_dir = Path.cwd() / "data"
        db_path = Path(data_dir) / "db" / "github_sim.db"
        return f"sqlite:///{db_path}"

    @field_validator("chroma_persist_dir", mode="before")
    @classmethod
    def set_chroma_dir(cls, v: Optional[str], info) -> Optional[Path]:
        """Set ChromaDB persistence directory."""
        if v:
            return Path(v).resolve()
        data_dir = info.data.get("data_dir")
        if data_dir is None:
            data_dir = Path.cwd() / "data"
        return Path(data_dir) / "vectors" / "chroma"

    @property
    def db_path(self) -> Path:
        """Get the database file path."""
        return Path(self.database_url.replace("sqlite:///", ""))

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        dirs = [
            self.data_dir,
            self.data_dir / "db",
            self.data_dir / "raw" / "samples",
            self.data_dir / "logs",
            self.data_dir / "vectors",
            self.data_dir / "cache",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience access
settings = get_settings()
