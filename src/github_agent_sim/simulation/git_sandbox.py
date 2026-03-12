"""Git sandbox for safe Git operations."""

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GitStatus:
    """Git repository status."""

    branch: str
    branches: list[str] = field(default_factory=list)
    clean: bool = True
    staged: list[str] = field(default_factory=list)
    unstaged: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0


@dataclass
class CommitInfo:
    """Commit information."""

    hash: str
    message: str
    author: str
    timestamp: str
    parents: list[str] = field(default_factory=list)


class GitSandbox:
    """
    Git sandbox for safe Git operations.

    Provides isolated Git operations for agent simulation.
    """

    def __init__(
        self,
        repo_path: Path | str | None = None,
        remote_url: str | None = None,
        create: bool = True,
    ):
        """
        Initialize Git sandbox.

        Args:
            repo_path: Path to repository (creates temp dir if None)
            remote_url: Optional remote URL to clone from
            create: If True and repo_path doesn't exist, initialize new repo
        """
        if repo_path is None:
            self.repo_path = Path(tempfile.mkdtemp(prefix="git_sandbox_"))
            self._temp_dir = True
        else:
            self.repo_path = Path(repo_path)
            self._temp_dir = False

        self.remote_url = remote_url
        self._initialized = False

        if create:
            self._initialize()

    def _initialize(self) -> None:
        """Initialize or clone the repository."""
        self.repo_path.mkdir(parents=True, exist_ok=True)

        if self.remote_url:
            # Clone from remote
            self._run_git_command(["clone", self.remote_url, "."])
        else:
            # Initialize new repo
            self._run_git_command(["init"])
            self._run_git_command(["config", "user.name", "Agent"])
            self._run_git_command(["config", "user.email", "agent@example.com"])

        self._initialized = True

    def _run_git_command(
        self,
        args: list[str],
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run a Git command.

        Args:
            args: Git arguments (without 'git')
            capture_output: Whether to capture output

        Returns:
            CompletedProcess
        """
        cmd = ["git"] + args
        return subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=capture_output,
            text=True,
            check=False,
        )

    def _check_initialized(self) -> None:
        """Check if sandbox is initialized."""
        if not self._initialized:
            raise RuntimeError("GitSandbox not initialized")

    def status(self) -> GitStatus:
        """
        Get repository status.

        Returns:
            GitStatus object
        """
        self._check_initialized()

        # Get current branch
        result = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        branch = result.stdout.strip() if result.returncode == 0 else "main"

        # Get branches
        result = self._run_git_command(["branch", "--list"])
        branches = [
            b.strip().lstrip("* ").strip()
            for b in result.stdout.split("\n")
            if b.strip()
        ]

        # Get status
        result = self._run_git_command(["status", "--porcelain"])
        staged = []
        unstaged = []
        untracked = []

        for line in result.stdout.split("\n"):
            if not line.strip():
                continue
            status_code = line[:2]
            file_path = line[3:].strip()

            if status_code.startswith("??"):
                untracked.append(file_path)
            elif status_code.startswith(" M"):
                unstaged.append(file_path)
            elif status_code.startswith("M "):
                staged.append(file_path)
            elif status_code.startswith("A "):
                staged.append(file_path)
            elif status_code.startswith(" D"):
                unstaged.append(file_path)

        return GitStatus(
            branch=branch,
            branches=branches,
            clean=len(staged) == 0 and len(unstaged) == 0 and len(untracked) == 0,
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
        )

    def create_branch(self, name: str, from_branch: str | None = None) -> bool:
        """
        Create a new branch.

        Args:
            name: Branch name
            from_branch: Source branch (uses current if None)

        Returns:
            True if successful
        """
        self._check_initialized()

        if from_branch:
            result = self._run_git_command(
                ["checkout", "-b", name, from_branch]
            )
        else:
            result = self._run_git_command(["checkout", "-b", name])

        return result.returncode == 0

    def switch_branch(self, name: str) -> bool:
        """
        Switch to a branch.

        Args:
            name: Branch name

        Returns:
            True if successful
        """
        self._check_initialized()
        result = self._run_git_command(["checkout", name])
        return result.returncode == 0

    def add(self, files: list[str] | str) -> bool:
        """
        Stage files.

        Args:
            files: File path or list of paths

        Returns:
            True if successful
        """
        self._check_initialized()

        if isinstance(files, str):
            files = [files]

        result = self._run_git_command(["add"] + files)
        return result.returncode == 0

    def commit(self, message: str, files: list[str] | None = None) -> CommitInfo | None:
        """
        Create a commit.

        Args:
            message: Commit message
            files: Optional files to stage first

        Returns:
            CommitInfo or None if failed
        """
        self._check_initialized()

        # Stage files if provided
        if files:
            self.add(files)

        result = self._run_git_command(["commit", "-m", message])
        if result.returncode != 0:
            return None

        # Get commit info
        result = self._run_git_command(
            ["log", "-1", "--format=%H|%an|%ai|%s"]
        )
        parts = result.stdout.strip().split("|")

        return CommitInfo(
            hash=parts[0],
            message=parts[3] if len(parts) > 3 else message,
            author=parts[1] if len(parts) > 1 else "unknown",
            timestamp=parts[2] if len(parts) > 2 else "",
        )

    def log(self, count: int = 10) -> list[CommitInfo]:
        """
        Get commit history.

        Args:
            count: Number of commits

        Returns:
            List of CommitInfo
        """
        self._check_initialized()

        result = self._run_git_command(
            ["log", f"-{count}", "--format=%H|%an|%ai|%s|%P"]
        )

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            commits.append(
                CommitInfo(
                    hash=parts[0],
                    message=parts[3] if len(parts) > 3 else "",
                    author=parts[1] if len(parts) > 1 else "",
                    timestamp=parts[2] if len(parts) > 2 else "",
                    parents=parts[4].split() if len(parts) > 4 and parts[4] else [],
                )
            )

        return commits

    def read_file(self, path: str) -> str | None:
        """
        Read a file.

        Args:
            path: File path

        Returns:
            File content or None
        """
        file_path = self.repo_path / path
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, path: str, content: str) -> bool:
        """
        Write a file.

        Args:
            path: File path relative to repo root
            content: File content

        Returns:
            True if successful
        """
        self._check_initialized()

        file_path = self.repo_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return True

    def delete_file(self, path: str) -> bool:
        """
        Delete a file.

        Args:
            path: File path

        Returns:
            True if successful
        """
        self._check_initialized()

        file_path = self.repo_path / path
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def run_command(self, command: str) -> tuple[bool, str, str]:
        """
        Run a shell command in the sandbox.

        Args:
            command: Command to run

        Returns:
            Tuple of (success, stdout, stderr)
        """
        self._check_initialized()

        # Security: restrict certain commands
        forbidden = ["rm -rf", "sudo", "wget", "curl"]
        for f in forbidden:
            if f in command.lower():
                return False, "", f"Command not allowed: {f}"

        result = subprocess.run(
            command,
            cwd=self.repo_path,
            shell=True,
            capture_output=True,
            text=True,
        )

        return result.returncode == 0, result.stdout, result.stderr

    def merge(
        self,
        branch: str,
        no_ff: bool = False,
    ) -> tuple[bool, str]:
        """
        Merge a branch.

        Args:
            branch: Branch to merge
            no_ff: Use --no-ff flag

        Returns:
            Tuple of (success, message)
        """
        self._check_initialized()

        args = ["merge"]
        if no_ff:
            args.append("--no-ff")
        args.append(branch)

        result = self._run_git_command(args)

        if result.returncode == 0:
            return True, f"Merged {branch}"
        else:
            return False, result.stderr

    def cleanup(self) -> None:
        """Clean up temporary directory."""
        if self._temp_dir and self.repo_path.exists():
            shutil.rmtree(self.repo_path)

    def __enter__(self) -> "GitSandbox":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.cleanup()

    def __del__(self) -> None:
        """Destructor."""
        if hasattr(self, "_temp_dir") and self._temp_dir:
            self.cleanup()
