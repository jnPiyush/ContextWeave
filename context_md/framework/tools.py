"""
Tool Registry for Agent Framework integration.

Wraps existing Context.md operations (subprocess calls, state management,
context generation) as async functions compatible with Agent Framework's
FunctionTool system.

Tools use Annotated types with Field descriptions for automatic
JSON schema generation by the framework.
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Role-to-tool mapping: which tools each role can access
ROLE_TOOLS: Dict[str, List[str]] = {
    "pm": [
        "git_status", "read_file", "search_code", "list_directory",
        "get_context", "get_memory_context", "record_execution",
        "update_issue_status",
    ],
    "architect": [
        "git_status", "read_file", "search_code", "list_directory",
        "get_context", "get_memory_context", "record_execution",
        "update_issue_status",
    ],
    "engineer": [
        "git_status", "read_file", "search_code", "list_directory",
        "run_command", "create_file", "get_context", "get_memory_context",
        "record_execution", "update_issue_status",
    ],
    "reviewer": [
        "git_status", "read_file", "search_code", "list_directory",
        "get_context", "get_memory_context", "record_execution",
        "update_issue_status",
    ],
    "ux": [
        "git_status", "read_file", "search_code", "list_directory",
        "create_file", "get_context", "get_memory_context",
        "record_execution", "update_issue_status",
    ],
}


def _run_subprocess(
    args: List[str],
    cwd: Path,
    timeout: int = 30,
) -> str:
    """Run a subprocess and return combined output."""
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.returncode != 0 and result.stderr:
            output += f"\nSTDERR: {result.stderr}"
        return output
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return f"Command not found: {args[0]}"


class ToolRegistry:
    """Registry of Context.md tools for Agent Framework agents.

    Wraps existing CLI operations as async functions compatible
    with the Agent Framework's FunctionTool system.
    """

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self._tools = self._build_tool_map()

    def _build_tool_map(self) -> Dict[str, Any]:
        """Build map of tool name -> bound tool function."""
        repo = self.repo_root

        async def git_status() -> str:
            """Get current git status of the working directory."""
            return await asyncio.to_thread(
                _run_subprocess, ["git", "status", "--porcelain"], repo
            )

        async def read_file(path: str) -> str:
            """Read a file from the repository. Path is relative to repo root."""
            from context_md.security import PathValidator

            validator = PathValidator(repo)
            full_path = repo / path
            is_valid, reason = validator.validate(str(full_path))
            if not is_valid:
                return f"Access denied: {reason}"

            try:
                return full_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                return f"File not found: {path}"
            except (OSError, UnicodeDecodeError) as e:
                return f"Error reading file: {e}"

        async def search_code(pattern: str, file_glob: str = "**/*") -> str:
            """Search for a pattern in the codebase using grep."""
            args = ["git", "grep", "-n", "--no-color", "-I", pattern]
            if file_glob != "**/*":
                args.extend(["--", file_glob])
            output = await asyncio.to_thread(
                _run_subprocess, args, repo, timeout=15
            )
            # Limit output size
            lines = output.split("\n")
            if len(lines) > 50:
                return "\n".join(lines[:50]) + f"\n... ({len(lines) - 50} more matches)"
            return output

        async def list_directory(path: str = ".") -> str:
            """List directory contents relative to repo root."""
            from context_md.security import PathValidator

            validator = PathValidator(repo)
            full_path = repo / path
            is_valid, reason = validator.validate(str(full_path))
            if not is_valid:
                return f"Access denied: {reason}"

            try:
                entries = sorted(full_path.iterdir())
                lines = []
                for entry in entries:
                    prefix = "d " if entry.is_dir() else "f "
                    lines.append(f"{prefix}{entry.name}")
                return "\n".join(lines) if lines else "(empty directory)"
            except FileNotFoundError:
                return f"Directory not found: {path}"
            except OSError as e:
                return f"Error listing directory: {e}"

        async def run_command(command: str, agent_role: str = "unknown") -> str:
            """Execute a command after security validation.

            Uses CommandValidator to validate before execution.
            """
            from context_md.security import CommandValidator

            validator = CommandValidator(repo)
            is_allowed, reason = validator.validate(command, agent_role)
            if not is_allowed:
                return f"Command blocked: {reason}"

            parts = command.split()
            return await asyncio.to_thread(
                _run_subprocess, parts, repo, timeout=60
            )

        async def create_file(path: str, content: str) -> str:
            """Create or overwrite a file. Path is relative to repo root."""
            from context_md.security import PathValidator

            validator = PathValidator(repo)
            full_path = repo / path
            is_valid, reason = validator.validate(str(full_path))
            if not is_valid:
                return f"Access denied: {reason}"

            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                return f"File created: {path}"
            except OSError as e:
                return f"Error creating file: {e}"

        async def get_context(issue: int) -> str:
            """Get or generate context for an issue."""
            context_path = repo / ".agent-context" / f"context-{issue}.md"
            if context_path.exists():
                try:
                    return context_path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as e:
                    return f"Error reading context: {e}"
            return f"No context file found for issue #{issue}. Generate with: context-md context generate {issue}"

        async def get_memory_context(
            issue: int, issue_type: str, role: str
        ) -> str:
            """Retrieve memory context (lessons, sessions) for an issue."""
            from context_md.memory import Memory

            memory = Memory(repo)
            categories = [issue_type]
            return memory.get_memory_context(issue, issue_type, role, categories)

        async def record_execution(
            issue: int,
            role: str,
            action: str,
            outcome: str,
            error_type: Optional[str] = None,
            error_message: Optional[str] = None,
        ) -> str:
            """Record an execution attempt in the memory layer."""
            from context_md.memory import ExecutionRecord, Memory

            memory = Memory(repo)
            record = ExecutionRecord(
                issue=issue,
                role=role,
                action=action,
                outcome=outcome,
                error_type=error_type,
                error_message=error_message,
            )
            memory.record_execution(record)
            return f"Recorded execution: {action} -> {outcome}"

        async def update_issue_status(issue: int, status: str) -> str:
            """Update issue status via git notes."""
            from context_md.state import State

            state = State(repo)
            branches = state.get_issue_branches()
            matching = [b for b in branches if b.startswith(f"issue-{issue}-")]
            if not matching:
                return f"No branch found for issue #{issue}"

            branch = matching[0]
            note = state.get_branch_note(branch) or {}
            note["status"] = status
            success = state.set_branch_note(branch, note)
            if success:
                return f"Status updated to '{status}' for issue #{issue}"
            return f"Failed to update status for issue #{issue}"

        return {
            "git_status": git_status,
            "read_file": read_file,
            "search_code": search_code,
            "list_directory": list_directory,
            "run_command": run_command,
            "create_file": create_file,
            "get_context": get_context,
            "get_memory_context": get_memory_context,
            "record_execution": record_execution,
            "update_issue_status": update_issue_status,
        }

    def get_all_tools(self) -> list:
        """Return all registered tools as a list of callables."""
        return list(self._tools.values())

    def get_tools_for_role(self, role: str) -> list:
        """Return tools appropriate for a specific agent role."""
        allowed_names = ROLE_TOOLS.get(role, ROLE_TOOLS.get("engineer", []))
        return [
            self._tools[name]
            for name in allowed_names
            if name in self._tools
        ]

    def get_tool_by_name(self, name: str) -> Optional[Any]:
        """Get a specific tool by name."""
        return self._tools.get(name)
