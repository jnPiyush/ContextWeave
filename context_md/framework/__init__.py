"""
Microsoft Agent Framework integration for Context.md.

This package is optional. It requires:
    pip install agent-framework --pre

Or install with the agent extra:
    pip install context-md[agent]

When the framework is not installed, AGENT_FRAMEWORK_AVAILABLE is False
and the 'run' CLI command is not registered.
"""

AGENT_FRAMEWORK_AVAILABLE: bool

try:
    import agent_framework  # noqa: F401
    AGENT_FRAMEWORK_AVAILABLE = True
except ImportError:
    AGENT_FRAMEWORK_AVAILABLE = False

__all__ = ["AGENT_FRAMEWORK_AVAILABLE"]
