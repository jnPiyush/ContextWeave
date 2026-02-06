"""
Configuration Management for Context.md

Handles configuration settings for the Context.md system.
"""

import copy
import json
from pathlib import Path
from typing import Any, Dict


class Config:
    """
    Manages Context.md configuration.

    Configuration is stored in .agent-context/config.json and includes:
    - Mode settings
    - Skill routing rules
    - Validation thresholds
    - GitHub integration settings
    """

    CONFIG_FILE = "config.json"

    DEFAULT_CONFIG = {
        "version": "1.0",
        "mode": "local",
        "worktree_base": "../worktrees",
        "skill_routing": {
            "api": ["#09", "#04", "#02", "#11"],
            "database": ["#06", "#04", "#02"],
            "security": ["#04", "#10", "#02", "#13", "#15"],
            "frontend": ["#21", "#22", "#02", "#11"],
            "bug": ["#03", "#02", "#15"],
            "performance": ["#05", "#06", "#02", "#15"],
            "ai": ["#17", "#04"],
            "default": ["#02", "#04", "#11"]
        },
        "validation": {
            "stuck_threshold_hours": {
                "bug": 12,
                "story": 24,
                "feature": 48,
                "epic": 72
            },
            "required_fields": {
                "story": ["references", "acceptance_criteria"],
                "bug": ["steps_to_reproduce", "expected_behavior"],
                "feature": ["documentation", "acceptance_criteria"]
            }
        },
        "hooks": {
            "prepare_commit_msg": True,
            "pre_commit": True,
            "post_commit": True,
            "pre_push": True,
            "post_merge": True
        },
        "github": {
            "auto_sync": False,
            "create_pr_on_push": True,
            "sync_notes": True
        }
    }

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.config_dir = repo_root / ".agent-context"
        self.config_file = self.config_dir / self.CONFIG_FILE
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load configuration from file or use defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                # Use deep copy to avoid mutating DEFAULT_CONFIG
                self._data = copy.deepcopy(self.DEFAULT_CONFIG)
        else:
            # Use deep copy to avoid mutating DEFAULT_CONFIG
            self._data = copy.deepcopy(self.DEFAULT_CONFIG)

    def save(self) -> None:
        """Save configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation (e.g., 'validation.stuck_threshold_hours')."""
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation."""
        keys = key.split(".")
        target = self._data
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    @property
    def mode(self) -> str:
        """Get operating mode."""
        return self._data.get("mode", "local")

    @mode.setter
    def mode(self, value: str) -> None:
        """Set operating mode."""
        if value not in ("local", "github", "hybrid"):
            raise ValueError(f"Invalid mode: {value}")
        self._data["mode"] = value

    @property
    def worktree_base(self) -> str:
        """Get worktree base directory (relative to repo root)."""
        return self._data.get("worktree_base", "../worktrees")

    def get_worktree_path(self, issue: int) -> Path:
        """Get full worktree path for an issue."""
        base = self.repo_root / self.worktree_base
        return base / str(issue)

    def get_skills_for_labels(self, labels: list) -> list:
        """Get skill numbers for a set of labels."""
        routing = self._data.get("skill_routing", {})
        skills = set()

        for label in labels:
            label_lower = label.lower()
            if label_lower in routing:
                skills.update(routing[label_lower])

        # Add default skills if no specific matches
        if not skills:
            skills.update(routing.get("default", []))

        return sorted(skills)

    def get_stuck_threshold(self, issue_type: str) -> int:
        """Get stuck detection threshold in hours for an issue type."""
        thresholds = self._data.get("validation", {}).get("stuck_threshold_hours", {})
        return thresholds.get(issue_type, 24)  # Default 24 hours

    def get_required_fields(self, issue_type: str) -> list:
        """Get required fields for an issue type."""
        fields = self._data.get("validation", {}).get("required_fields", {})
        return fields.get(issue_type, [])

    def is_hook_enabled(self, hook_name: str) -> bool:
        """Check if a Git hook is enabled."""
        hooks = self._data.get("hooks", {})
        return hooks.get(hook_name, True)

    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return self._data.copy()
