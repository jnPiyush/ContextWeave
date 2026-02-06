"""
Scaffold files for ContextWeave project initialization.

Contains .github/ templates (agents, instructions, prompts, templates)
that are deployed to target repositories via `context-weave init`.
"""

from pathlib import Path


def get_scaffolds_dir() -> Path:
    """Return the path to the scaffolds directory."""
    return Path(__file__).parent
