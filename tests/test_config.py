"""Tests for configuration module."""

import os
from pathlib import Path

import pytest

from github_agent_sim.config.settings import Settings, get_settings


@pytest.fixture
def test_env():
    """Set up test environment."""
    os.environ["DATA_DIR"] = "/tmp/test_data"
    os.environ["LLM_API_KEY"] = "test-key"
    yield
    # Cleanup
    if "DATA_DIR" in os.environ:
        del os.environ["DATA_DIR"]
    if "LLM_API_KEY" in os.environ:
        del os.environ["LLM_API_KEY"]


def test_settings_default_values(test_env):
    """Test default settings values."""
    settings = Settings()

    assert settings.max_storage_gb == 5.0
    assert settings.default_agent_count == 5
    assert settings.max_agent_count == 50
    assert settings.log_level == "INFO"


def test_settings_from_env(test_env):
    """Test settings loaded from environment."""
    os.environ["MAX_STORAGE_GB"] = "10.0"
    os.environ["DEFAULT_AGENT_COUNT"] = "3"
    os.environ["LOG_LEVEL"] = "DEBUG"

    # Clear cached settings
    get_settings.cache_clear()

    settings = Settings()

    assert settings.max_storage_gb == 10.0
    assert settings.default_agent_count == 3
    assert settings.log_level == "DEBUG"

    # Cleanup
    del os.environ["MAX_STORAGE_GB"]
    del os.environ["DEFAULT_AGENT_COUNT"]
    del os.environ["LOG_LEVEL"]
    get_settings.cache_clear()


def test_settings_data_dir_resolution(test_env):
    """Test data directory path resolution."""
    settings = Settings()

    # Should resolve to absolute path
    assert settings.data_dir.is_absolute()
    assert str(settings.data_dir) == "/tmp/test_data"


def test_settings_database_url_generation(test_env):
    """Test database URL generation from data_dir."""
    settings = Settings()

    # Should generate database URL from data_dir
    assert settings.database_url.startswith("sqlite:///")
    assert "github_sim.db" in settings.database_url


def test_settings_ensure_directories(test_env, tmp_path):
    """Test directory creation."""
    os.environ["DATA_DIR"] = str(tmp_path / "test_data")

    settings = Settings()
    settings.ensure_directories()

    # Check directories created
    assert (settings.data_dir / "db").exists()
    assert (settings.data_dir / "raw" / "samples").exists()
    assert (settings.data_dir / "logs").exists()
    assert (settings.data_dir / "vectors").exists()
    assert (settings.data_dir / "cache").exists()


def test_settings_validation_agent_count():
    """Test agent count validation."""
    # Valid values
    settings = Settings(default_agent_count=1)
    assert settings.default_agent_count == 1

    settings = Settings(default_agent_count=100)
    assert settings.default_agent_count == 100


def test_get_settings_singleton(test_env):
    """Test get_settings returns cached instance."""
    get_settings.cache_clear()

    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2

    get_settings.cache_clear()
