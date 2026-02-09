"""
ContextWeave - Runtime Context Management for AI Agents

A Git-native tool for managing AI agent context, isolation, and quality gates.
Achieves >95% success rate in production code generation through:
- Git worktree-based SubAgent isolation
- Hook-based automation (no polling)
- Mode selection (Local/GitHub/Hybrid)
- Full traceability via Git's immutable history
"""

__version__ = "2.0.0"
__author__ = "ContextWeave Team"

from context_weave.config import Config
from context_weave.state import State

__all__ = ["State", "Config", "__version__"]
