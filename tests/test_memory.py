"""
Tests for Memory Module (Layer 3: Persistent Knowledge)

Coverage target: 80%+
"""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner

from context_md.memory import (
    ExecutionRecord,
    LessonLearned,
    Memory,
    SessionContext,
)
from context_md.commands.memory import memory_cmd


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def memory_with_data(tmp_path):
    """Create a memory instance with sample data."""
    memory = Memory(tmp_path)
    
    # Add some lessons
    lesson1 = LessonLearned(
        id="abc123",
        issue=100,
        issue_type="bug",
        role="engineer",
        category="security",
        lesson="Always validate user input before processing",
        context="SQL injection vulnerability found in production",
        outcome="failure"
    )
    memory.add_lesson(lesson1)
    
    lesson2 = LessonLearned(
        id="def456",
        issue=101,
        issue_type="story",
        role="engineer",
        category="testing",
        lesson="Write tests before implementing features",
        context="TDD approach improved code quality",
        outcome="success"
    )
    memory.add_lesson(lesson2)
    
    # Add some executions
    for outcome in ["success", "success", "failure"]:
        record = ExecutionRecord(
            issue=100,
            role="engineer",
            action="implement feature",
            outcome=outcome,
            error_type="test_failure" if outcome == "failure" else None
        )
        memory.record_execution(record)
    
    # Add a session
    session = SessionContext(
        issue=100,
        session_id="sess123",
        summary="Implemented authentication module",
        progress="Completed login flow, starting on logout",
        blockers=["Need API key for OAuth"],
        next_steps=["Implement logout", "Add tests"],
        files_modified=["src/auth.py", "tests/test_auth.py"]
    )
    memory.save_session(session)
    
    return memory


class TestLessonLearned:
    """Test LessonLearned dataclass."""
    
    def test_create_lesson(self):
        """Test creating a lesson."""
        lesson = LessonLearned(
            id="test123",
            issue=42,
            issue_type="bug",
            role="engineer",
            category="security",
            lesson="Test lesson",
            context="Test context",
            outcome="success"
        )
        
        assert lesson.id == "test123"
        assert lesson.issue == 42
        assert lesson.effectiveness == 1.0
        assert lesson.applied_count == 0
    
    def test_lesson_to_dict(self):
        """Test serialization to dict."""
        lesson = LessonLearned(
            id="test123",
            issue=42,
            issue_type="bug",
            role="engineer",
            category="security",
            lesson="Test lesson",
            context="Test context",
            outcome="success"
        )
        
        data = lesson.to_dict()
        assert data["id"] == "test123"
        assert data["effectiveness"] == 1.0
    
    def test_lesson_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "id": "test123",
            "issue": 42,
            "issue_type": "bug",
            "role": "engineer",
            "category": "security",
            "lesson": "Test lesson",
            "context": "Test context",
            "outcome": "success",
            "created_at": "2026-01-30T00:00:00Z",
            "applied_count": 5,
            "effectiveness": 0.8
        }
        
        lesson = LessonLearned.from_dict(data)
        assert lesson.applied_count == 5
        assert lesson.effectiveness == 0.8


class TestExecutionRecord:
    """Test ExecutionRecord dataclass."""
    
    def test_create_execution(self):
        """Test creating an execution record."""
        record = ExecutionRecord(
            issue=100,
            role="engineer",
            action="implement feature",
            outcome="success"
        )
        
        assert record.issue == 100
        assert record.error_type is None
    
    def test_execution_with_error(self):
        """Test execution with error details."""
        record = ExecutionRecord(
            issue=100,
            role="engineer",
            action="run tests",
            outcome="failure",
            error_type="test_failure",
            error_message="3 tests failed"
        )
        
        assert record.error_type == "test_failure"
        assert record.error_message == "3 tests failed"


class TestSessionContext:
    """Test SessionContext dataclass."""
    
    def test_create_session(self):
        """Test creating a session context."""
        session = SessionContext(
            issue=100,
            session_id="sess123",
            summary="Worked on auth",
            progress="50% complete"
        )
        
        assert session.issue == 100
        assert session.blockers == []
        assert session.next_steps == []
    
    def test_session_with_details(self):
        """Test session with full details."""
        session = SessionContext(
            issue=100,
            session_id="sess123",
            summary="Worked on auth",
            progress="50% complete",
            blockers=["Need API key"],
            next_steps=["Finish login"],
            files_modified=["auth.py"]
        )
        
        assert len(session.blockers) == 1
        assert len(session.next_steps) == 1
        assert len(session.files_modified) == 1


class TestMemoryClass:
    """Test Memory class directly."""
    
    def test_default_memory(self, tmp_path):
        """Test default memory initialization."""
        memory = Memory(tmp_path)
        
        assert memory.metrics.get("total_executions", 0) == 0
        assert len(memory._data.get("lessons", [])) == 0
    
    def test_save_and_load(self, tmp_path):
        """Test memory persistence."""
        memory = Memory(tmp_path)
        
        lesson = LessonLearned(
            id="test123",
            issue=42,
            issue_type="bug",
            role="engineer",
            category="security",
            lesson="Test lesson",
            context="Test context",
            outcome="success"
        )
        memory.add_lesson(lesson)
        
        # Load fresh instance
        memory2 = Memory(tmp_path)
        lessons = memory2._data.get("lessons", [])
        assert len(lessons) == 1
        assert lessons[0]["id"] == "test123"
    
    def test_add_lesson(self, tmp_path):
        """Test adding lessons."""
        memory = Memory(tmp_path)
        
        lesson = LessonLearned(
            id="test123",
            issue=42,
            issue_type="bug",
            role="engineer",
            category="security",
            lesson="Test lesson",
            context="Test context",
            outcome="success"
        )
        memory.add_lesson(lesson)
        
        lessons = memory._data.get("lessons", [])
        assert len(lessons) == 1
    
    def test_duplicate_lesson_updates_count(self, tmp_path):
        """Test that duplicate lessons update applied count."""
        memory = Memory(tmp_path)
        
        for _ in range(3):
            lesson = LessonLearned(
                id=f"test{_}",  # Different IDs
                issue=42,
                issue_type="bug",
                role="engineer",
                category="security",
                lesson="Same lesson text",  # Same lesson content
                context="Test context",
                outcome="success"
            )
            memory.add_lesson(lesson)
        
        # Should only have 1 lesson with applied_count increased
        lessons = memory._data.get("lessons", [])
        assert len(lessons) == 1
        assert lessons[0]["applied_count"] == 2  # Incremented twice after first add
    
    def test_get_lessons_for_context(self, memory_with_data):
        """Test getting relevant lessons."""
        lessons = memory_with_data.get_lessons_for_context(
            issue_type="bug",
            role="engineer",
            categories=["security"],
            limit=5
        )
        
        assert len(lessons) >= 1
        # Security lesson should be boosted for bug/engineer/security context
        security_lessons = [l for l in lessons if l.category == "security"]
        assert len(security_lessons) >= 1
    
    def test_record_execution(self, tmp_path):
        """Test recording executions."""
        memory = Memory(tmp_path)
        
        record = ExecutionRecord(
            issue=100,
            role="engineer",
            action="test action",
            outcome="success"
        )
        memory.record_execution(record)
        
        assert memory.metrics["total_executions"] == 1
        assert memory.metrics["success_count"] == 1
    
    def test_get_success_rate(self, memory_with_data):
        """Test success rate calculation."""
        # From fixture: 2 success, 1 failure
        rate = memory_with_data.get_success_rate()
        assert rate == pytest.approx(2/3, rel=0.01)
    
    def test_get_success_rate_by_role(self, memory_with_data):
        """Test role-specific success rate."""
        rate = memory_with_data.get_success_rate(role="engineer")
        assert rate == pytest.approx(2/3, rel=0.01)
    
    def test_get_common_failures(self, memory_with_data):
        """Test getting common failures."""
        failures = memory_with_data.get_common_failures(limit=5)
        
        assert len(failures) >= 1
        assert failures[0]["error_type"] == "test_failure"
        assert failures[0]["count"] >= 1
    
    def test_save_session(self, tmp_path):
        """Test saving session context."""
        memory = Memory(tmp_path)
        
        session = SessionContext(
            issue=100,
            session_id="sess123",
            summary="Test summary",
            progress="Test progress"
        )
        memory.save_session(session)
        
        sessions = memory._data.get("sessions", {})
        assert "100" in sessions
        assert len(sessions["100"]) == 1
    
    def test_get_session_history(self, memory_with_data):
        """Test getting session history."""
        history = memory_with_data.get_session_history(100)
        
        assert len(history) >= 1
        assert history[0].summary == "Implemented authentication module"
    
    def test_get_latest_session(self, memory_with_data):
        """Test getting latest session."""
        session = memory_with_data.get_latest_session(100)
        
        assert session is not None
        assert session.issue == 100
    
    def test_get_memory_context(self, memory_with_data):
        """Test generating memory context for inclusion."""
        context = memory_with_data.get_memory_context(
            issue=100,
            issue_type="bug",
            role="engineer",
            categories=["security"]
        )
        
        assert "Previous Session" in context or "Lessons Learned" in context
        assert len(context) > 0
    
    def test_lesson_effectiveness_update(self, tmp_path):
        """Test updating lesson effectiveness."""
        memory = Memory(tmp_path)
        
        lesson = LessonLearned(
            id="eff123",
            issue=42,
            issue_type="bug",
            role="engineer",
            category="testing",
            lesson="Test effectiveness",
            context="Test context",
            outcome="success",
            effectiveness=0.5
        )
        memory.add_lesson(lesson)
        
        # Update on success
        memory.update_lesson_effectiveness("eff123", "success")
        lessons = memory._data.get("lessons", [])
        updated = [l for l in lessons if l["id"] == "eff123"][0]
        assert updated["effectiveness"] > 0.5
    
    def test_corrupted_memory_recovery(self, tmp_path):
        """Test recovery from corrupted memory file."""
        memory_dir = tmp_path / ".agent-context"
        memory_dir.mkdir(parents=True, exist_ok=True)
        memory_file = memory_dir / "memory.json"
        memory_file.write_text("{ invalid json }")
        
        # Should fall back to defaults
        memory = Memory(tmp_path)
        assert memory.metrics.get("total_executions", 0) == 0


class TestMemoryShowCommand:
    """Test memory show command."""
    
    def test_show_empty_memory(self, runner, tmp_path):
        """Test showing empty memory."""
        memory = Memory(tmp_path)
        memory.save()
        
        result = runner.invoke(
            memory_cmd,
            ["show"],
            obj={"repo_root": tmp_path},
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "MEMORY SUMMARY" in result.output
    
    def test_show_memory_json(self, runner, tmp_path):
        """Test JSON output format."""
        memory = Memory(tmp_path)
        memory.save()
        
        result = runner.invoke(
            memory_cmd,
            ["show", "--json"],
            obj={"repo_root": tmp_path},
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "metrics" in data


class TestLessonsCommand:
    """Test lessons subcommands."""
    
    def test_lessons_list_empty(self, runner, tmp_path):
        """Test listing empty lessons."""
        memory = Memory(tmp_path)
        memory.save()
        
        result = runner.invoke(
            memory_cmd,
            ["lessons", "list"],
            obj={"repo_root": tmp_path},
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "No lessons" in result.output
    
    def test_lessons_add(self, runner, tmp_path):
        """Test adding a lesson."""
        memory = Memory(tmp_path)
        memory.save()
        
        result = runner.invoke(
            memory_cmd,
            [
                "lessons", "add",
                "--issue", "100",
                "--category", "security",
                "--lesson", "Always sanitize input",
                "--context", "Found XSS vulnerability",
                "--outcome", "failure"
            ],
            obj={"repo_root": tmp_path},
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "OK" in result.output
        
        # Verify it was saved
        memory2 = Memory(tmp_path)
        assert len(memory2._data.get("lessons", [])) == 1


class TestRecordCommand:
    """Test record execution command."""
    
    def test_record_success(self, runner, tmp_path):
        """Test recording successful execution."""
        memory = Memory(tmp_path)
        memory.save()
        
        result = runner.invoke(
            memory_cmd,
            [
                "record", "100",
                "--role", "engineer",
                "--action", "implement feature",
                "--outcome", "success"
            ],
            obj={"repo_root": tmp_path},
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "success" in result.output.lower()
    
    def test_record_failure_with_error(self, runner, tmp_path):
        """Test recording failed execution with error details."""
        memory = Memory(tmp_path)
        memory.save()
        
        result = runner.invoke(
            memory_cmd,
            [
                "record", "100",
                "--role", "engineer",
                "--action", "run tests",
                "--outcome", "failure",
                "--error-type", "test_failure",
                "--error-message", "3 tests failed"
            ],
            obj={"repo_root": tmp_path},
            catch_exceptions=False
        )
        
        assert result.exit_code == 0


class TestMetricsCommand:
    """Test metrics command."""
    
    def test_metrics_empty(self, runner, tmp_path):
        """Test showing metrics with no data."""
        memory = Memory(tmp_path)
        memory.save()
        
        result = runner.invoke(
            memory_cmd,
            ["metrics"],
            obj={"repo_root": tmp_path},
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "Success Metrics" in result.output


class TestSessionCommand:
    """Test session subcommands."""
    
    def test_session_save(self, runner, tmp_path):
        """Test saving session context."""
        memory = Memory(tmp_path)
        memory.save()
        
        result = runner.invoke(
            memory_cmd,
            [
                "session", "save", "100",
                "--summary", "Worked on auth module",
                "--progress", "50% complete",
                "--blocker", "Need API key",
                "--next", "Finish login flow"
            ],
            obj={"repo_root": tmp_path},
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "OK" in result.output
    
    def test_session_show_empty(self, runner, tmp_path):
        """Test showing nonexistent session."""
        memory = Memory(tmp_path)
        memory.save()
        
        result = runner.invoke(
            memory_cmd,
            ["session", "show", "999"],
            obj={"repo_root": tmp_path},
            catch_exceptions=False
        )
        
        assert result.exit_code == 0
        assert "No session" in result.output
