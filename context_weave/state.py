"""
State Management for ContextWeave

Manages the minimal runtime state stored in .context-weave/state.json.
Most state is derived from Git (branches, notes, worktrees).
"""

import json
import logging
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import keyring

logger = logging.getLogger(__name__)


@dataclass
class WorktreeInfo:
    """Information about an active SubAgent worktree."""
    issue: int
    branch: str
    path: str
    role: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorktreeInfo":
        return cls(**data)


@dataclass
class GitHubConfig:
    """GitHub sync configuration."""
    enabled: bool = False
    owner: Optional[str] = None
    repo: Optional[str] = None
    project_number: Optional[int] = None
    last_sync: Optional[str] = None
    issue_cache: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitHubConfig":
        # Handle missing fields gracefully
        return cls(
            enabled=data.get("enabled", False),
            owner=data.get("owner"),
            repo=data.get("repo"),
            project_number=data.get("project_number"),
            last_sync=data.get("last_sync"),
            issue_cache=data.get("issue_cache", {})
        )


class State:
    """
    Manages ContextWeave runtime state.

    State is stored in .context-weave/state.json and tracks:
    - Active worktrees (SubAgent isolation)
    - GitHub sync configuration
    - Mode settings

    Most other state is derived directly from Git:
    - Issues -> Branches (issue-{N}-*)
    - Status -> Git notes (refs/notes/context)
    - Audit -> Commit history
    """

    SCHEMA_VERSION = "1.0"
    STATE_DIR = ".context-weave"
    STATE_FILE = "state.json"

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.state_dir = repo_root / self.STATE_DIR
        self.state_file = self.state_dir / self.STATE_FILE
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load state from file or create default."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = self._default_state()
        else:
            self._data = self._default_state()

    def _default_state(self) -> Dict[str, Any]:
        """Create default state structure."""
        return {
            "$schema": "https://contextweave.dev/schemas/state-v1.json",
            "version": self.SCHEMA_VERSION,
            "mode": "local",
            "worktrees": [],
            "local_issues": {},
            "auth": {
                "github_token": None,
                "github_token_created": None
            },
            "github": {
                "enabled": False,
                "owner": None,
                "repo": None,
                "project_number": None,
                "last_sync": None,
                "issue_cache": {}
            }
        }

    def save(self) -> None:
        """Save state to file."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    @property
    def mode(self) -> str:
        """Get current operating mode (local/github/hybrid)."""
        return self._data.get("mode", "local")

    @mode.setter
    def mode(self, value: str) -> None:
        """Set operating mode."""
        if value not in ("local", "github", "hybrid"):
            raise ValueError(f"Invalid mode: {value}. Must be local, github, or hybrid.")
        self._data["mode"] = value

    @property
    def worktrees(self) -> List[WorktreeInfo]:
        """Get list of active worktrees."""
        return [WorktreeInfo.from_dict(w) for w in self._data.get("worktrees", [])]

    def add_worktree(self, worktree: WorktreeInfo) -> None:
        """Add a worktree to tracking."""
        if "worktrees" not in self._data:
            self._data["worktrees"] = []
        self._data["worktrees"].append(worktree.to_dict())

    def remove_worktree(self, issue: int) -> Optional[WorktreeInfo]:
        """Remove a worktree from tracking by issue number."""
        worktrees = self._data.get("worktrees", [])
        for i, w in enumerate(worktrees):
            if w.get("issue") == issue:
                removed = worktrees.pop(i)
                return WorktreeInfo.from_dict(removed)
        return None

    def get_worktree(self, issue: int) -> Optional[WorktreeInfo]:
        """Get worktree info by issue number."""
        for w in self.worktrees:
            if w.issue == issue:
                return w
        return None

    @property
    def github(self) -> GitHubConfig:
        """Get GitHub configuration."""
        return GitHubConfig.from_dict(self._data.get("github", {}))

    @github.setter
    def github(self, config: GitHubConfig) -> None:
        """Set GitHub configuration."""
        self._data["github"] = config.to_dict()

    @property
    def local_issues(self) -> Dict[str, Any]:
        """Get locally tracked issues."""
        if "local_issues" not in self._data:
            self._data["local_issues"] = {}
        return self._data["local_issues"]

    @local_issues.setter
    def local_issues(self, issues: Dict[str, Any]) -> None:
        """Set locally tracked issues."""
        self._data["local_issues"] = issues

    @property
    def github_token(self) -> Optional[str]:
        """Get stored GitHub OAuth token from system keyring.

        Falls back to environment variable GITHUB_TOKEN for CI/CD.
        """
        import os

        # Try keyring first
        try:
            token = keyring.get_password("context-weave", "github_token")
            if token:
                return token
        except keyring.errors.KeyringError as e:
            # Specific keyring errors (backend issues, permissions, etc.)
            logger.warning("Keyring access failed: %s", e)
        except OSError as e:
            # File system or platform-specific errors
            logger.warning("OS error accessing keyring: %s", e)

        # Fallback to environment variable
        return os.getenv("GITHUB_TOKEN")

    @github_token.setter
    def github_token(self, token: Optional[str]) -> None:
        """Store GitHub OAuth token in system keyring.

        Never stores in state.json for security.
        """
        if token:
            try:
                keyring.set_password("context-weave", "github_token", token)
                logger.info("GitHub token stored securely in system keyring")
            except keyring.errors.KeyringError as e:
                logger.error("Failed to store token in keyring: %s", e)
                raise click.ClickException(
                    f"Failed to store token securely: {e}. "
                    "Ensure keyring is properly configured on your system."
                ) from e
            except OSError as e:
                logger.error("OS error storing token: %s", e)
                raise click.ClickException(
                    f"Failed to store token: {e}. Check system permissions."
                ) from e
        else:
            try:
                keyring.delete_password("context-weave", "github_token")
                logger.info("GitHub token removed from keyring")
            except keyring.errors.PasswordDeleteError:
                pass  # Token wasn't stored, that's fine
            except keyring.errors.KeyringError as e:
                logger.warning("Failed to delete token from keyring: %s", e)
            except OSError as e:
                logger.warning("OS error deleting token: %s", e)

    @property
    def github_token_created(self) -> Optional[str]:
        """Get timestamp when token was created."""
        auth = self._data.get("auth", {})
        return auth.get("github_token_created")

    @github_token_created.setter
    def github_token_created(self, timestamp: Optional[str]) -> None:
        """Set token creation timestamp."""
        if "auth" not in self._data:
            self._data["auth"] = {}
        self._data["auth"]["github_token_created"] = timestamp

    def update_github(self, enabled: Optional[bool] = None, last_sync: Optional[str] = None) -> None:
        """Update GitHub configuration."""
        if "github" not in self._data:
            self._data["github"] = {"enabled": False, "last_sync": None}
        if enabled is not None:
            self._data["github"]["enabled"] = enabled
        if last_sync is not None:
            self._data["github"]["last_sync"] = last_sync

    def is_initialized(self) -> bool:
        """Check if ContextWeave is initialized in this repository."""
        return self.state_file.exists()

    # Git-derived state methods

    def get_issue_branches(self) -> List[str]:
        """Get all issue branches from Git."""
        try:
            result = subprocess.run(
                ["git", "branch", "--list", "issue-*"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            branches = []
            for line in result.stdout.strip().split("\n"):
                branch = line.strip().lstrip("* ")
                if branch:
                    branches.append(branch)
            return branches
        except subprocess.CalledProcessError:
            return []

    def get_git_worktrees(self) -> List[Dict[str, str]]:
        """Get all Git worktrees."""
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            worktrees = []
            current: Dict[str, str] = {}
            for line in result.stdout.strip().split("\n"):
                if line.startswith("worktree "):
                    if current:
                        worktrees.append(current)
                    current = {"path": line[9:]}
                elif line.startswith("HEAD "):
                    current["head"] = line[5:]
                elif line.startswith("branch "):
                    current["branch"] = line[7:]
                elif line == "bare":
                    current["bare"] = True
            if current:
                worktrees.append(current)
            return worktrees
        except subprocess.CalledProcessError:
            return []

    def get_branch_note(self, branch: str, ref: str = "context") -> Optional[Dict[str, Any]]:
        """Get Git note for a branch."""
        try:
            result = subprocess.run(
                ["git", "notes", f"--ref={ref}", "show", f"refs/heads/{branch}"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout.strip())
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return None

    def set_branch_note(self, branch: str, data: Dict[str, Any], ref: str = "context") -> bool:
        """Set Git note for a branch."""
        try:
            json_data = json.dumps(data)
            subprocess.run(
                ["git", "notes", f"--ref={ref}", "add", "-f", "-m", json_data, f"refs/heads/{branch}"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def get_last_commit_time(self, branch: str) -> Optional[datetime]:
        """Get the timestamp of the last commit on a branch."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%aI", branch],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            timestamp = result.stdout.strip()
            if timestamp:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except subprocess.CalledProcessError:
            pass
        return None
