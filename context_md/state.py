"""
State Management for Context.md

Manages the minimal runtime state stored in .agent-context/state.json.
Most state is derived from Git (branches, notes, worktrees).
"""

import json
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class WorktreeInfo:
    """Information about an active SubAgent worktree."""
    issue: int
    branch: str
    path: str
    role: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorktreeInfo":
        return cls(**data)


@dataclass
class GitHubConfig:
    """GitHub sync configuration."""
    enabled: bool = False
    last_sync: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitHubConfig":
        return cls(**data)


class State:
    """
    Manages Context.md runtime state.
    
    State is stored in .agent-context/state.json and tracks:
    - Active worktrees (SubAgent isolation)
    - GitHub sync configuration
    - Mode settings
    
    Most other state is derived directly from Git:
    - Issues → Branches (issue-{N}-*)
    - Status → Git notes (refs/notes/context)
    - Audit → Commit history
    """
    
    SCHEMA_VERSION = "1.0"
    STATE_DIR = ".agent-context"
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
            "$schema": "https://context.md/schemas/state-v1.json",
            "version": self.SCHEMA_VERSION,
            "mode": "local",
            "worktrees": [],
            "github": {
                "enabled": False,
                "last_sync": None
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
    
    def update_github(self, enabled: Optional[bool] = None, last_sync: Optional[str] = None) -> None:
        """Update GitHub configuration."""
        if "github" not in self._data:
            self._data["github"] = {"enabled": False, "last_sync": None}
        if enabled is not None:
            self._data["github"]["enabled"] = enabled
        if last_sync is not None:
            self._data["github"]["last_sync"] = last_sync
    
    def is_initialized(self) -> bool:
        """Check if Context.md is initialized in this repository."""
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
