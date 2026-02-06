"""
Git-backed Thread Store for Agent Framework integration.

Implements persistent conversation storage in .context-weave/threads/,
enabling session suspend/resume for agent conversations.

Thread files are JSON and can be tracked by Git for audit purposes.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, MutableMapping, Optional, Sequence

logger = logging.getLogger(__name__)


class ChatMessage:
    """Lightweight message representation for thread storage."""

    def __init__(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.role = role
        self.content = content
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.metadata:
            data["metadata"] = self.metadata
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        return cls(
            role=data.get("role", "unknown"),
            content=data.get("content", ""),
            metadata=data.get("metadata"),
        )


class GitThreadStore:
    """Git-native thread store for Agent Framework.

    Stores conversation threads as JSON files in:
        .context-weave/threads/thread-{issue}-{role}.json

    This enables:
    - Persistent conversation history across sessions
    - Git-trackable thread state
    - Integration with existing .context-weave directory
    """

    THREADS_DIR = "threads"

    def __init__(
        self,
        repo_root: Path,
        issue: int,
        role: str,
        thread_id: Optional[str] = None,
    ):
        self.repo_root = repo_root
        self.issue = issue
        self.role = role
        self.thread_id = thread_id or f"thread-{issue}-{role}"
        self.messages: List[ChatMessage] = []
        self._created_at: Optional[str] = None
        self._updated_at: Optional[str] = None
        self._load()

    def _threads_dir(self) -> Path:
        return self.repo_root / ".context-weave" / self.THREADS_DIR

    def _thread_file(self) -> Path:
        return self._threads_dir() / f"{self.thread_id}.json"

    def _load(self) -> None:
        """Load thread from JSON file if it exists."""
        thread_file = self._thread_file()
        if thread_file.exists():
            try:
                data = json.loads(thread_file.read_text(encoding="utf-8"))
                self.messages = [
                    ChatMessage.from_dict(m) for m in data.get("messages", [])
                ]
                self._created_at = data.get("created_at")
                self._updated_at = data.get("updated_at")
                logger.debug(
                    "Loaded thread %s with %d messages",
                    self.thread_id, len(self.messages)
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load thread %s: %s", self.thread_id, e)
                self.messages = []
        else:
            self._created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    async def list_messages(self) -> List[ChatMessage]:
        """Return all messages in chronological order."""
        return list(self.messages)

    async def add_messages(self, messages: Sequence[Any]) -> None:
        """Add messages and persist to disk."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        for msg in messages:
            if isinstance(msg, ChatMessage):
                self.messages.append(msg)
            elif isinstance(msg, dict):
                self.messages.append(ChatMessage.from_dict(msg))
            else:
                # Try to extract role/content from framework message objects
                role = getattr(msg, "role", "unknown")
                content = getattr(msg, "content", str(msg))
                if isinstance(content, list):
                    # Handle content blocks
                    content = " ".join(
                        block.get("text", str(block)) if isinstance(block, dict) else str(block)
                        for block in content
                    )
                self.messages.append(ChatMessage(role=str(role), content=str(content)))

        self._updated_at = now
        self._persist()

    async def serialize(self, **kwargs: Any) -> Dict[str, Any]:
        """Serialize thread state for persistence."""
        return {
            "thread_id": self.thread_id,
            "issue": self.issue,
            "role": self.role,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    async def deserialize(
        cls,
        serialized_store_state: MutableMapping[str, Any],
        repo_root: Optional[Path] = None,
        **kwargs: Any,
    ) -> "GitThreadStore":
        """Create store from serialized state."""
        if repo_root is None:
            raise ValueError("repo_root is required for GitThreadStore.deserialize()")

        store = cls(
            repo_root=repo_root,
            issue=serialized_store_state.get("issue", 0),
            role=serialized_store_state.get("role", "unknown"),
            thread_id=serialized_store_state.get("thread_id"),
        )
        store.messages = [
            ChatMessage.from_dict(m)
            for m in serialized_store_state.get("messages", [])
        ]
        store._created_at = serialized_store_state.get("created_at")
        store._updated_at = serialized_store_state.get("updated_at")
        return store

    async def update_from_state(
        self,
        serialized_store_state: MutableMapping[str, Any],
        **kwargs: Any,
    ) -> None:
        """Update from serialized state."""
        self.messages = [
            ChatMessage.from_dict(m)
            for m in serialized_store_state.get("messages", [])
        ]
        self._updated_at = serialized_store_state.get("updated_at")
        self._persist()

    def _persist(self) -> None:
        """Write current state to JSON file."""
        threads_dir = self._threads_dir()
        threads_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "thread_id": self.thread_id,
            "issue": self.issue,
            "role": self.role,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "message_count": len(self.messages),
            "messages": [m.to_dict() for m in self.messages],
        }

        thread_file = self._thread_file()
        thread_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("Persisted thread %s (%d messages)", self.thread_id, len(self.messages))

    @staticmethod
    def list_threads(repo_root: Path) -> List[Dict[str, Any]]:
        """List all stored threads."""
        threads_dir = repo_root / ".context-weave" / GitThreadStore.THREADS_DIR
        threads = []

        if not threads_dir.exists():
            return threads

        for tf in sorted(threads_dir.glob("thread-*.json")):
            try:
                data = json.loads(tf.read_text(encoding="utf-8"))
                threads.append({
                    "thread_id": data.get("thread_id", tf.stem),
                    "issue": data.get("issue"),
                    "role": data.get("role"),
                    "message_count": data.get("message_count", 0),
                    "updated_at": data.get("updated_at"),
                })
            except (json.JSONDecodeError, OSError):
                continue

        return threads

    @staticmethod
    def delete_thread(repo_root: Path, issue: int, role: str) -> bool:
        """Delete a thread file."""
        thread_file = (
            repo_root / ".context-weave" / GitThreadStore.THREADS_DIR
            / f"thread-{issue}-{role}.json"
        )
        if thread_file.exists():
            thread_file.unlink()
            return True
        return False

    @staticmethod
    def thread_exists(repo_root: Path, issue: int, role: str) -> bool:
        """Check if a thread exists for a given issue and role."""
        thread_file = (
            repo_root / ".context-weave" / GitThreadStore.THREADS_DIR
            / f"thread-{issue}-{role}.json"
        )
        return thread_file.exists()
