"""
Context.md - Runtime Context Management for AI Agents

A Git-native tool for managing AI agent context, isolation, and quality gates.
Achieves >95% success rate in production code generation through:
- Git worktree-based SubAgent isolation
- Hook-based automation (no polling)
- Mode selection (Local/GitHub/Hybrid)
- Full traceability via Git's immutable history
"""

__version__ = "0.1.0"
__author__ = "Context.md Team"

from context_md.state import State
from context_md.config import Config

__all__ = ["State", "Config", "__version__"]
