"""Tests for context_md.framework.thread_store -- Git Thread Store."""

import json

import pytest

from context_md.framework.thread_store import ChatMessage, GitThreadStore


class TestChatMessage:
    def test_create(self):
        msg = ChatMessage("user", "Hello world")
        assert msg.role == "user"
        assert msg.content == "Hello world"
        assert msg.metadata == {}

    def test_to_dict(self):
        msg = ChatMessage("assistant", "Response", metadata={"tool": "test"})
        data = msg.to_dict()
        assert data["role"] == "assistant"
        assert data["content"] == "Response"
        assert data["metadata"]["tool"] == "test"

    def test_from_dict(self):
        data = {"role": "user", "content": "Hello"}
        msg = ChatMessage.from_dict(data)
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_roundtrip(self):
        original = ChatMessage("system", "Instructions", {"key": "val"})
        restored = ChatMessage.from_dict(original.to_dict())
        assert restored.role == original.role
        assert restored.content == original.content
        assert restored.metadata == original.metadata


class TestGitThreadStore:
    def test_create_new_thread(self, tmp_path):
        store = GitThreadStore(tmp_path, issue=42, role="engineer")
        assert store.thread_id == "thread-42-engineer"
        assert store.messages == []
        assert store.issue == 42
        assert store.role == "engineer"

    def test_custom_thread_id(self, tmp_path):
        store = GitThreadStore(tmp_path, issue=1, role="pm", thread_id="custom-thread")
        assert store.thread_id == "custom-thread"

    @pytest.mark.asyncio
    async def test_add_and_list_messages(self, tmp_path):
        store = GitThreadStore(tmp_path, issue=1, role="engineer")

        await store.add_messages([
            ChatMessage("user", "Hello"),
            ChatMessage("assistant", "Hi there"),
        ])

        messages = await store.list_messages()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].content == "Hi there"

    @pytest.mark.asyncio
    async def test_add_messages_dict(self, tmp_path):
        store = GitThreadStore(tmp_path, issue=1, role="engineer")

        await store.add_messages([
            {"role": "user", "content": "Test message"},
        ])

        messages = await store.list_messages()
        assert len(messages) == 1
        assert messages[0].content == "Test message"

    @pytest.mark.asyncio
    async def test_persistence(self, tmp_path):
        # Create and populate a thread
        store1 = GitThreadStore(tmp_path, issue=5, role="architect")
        await store1.add_messages([
            ChatMessage("user", "Design the system"),
            ChatMessage("assistant", "Here is the design..."),
        ])

        # Load the same thread fresh
        store2 = GitThreadStore(tmp_path, issue=5, role="architect")
        messages = await store2.list_messages()
        assert len(messages) == 2
        assert messages[0].content == "Design the system"
        assert messages[1].content == "Here is the design..."

    @pytest.mark.asyncio
    async def test_thread_file_location(self, tmp_path):
        store = GitThreadStore(tmp_path, issue=10, role="reviewer")
        await store.add_messages([ChatMessage("user", "test")])

        expected_file = tmp_path / ".agent-context" / "threads" / "thread-10-reviewer.json"
        assert expected_file.exists()

        data = json.loads(expected_file.read_text())
        assert data["thread_id"] == "thread-10-reviewer"
        assert data["issue"] == 10
        assert data["role"] == "reviewer"
        assert data["message_count"] == 1

    @pytest.mark.asyncio
    async def test_serialize(self, tmp_path):
        store = GitThreadStore(tmp_path, issue=1, role="pm")
        await store.add_messages([ChatMessage("user", "Hello")])

        data = await store.serialize()
        assert data["thread_id"] == "thread-1-pm"
        assert data["issue"] == 1
        assert len(data["messages"]) == 1

    @pytest.mark.asyncio
    async def test_deserialize(self, tmp_path):
        serialized = {
            "thread_id": "thread-99-engineer",
            "issue": 99,
            "role": "engineer",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T01:00:00Z",
            "messages": [
                {"role": "user", "content": "Fix bug"},
                {"role": "assistant", "content": "Fixed!"},
            ],
        }
        store = await GitThreadStore.deserialize(serialized, repo_root=tmp_path)
        assert store.thread_id == "thread-99-engineer"
        assert len(store.messages) == 2

    @pytest.mark.asyncio
    async def test_deserialize_no_repo_root(self):
        with pytest.raises(ValueError, match="repo_root"):
            await GitThreadStore.deserialize({})


class TestGitThreadStoreStaticMethods:
    @pytest.mark.asyncio
    async def test_list_threads(self, tmp_path):
        # Create threads
        store1 = GitThreadStore(tmp_path, issue=1, role="engineer")
        await store1.add_messages([ChatMessage("user", "msg1")])

        store2 = GitThreadStore(tmp_path, issue=2, role="reviewer")
        await store2.add_messages([ChatMessage("user", "msg2")])

        threads = GitThreadStore.list_threads(tmp_path)
        assert len(threads) == 2
        issues = [t["issue"] for t in threads]
        assert 1 in issues
        assert 2 in issues

    def test_list_threads_empty(self, tmp_path):
        threads = GitThreadStore.list_threads(tmp_path)
        assert threads == []

    @pytest.mark.asyncio
    async def test_delete_thread(self, tmp_path):
        store = GitThreadStore(tmp_path, issue=1, role="engineer")
        await store.add_messages([ChatMessage("user", "test")])

        assert GitThreadStore.thread_exists(tmp_path, 1, "engineer")
        deleted = GitThreadStore.delete_thread(tmp_path, 1, "engineer")
        assert deleted
        assert not GitThreadStore.thread_exists(tmp_path, 1, "engineer")

    def test_delete_nonexistent_thread(self, tmp_path):
        deleted = GitThreadStore.delete_thread(tmp_path, 999, "unknown")
        assert not deleted

    @pytest.mark.asyncio
    async def test_thread_exists(self, tmp_path):
        assert not GitThreadStore.thread_exists(tmp_path, 1, "engineer")

        store = GitThreadStore(tmp_path, issue=1, role="engineer")
        await store.add_messages([ChatMessage("user", "test")])

        assert GitThreadStore.thread_exists(tmp_path, 1, "engineer")
