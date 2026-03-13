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


@dataclass
class PullRequestInfo:
    """Pull request information."""

    pr_number: int
    title: str
    body: str
    head_branch: str
    base_branch: str
    author_id: str
    status: str  # 'open', 'closed', 'merged'
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0
    merge_commit_sha: str | None = None


@dataclass
class PRReview:
    """PR review information."""

    reviewer_id: str
    review_type: str  # 'approved', 'changes_requested', 'commented'
    body: str
    comments: list[dict] = field(default_factory=list)


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
        self._pr_counter = 0  # Local PR number counter
        self._pull_requests: dict[int, PullRequestInfo] = {}  # In-memory PR storage

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

        # If from_branch is not specified, use current branch
        if from_branch is None:
            result = self._run_git_command(["checkout", "-b", name])
        else:
            # Check if the source branch exists
            branch_result = self._run_git_command(["show-ref", "--verify", "--quiet", f"refs/heads/{from_branch}"])
            if branch_result.returncode != 0:
                # Source branch doesn't exist, use current branch instead
                result = self._run_git_command(["checkout", "-b", name])
            else:
                result = self._run_git_command(["checkout", "-b", name, from_branch])

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

    def create_pr(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        author_id: str,
    ) -> PullRequestInfo | None:
        """
        Create a pull request.

        Args:
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch
            author_id: Author agent ID

        Returns:
            PullRequestInfo or None if failed
        """
        self._check_initialized()

        # Verify head branch exists
        status = self.status()
        if head_branch not in status.branches:
            return None

        # Calculate changes (simplified - count files different from base)
        result = self._run_git_command(["diff", "--stat", f"{base_branch}..{head_branch}"])
        additions, deletions, files_changed = 0, 0, 0
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            for line in lines[:-1]:  # Last line is summary
                parts = line.split("|")
                if len(parts) >= 2:
                    files_changed += 1
                    # Parse + and - counts
                    diff_part = parts[-1] if len(parts) > 1 else ""
                    additions += diff_part.count("+")
                    deletions += diff_part.count("-")

        # Create PR
        self._pr_counter += 1
        pr_number = self._pr_counter

        pr = PullRequestInfo(
            pr_number=pr_number,
            title=title,
            body=body,
            head_branch=head_branch,
            base_branch=base_branch,
            author_id=author_id,
            status="open",
            additions=additions,
            deletions=deletions,
            files_changed=files_changed,
        )

        self._pull_requests[pr_number] = pr
        return pr

    def merge_pr(
        self,
        pr_number: int,
        merge_method: str = "merge",  # 'merge', 'squash', 'rebase'
    ) -> tuple[bool, str]:
        """
        Merge a pull request.

        Args:
            pr_number: PR number to merge
            merge_method: Merge method to use

        Returns:
            Tuple of (success, message)
        """
        self._check_initialized()

        pr = self._pull_requests.get(pr_number)
        if not pr:
            return False, f"PR #{pr_number} not found"

        if pr.status != "open":
            return False, f"PR #{pr_number} is already {pr.status}"

        # Switch to base branch
        self.switch_branch(pr.base_branch)

        # Merge the head branch
        success, message = self.merge(pr.head_branch, no_ff=(merge_method == "merge"))

        if success:
            pr.status = "merged"
            pr.merge_commit_sha = self.log(1)[0].hash if self.log(1) else "unknown"
            return True, f"Merged PR #{pr_number}: {pr.title}"
        else:
            return False, message

    def get_pr(
        self,
        pr_number: int,
    ) -> PullRequestInfo | None:
        """
        Get a pull request by number.

        Args:
            pr_number: PR number

        Returns:
            PullRequestInfo or None
        """
        return self._pull_requests.get(pr_number)

    def get_pr_reviews(
        self,
        pr_number: int,
    ) -> list[PRReview]:
        """
        Get reviews for a PR.

        Args:
            pr_number: PR number

        Returns:
            List of PRReview
        """
        pr = self._pull_requests.get(pr_number)
        return getattr(pr, "_reviews", []) if pr else []

    def add_pr_review(
        self,
        pr_number: int,
        reviewer_id: str,
        review_type: str,
        body: str,
        comments: list[dict] | None = None,
    ) -> PRReview | None:
        """
        Add a review to a PR.

        Args:
            pr_number: PR number
            reviewer_id: Reviewer agent ID
            review_type: 'approved', 'changes_requested', or 'commented'
            body: Review body text
            comments: Optional line-level comments

        Returns:
            PRReview or None if PR not found
        """
        pr = self._pull_requests.get(pr_number)
        if not pr:
            return None

        review = PRReview(
            reviewer_id=reviewer_id,
            review_type=review_type,
            body=body,
            comments=comments or [],
        )

        if not hasattr(pr, "_reviews"):
            pr._reviews = []
        pr._reviews.append(review)
        return review

    def cleanup(self) -> None:
        """Clean up temporary directory."""
        if self._temp_dir and self.repo_path.exists():
            # Windows: Handle read-only files and file locks
            import stat
            import time

            def handle_remove_readonly(func, path, exc_info):
                """Error handler for shutil.rmtree that handles read-only files."""
                try:
                    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
                    func(path)
                except PermissionError:
                    # File is locked, skip it
                    pass

            # Try normal cleanup first
            try:
                shutil.rmtree(self.repo_path, onerror=handle_remove_readonly)
            except Exception:
                # If cleanup fails, wait and retry (handles file locks)
                time.sleep(0.5)
                try:
                    shutil.rmtree(self.repo_path, onerror=handle_remove_readonly)
                except Exception:
                    # Final attempt: just mark for deletion
                    pass

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
