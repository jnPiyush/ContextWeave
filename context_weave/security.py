"""
Security Module - Runtime Command Validation

Implements defense-in-depth security model for AgentX:
- Level 1: Sandbox (OS-level isolation) - external
- Level 2: Filesystem (path restrictions) - implemented here
- Level 3: Allowlist (command validation) - implemented here
- Level 4: Audit (command logging) - implemented here

Design note: This module is integrated via the Agent Framework middleware
(framework/middleware.py and framework/tools.py), NOT the CLI commands.
CLI users have full terminal access and are trusted; this module guards
automated framework agents that run sandboxed.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when a security violation is detected."""


class CommandValidator:
    """Validates commands against allowlist before execution.

    Usage:
        validator = CommandValidator(repo_root)
        is_allowed, reason = validator.validate("git commit -m 'test'")
        if not is_allowed:
            raise SecurityError(reason)
    """

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize command validator.

        Args:
            repo_root: Repository root path. If None, uses current directory.
        """
        self.repo_root = repo_root or Path.cwd()
        self._load_allowlist()
        self._setup_audit_log()

    def _load_allowlist(self) -> None:
        """Load command allowlist from .github/security/allowed-commands.json"""
        allowlist_path = self.repo_root / ".github" / "security" / "allowed-commands.json"

        if allowlist_path.exists():
            try:
                with open(allowlist_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load allowlist: %s. Using defaults.", e)
                self.config = self._default_config()
        else:
            self.config = self._default_config()

        # Compile blocked patterns for efficiency
        self._blocked_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.get("blocked_patterns", [])
        ]

    def _default_config(self) -> dict:
        """Return default security configuration."""
        return {
            "allowed_commands": {
                "git": ["status", "add", "commit", "push", "pull", "fetch", "branch", "checkout", "log", "diff"],
                "dotnet": ["build", "test", "run", "restore", "publish"],
                "npm": ["install", "test", "run", "build"],
                "python": ["-m", "pip"],
                "pip": ["install", "list"],
                "pytest": [],
                "context-weave": []
            },
            "blocked_patterns": [
                "rm -rf /",
                "rm -rf /*",
                "del /s /q",
                "git reset --hard",
                "git push --force",
                "git push -f",
                "DROP DATABASE",
                "DROP TABLE",
                "TRUNCATE TABLE",
                "chmod 777",
                "curl.*\\|.*sh",
                "wget.*\\|.*bash"
            ],
            "blocked_commands": [
                "format",
                "fdisk",
                "mkfs"
            ]
        }

    def _setup_audit_log(self) -> None:
        """Setup audit logging."""
        self.audit_path = self.repo_root / ".github" / "security" / "audit.log"
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def validate(self, command: str, agent_role: str = "unknown") -> Tuple[bool, str]:
        """Validate a command against the security policy.

        Args:
            command: The command to validate
            agent_role: The role of the agent executing the command

        Returns:
            Tuple of (is_allowed, reason)
        """
        command = command.strip()

        # Check blocked patterns first
        for pattern in self._blocked_patterns:
            if pattern.search(command):
                reason = f"Blocked pattern detected: {pattern.pattern}"
                self._audit_log(command, agent_role, False, reason)
                return False, reason

        # Check blocked commands
        cmd_parts = command.split()
        if cmd_parts:
            base_cmd = cmd_parts[0].lower()
            if base_cmd in self.config.get("blocked_commands", []):
                reason = f"Command '{base_cmd}' is blocked"
                self._audit_log(command, agent_role, False, reason)
                return False, reason

        # Check if command is in allowlist
        allowed_commands = self.config.get("allowed_commands", {})
        if cmd_parts:
            base_cmd = cmd_parts[0].lower()

            # Check if base command is allowed
            if base_cmd in allowed_commands:
                allowed_subcommands = allowed_commands[base_cmd]

                # Empty list means all subcommands allowed
                if not allowed_subcommands:
                    self._audit_log(command, agent_role, True, "Allowed (all subcommands)")
                    return True, "Allowed"

                # Check if subcommand is allowed
                if len(cmd_parts) > 1:
                    subcommand = cmd_parts[1].lower()
                    if subcommand in allowed_subcommands:
                        self._audit_log(command, agent_role, True, "Allowed")
                        return True, "Allowed"
                    else:
                        reason = f"Subcommand '{subcommand}' not in allowlist for '{base_cmd}'"
                        self._audit_log(command, agent_role, False, reason)
                        return False, reason
                else:
                    self._audit_log(command, agent_role, True, "Allowed (base command)")
                    return True, "Allowed"

        # Default: allow commands not in blocklist (permissive mode)
        # In strict mode, change this to return False
        self._audit_log(command, agent_role, True, "Allowed (not in blocklist)")
        return True, "Allowed (not in blocklist)"

    def _audit_log(self, command: str, agent_role: str, allowed: bool, reason: str) -> None:
        """Log command execution to audit trail.

        Args:
            command: The command that was validated
            agent_role: The role executing the command
            allowed: Whether the command was allowed
            reason: Reason for the decision
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        status = "allowed" if allowed else "blocked"

        log_entry = f"[{timestamp}] [{agent_role}] [{command}] [{status}:{reason}]\n"

        try:
            with open(self.audit_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except IOError as e:
            logger.warning("Failed to write audit log: %s", e)

    def get_audit_log(self, limit: int = 100) -> List[str]:
        """Get recent audit log entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries (most recent first)
        """
        if not self.audit_path.exists():
            return []

        try:
            with open(self.audit_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            return lines[-limit:][::-1]  # Last N lines, reversed
        except IOError:
            return []


class PathValidator:
    """Validates file paths against security boundaries.

    Implements Level 2 (Filesystem) security - restricts operations
    to within the project directory.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize path validator.

        Args:
            repo_root: Repository root path. If None, uses current directory.
        """
        self.repo_root = (repo_root or Path.cwd()).resolve()

    def validate(self, path: str) -> Tuple[bool, str]:
        """Validate that a path is within the repository.

        Args:
            path: The path to validate

        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            resolved = Path(path).resolve()

            # Check if path is within repo root
            if self.repo_root in resolved.parents or resolved == self.repo_root:
                return True, "Path is within repository"

            # Also allow paths that start with repo_root
            try:
                resolved.relative_to(self.repo_root)
                return True, "Path is within repository"
            except ValueError:
                return False, f"Path '{path}' is outside repository root"

        except (ValueError, OSError) as e:
            return False, f"Invalid path: {e}"

    def sanitize(self, path: str) -> Optional[Path]:
        """Sanitize and resolve a path within the repository.

        Args:
            path: The path to sanitize

        Returns:
            Resolved Path if valid, None otherwise
        """
        is_valid, _ = self.validate(path)
        if is_valid:
            return Path(path).resolve()
        return None


def validate_command(command: str, repo_root: Optional[Path] = None,
                     agent_role: str = "unknown") -> Tuple[bool, str]:
    """Convenience function to validate a command.

    Args:
        command: The command to validate
        repo_root: Repository root path
        agent_role: The role of the agent

    Returns:
        Tuple of (is_allowed, reason)
    """
    validator = CommandValidator(repo_root)
    return validator.validate(command, agent_role)


def validate_path(path: str, repo_root: Optional[Path] = None) -> Tuple[bool, str]:
    """Convenience function to validate a path.

    Args:
        path: The path to validate
        repo_root: Repository root path

    Returns:
        Tuple of (is_valid, reason)
    """
    validator = PathValidator(repo_root)
    return validator.validate(path)
