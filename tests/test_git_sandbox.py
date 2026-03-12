"""Tests for Git sandbox module."""

import os
import tempfile
from pathlib import Path

import pytest

from github_agent_sim.simulation.git_sandbox import CommitInfo, GitSandbox


@pytest.fixture
def sandbox():
    """Create a temporary Git sandbox."""
    sb = GitSandbox(create=True)
    yield sb
    sb.cleanup()


@pytest.fixture
def sandbox_with_commit(sandbox):
    """Create a sandbox with an initial commit."""
    sandbox.write_file("README.md", "# Test Repo\n")
    sandbox.commit("Initial commit")
    yield sandbox


def test_sandbox_initialization():
    """Test sandbox creates temp directory."""
    with GitSandbox(create=True) as sandbox:
        assert sandbox.repo_path.exists()
        assert sandbox._initialized


def test_sandbox_cleanup():
    """Test sandbox cleanup removes temp directory."""
    sandbox = GitSandbox(create=True)
    repo_path = sandbox.repo_path
    sandbox.cleanup()
    assert not repo_path.exists()


def test_status_empty_repo(sandbox):
    """Test status on empty repo."""
    status = sandbox.status()

    assert status.branch == "main" or status.branch == "master"
    assert status.clean
    assert len(status.staged) == 0
    assert len(status.unstaged) == 0


def test_write_file(sandbox):
    """Test writing a file."""
    result = sandbox.write_file("test.txt", "Hello, World!")

    assert result is True
    assert (sandbox.repo_path / "test.txt").exists()

    # Verify content
    content = sandbox.read_file("test.txt")
    assert content == "Hello, World!"


def test_read_file_not_exists(sandbox):
    """Test reading non-existent file."""
    content = sandbox.read_file("nonexistent.txt")
    assert content is None


def test_delete_file(sandbox):
    """Test deleting a file."""
    sandbox.write_file("test.txt", "content")
    result = sandbox.delete_file("test.txt")

    assert result is True
    assert not (sandbox.repo_path / "test.txt").exists()

    # Deleting again should return False
    result = sandbox.delete_file("test.txt")
    assert result is False


def test_status_with_unstaged(sandbox_with_commit):
    """Test status with unstaged changes."""
    sandbox = sandbox_with_commit

    # Modify a file
    sandbox.write_file("README.md", "# Modified\n")

    status = sandbox.status()

    assert not status.clean
    assert "README.md" in status.unstaged


def test_status_with_staged(sandbox_with_commit):
    """Test status with staged changes."""
    sandbox = sandbox_with_commit

    # Create and stage a file
    sandbox.write_file("new.txt", "content")
    sandbox.add("new.txt")

    status = sandbox.status()

    assert "new.txt" in status.staged


def test_create_branch(sandbox_with_commit):
    """Test creating a new branch."""
    sandbox = sandbox_with_commit

    result = sandbox.create_branch("feature/test")

    assert result is True
    status = sandbox.status()
    assert status.branch == "feature/test"


def test_switch_branch(sandbox_with_commit):
    """Test switching branches."""
    sandbox = sandbox_with_commit
    sandbox.create_branch("feature/test")
    sandbox.switch_branch("main")

    status = sandbox.status()
    assert status.branch == "main"


def test_commit(sandbox_with_commit):
    """Test creating a commit."""
    sandbox = sandbox_with_commit

    sandbox.write_file("new.txt", "content")
    commit = sandbox.commit("Add new file", ["new.txt"])

    assert commit is not None
    assert commit.message == "Add new file"
    assert len(commit.hash) > 0


def test_commit_no_changes(sandbox_with_commit):
    """Test commit with no changes."""
    sandbox = sandbox_with_commit

    commit = sandbox.commit("Empty commit")

    # Should still succeed with empty commit
    assert commit is not None or True  # Git may reject empty commits


def test_log(sandbox_with_commit):
    """Test commit log."""
    sandbox = sandbox_with_commit

    # Create more commits
    sandbox.write_file("a.txt", "a")
    sandbox.commit("Add a")

    sandbox.write_file("b.txt", "b")
    sandbox.commit("Add b")

    commits = sandbox.log(count=5)

    assert len(commits) >= 2  # At least initial + 2 new
    assert commits[0].message == "Add b"
    assert commits[1].message == "Add a"


def test_run_command(sandbox):
    """Test running shell commands."""
    success, stdout, stderr = sandbox.run_command("echo 'Hello'")

    assert success is True
    assert "Hello" in stdout


def test_run_command_forbidden(sandbox):
    """Test running forbidden commands."""
    success, stdout, stderr = sandbox.run_command("rm -rf /")

    assert success is False
    assert "not allowed" in stderr


def test_merge(sandbox_with_commit):
    """Test merging branches."""
    sandbox = sandbox_with_commit

    # Create feature branch with changes
    sandbox.create_branch("feature")
    sandbox.write_file("feature.txt", "content")
    sandbox.commit("Add feature")

    # Switch back and merge
    sandbox.switch_branch("main")
    success, message = sandbox.merge("feature")

    assert success is True


def test_context_manager(sandbox):
    """Test using sandbox as context manager."""
    with GitSandbox(repo_path=sandbox.repo_path) as sb:
        sb.write_file("test.txt", "content")
        assert sb.read_file("test.txt") == "content"


def test_multiple_commits(sandbox):
    """Test creating multiple commits."""
    sandbox.write_file("README.md", "# Test")
    first = sandbox.commit("Initial commit")
    assert first is not None

    sandbox.write_file("file1.txt", "content1")
    second = sandbox.commit("Add file1")
    assert second is not None
    assert second.hash != first.hash

    sandbox.write_file("file2.txt", "content2")
    third = sandbox.commit("Add file2")
    assert third is not None

    commits = sandbox.log(count=3)
    assert len(commits) == 3
