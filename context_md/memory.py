"""
Memory Layer for Context.md

Implements persistent memory for AI agents including:
- Learning Memory: Success/failure patterns and lessons learned
- Session Memory: Cross-session context continuity
- Execution Memory: Track what was tried and outcomes

This is Layer 3 of the 4-Layer AI Context Architecture:
1. System Context - Role instructions, skills (governs behavior)
2. User Prompt - Issue details, requirements (what user asks)
3. Memory - This module (persistent info across sessions)
4. Retrieval Context - Knowledge grounding from skills/docs
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LessonLearned:
    """A lesson learned from execution outcomes."""

    id: str
    issue: int
    issue_type: str  # bug, story, feature, etc.
    role: str  # engineer, pm, architect, etc.
    category: str  # security, testing, api, performance, etc.
    lesson: str  # The actual lesson
    context: str  # What triggered this lesson
    outcome: str  # success, failure, partial
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    applied_count: int = 0  # How many times this lesson was applied
    effectiveness: float = 1.0  # 0.0-1.0, updated based on outcomes

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LessonLearned":
        return cls(**data)


@dataclass
class ExecutionRecord:
    """Record of an execution attempt."""

    issue: int
    role: str
    action: str  # what was attempted
    outcome: str  # success, failure, partial
    error_type: Optional[str] = None  # classification of error if failed
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    tokens_used: Optional[int] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionRecord":
        return cls(**data)


@dataclass
class SessionContext:
    """Context from a previous session for continuity."""

    issue: int
    session_id: str
    summary: str  # Brief summary of what was done
    progress: str  # Where we left off
    blockers: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionContext":
        return cls(**data)


class Memory:
    """
    Manages persistent memory for AI agents.

    Memory is stored in .agent-context/memory.json and includes:
    - Lessons learned from past executions
    - Execution history for pattern analysis
    - Session contexts for continuity
    - Success/failure metrics by category

    This enables the "learning loop" where agents improve over time.
    """

    MEMORY_FILE = "memory.json"
    MAX_LESSONS = 100  # Keep top 100 lessons by effectiveness
    MAX_EXECUTIONS = 500  # Rolling window of execution history
    MAX_SESSIONS_PER_ISSUE = 10  # Keep last 10 sessions per issue

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.memory_dir = repo_root / ".agent-context"
        self.memory_file = self.memory_dir / self.MEMORY_FILE
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load memory from file or create default."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load memory, starting fresh: %s", e)
                self._data = self._default_memory()
        else:
            self._data = self._default_memory()

    def _default_memory(self) -> Dict[str, Any]:
        """Create default memory structure."""
        return {
            "$schema": "https://context.md/schemas/memory-v1.json",
            "version": "1.0",
            "lessons": [],
            "executions": [],
            "sessions": {},  # keyed by issue number
            "metrics": {
                "total_executions": 0,
                "success_count": 0,
                "failure_count": 0,
                "partial_count": 0,
                "by_role": {},
                "by_category": {},
                "by_issue_type": {}
            }
        }

    def save(self) -> None:
        """Save memory to file."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    # ============ Lessons Learned ============

    def add_lesson(self, lesson: LessonLearned) -> None:
        """Add a new lesson learned."""
        lessons = self._data.get("lessons", [])

        # Check for similar existing lesson
        for existing in lessons:
            if (existing.get("category") == lesson.category and
                existing.get("lesson") == lesson.lesson):
                # Update existing lesson's applied count
                existing["applied_count"] = existing.get("applied_count", 0) + 1
                self.save()
                return

        lessons.append(lesson.to_dict())

        # Prune to MAX_LESSONS, keeping most effective
        if len(lessons) > self.MAX_LESSONS:
            lessons.sort(key=lambda x: x.get("effectiveness", 0) * x.get("applied_count", 1), reverse=True)
            self._data["lessons"] = lessons[:self.MAX_LESSONS]
        else:
            self._data["lessons"] = lessons

        self.save()

    def get_lessons_for_context(
        self,
        issue_type: Optional[str] = None,
        role: Optional[str] = None,
        categories: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[LessonLearned]:
        """Get relevant lessons for current context."""
        lessons = self._data.get("lessons", [])

        # Filter by context
        filtered = []
        for lesson_data in lessons:
            score = lesson_data.get("effectiveness", 1.0) * (lesson_data.get("applied_count", 0) + 1)

            # Boost score for matching context
            if issue_type and lesson_data.get("issue_type") == issue_type:
                score *= 1.5
            if role and lesson_data.get("role") == role:
                score *= 1.5
            if categories and lesson_data.get("category") in categories:
                score *= 2.0

            filtered.append((score, lesson_data))

        # Sort by score and return top lessons
        filtered.sort(key=lambda x: x[0], reverse=True)
        return [LessonLearned.from_dict(data) for _, data in filtered[:limit]]

    def update_lesson_effectiveness(self, lesson_id: str, outcome: str) -> None:
        """Update lesson effectiveness based on outcome when applied."""
        lessons = self._data.get("lessons", [])

        for lesson in lessons:
            if lesson.get("id") == lesson_id:
                current = lesson.get("effectiveness", 1.0)
                applied = lesson.get("applied_count", 0) + 1
                lesson["applied_count"] = applied

                # Adjust effectiveness based on outcome
                if outcome == "success":
                    # Increase effectiveness, weighted by history
                    lesson["effectiveness"] = min(1.0, current + (1.0 - current) * 0.1)
                elif outcome == "failure":
                    # Decrease effectiveness
                    lesson["effectiveness"] = max(0.1, current * 0.9)
                # partial keeps current effectiveness

                self.save()
                return

    # ============ Execution History ============

    def record_execution(self, record: ExecutionRecord) -> None:
        """Record an execution attempt."""
        executions = self._data.get("executions", [])
        executions.append(record.to_dict())

        # Keep rolling window
        if len(executions) > self.MAX_EXECUTIONS:
            self._data["executions"] = executions[-self.MAX_EXECUTIONS:]
        else:
            self._data["executions"] = executions

        # Update metrics
        self._update_metrics(record)
        self.save()

    def _update_metrics(self, record: ExecutionRecord) -> None:
        """Update aggregate metrics."""
        metrics = self._data.get("metrics", {})

        metrics["total_executions"] = metrics.get("total_executions", 0) + 1

        if record.outcome == "success":
            metrics["success_count"] = metrics.get("success_count", 0) + 1
        elif record.outcome == "failure":
            metrics["failure_count"] = metrics.get("failure_count", 0) + 1
        else:
            metrics["partial_count"] = metrics.get("partial_count", 0) + 1

        # By role
        by_role = metrics.get("by_role", {})
        role_stats = by_role.get(record.role, {"total": 0, "success": 0, "failure": 0})
        role_stats["total"] = role_stats.get("total", 0) + 1
        if record.outcome == "success":
            role_stats["success"] = role_stats.get("success", 0) + 1
        elif record.outcome == "failure":
            role_stats["failure"] = role_stats.get("failure", 0) + 1
        by_role[record.role] = role_stats
        metrics["by_role"] = by_role

        self._data["metrics"] = metrics

    def get_success_rate(self, role: Optional[str] = None) -> float:
        """Get overall or role-specific success rate."""
        metrics = self._data.get("metrics", {})

        if role:
            by_role = metrics.get("by_role", {})
            role_stats = by_role.get(role, {})
            total = role_stats.get("total", 0)
            success = role_stats.get("success", 0)
        else:
            total = metrics.get("total_executions", 0)
            success = metrics.get("success_count", 0)

        return success / total if total > 0 else 0.0

    def get_common_failures(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most common failure patterns."""
        executions = self._data.get("executions", [])

        # Count failures by error type
        failure_counts: Dict[str, int] = {}
        failure_examples: Dict[str, str] = {}

        for ex in executions:
            if ex.get("outcome") == "failure" and ex.get("error_type"):
                error_type = ex["error_type"]
                failure_counts[error_type] = failure_counts.get(error_type, 0) + 1
                if error_type not in failure_examples:
                    failure_examples[error_type] = ex.get("error_message", "No message")

        # Sort by count
        sorted_failures = sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)

        return [
            {"error_type": error_type, "count": count, "example": failure_examples.get(error_type)}
            for error_type, count in sorted_failures[:limit]
        ]

    # ============ Session Context ============

    def save_session(self, session: SessionContext) -> None:
        """Save session context for an issue."""
        sessions = self._data.get("sessions", {})
        issue_key = str(session.issue)

        if issue_key not in sessions:
            sessions[issue_key] = []

        sessions[issue_key].append(session.to_dict())

        # Keep only recent sessions
        if len(sessions[issue_key]) > self.MAX_SESSIONS_PER_ISSUE:
            sessions[issue_key] = sessions[issue_key][-self.MAX_SESSIONS_PER_ISSUE:]

        self._data["sessions"] = sessions
        self.save()

    def get_session_history(self, issue: int, limit: int = 5) -> List[SessionContext]:
        """Get session history for an issue."""
        sessions = self._data.get("sessions", {})
        issue_sessions = sessions.get(str(issue), [])

        return [SessionContext.from_dict(s) for s in issue_sessions[-limit:]]

    def get_latest_session(self, issue: int) -> Optional[SessionContext]:
        """Get the most recent session for an issue."""
        sessions = self.get_session_history(issue, limit=1)
        return sessions[0] if sessions else None

    # ============ Memory Summary for Context ============

    def get_memory_context(
        self,
        issue: int,
        issue_type: str,
        role: str,
        categories: List[str]
    ) -> str:
        """Generate memory context to include in generated context file."""
        sections = []

        # Previous session context
        latest_session = self.get_latest_session(issue)
        if latest_session:
            sections.append(f"""### Previous Session
**Last Active**: {latest_session.timestamp}
**Progress**: {latest_session.progress}
**Summary**: {latest_session.summary}
""")
            if latest_session.blockers:
                sections.append("**Blockers**:\n" + "\n".join(f"- {b}" for b in latest_session.blockers))
            if latest_session.next_steps:
                sections.append("**Next Steps**:\n" + "\n".join(f"- {s}" for s in latest_session.next_steps))

        # Relevant lessons
        lessons = self.get_lessons_for_context(issue_type, role, categories, limit=5)
        if lessons:
            lesson_text = ["### Lessons Learned"]
            for lesson in lessons:
                lesson_text.append(
                    f"- **[{lesson.category}]** {lesson.lesson} "
                    f"_(applied {lesson.applied_count}x, {lesson.effectiveness:.0%} effective)_"
                )
            sections.append("\n".join(lesson_text))

        # Success rate
        success_rate = self.get_success_rate(role)
        if success_rate > 0:
            sections.append(f"\n### Performance\n- **{role.title()} Success Rate**: {success_rate:.1%}")

        # Common failures to avoid
        failures = self.get_common_failures(limit=3)
        if failures:
            failure_text = ["### Common Pitfalls to Avoid"]
            for f in failures:
                failure_text.append(f"- **{f['error_type']}** ({f['count']} occurrences)")
            sections.append("\n".join(failure_text))

        return "\n\n".join(sections) if sections else "_No memory context available yet._"

    def to_dict(self) -> Dict[str, Any]:
        """Export memory as dictionary."""
        return self._data.copy()

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self._data.get("metrics", {})
