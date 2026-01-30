#!/usr/bin/env python3
"""
Prompt Enhancement Demonstration

This script shows the before/after transformation of user prompts
using the PromptEngineer class from Context.md.

Repository: https://github.com/jnPiyush/ContextMD
"""

from context_md.prompt import PromptEngineer, EnhancedPrompt

# ============================================================================
# EXAMPLE 1: Simple Bug Fix
# ============================================================================

print("=" * 80)
print("EXAMPLE 1: Simple Bug Fix (Engineer Role)")
print("=" * 80)

# Before: Raw prompt from GitHub Issue
raw_bug_prompt = """
Login page returns 500 error when user enters special characters in email field.
Steps to reproduce:
1. Go to /login
2. Enter 'test@example.com<script>' in email
3. Click submit
4. Page crashes with 500 error
"""

print("\n📝 BEFORE (Raw Issue Description):")
print("-" * 40)
print(raw_bug_prompt)

# After: Enhanced with prompt engineering
engineer = PromptEngineer()
enhanced = engineer.enhance_prompt(
    raw_prompt=raw_bug_prompt,
    role="engineer",
    issue_number=42,
    issue_type="bug",
    labels=["type:bug", "security", "priority:p0"],
    context={
        "previous_session": "Initial investigation found XSS vulnerability",
        "dependencies": ["#30 - Auth module refactor"]
    }
)

print("\n✨ AFTER (Enhanced Prompt):")
print("-" * 40)
print(enhanced.to_markdown())

# Validation
validation = engineer.validate_prompt_completeness(enhanced)
print(f"\n📊 Quality Score: {validation['completeness_score']:.0%}")
if validation['warnings']:
    print("⚠️  Warnings:", ", ".join(validation['warnings']))


# ============================================================================
# EXAMPLE 2: Feature Request (Architect Role)
# ============================================================================

print("\n" + "=" * 80)
print("EXAMPLE 2: Feature Request (Architect Role)")
print("=" * 80)

raw_feature_prompt = """
Add OAuth2 support for third-party login.
Should support Google, GitHub, and Microsoft providers.
"""

print("\n📝 BEFORE (Raw Issue Description):")
print("-" * 40)
print(raw_feature_prompt)

enhanced_arch = engineer.enhance_prompt(
    raw_prompt=raw_feature_prompt,
    role="architect",
    issue_number=100,
    issue_type="feature",
    labels=["type:feature", "api", "security"],
    context={
        "prd_path": "docs/prd/PRD-100.md",
        "dependencies": ["#98 - User service", "#99 - Session management"]
    }
)

print("\n✨ AFTER (Enhanced Prompt):")
print("-" * 40)
print(enhanced_arch.to_markdown())


# ============================================================================
# EXAMPLE 3: Epic Definition (PM Role)
# ============================================================================

print("\n" + "=" * 80)
print("EXAMPLE 3: Epic Definition (Product Manager Role)")  
print("=" * 80)

raw_epic_prompt = """
Build a comprehensive user authentication system.
"""

print("\n📝 BEFORE (Raw Issue Description):")
print("-" * 40)
print(raw_epic_prompt)

enhanced_pm = engineer.enhance_prompt(
    raw_prompt=raw_epic_prompt,
    role="pm",
    issue_number=200,
    issue_type="epic",
    labels=["type:epic"]
)

print("\n✨ AFTER (Enhanced Prompt):")
print("-" * 40)
print(enhanced_pm.to_markdown())


# ============================================================================
# EXAMPLE 4: Chain-of-Thought Prompting
# ============================================================================

print("\n" + "=" * 80)
print("EXAMPLE 4: Chain-of-Thought Prompt")
print("=" * 80)

cot_prompt = engineer.get_chain_of_thought_prompt(
    role="engineer",
    task="Implement rate limiting for API endpoints"
)

print("\n🧠 Chain-of-Thought Prompt:")
print("-" * 40)
print(cot_prompt)


# ============================================================================
# EXAMPLE 5: Comparison Table
# ============================================================================

print("\n" + "=" * 80)
print("SUMMARY: Raw vs Enhanced Prompts")
print("=" * 80)

print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RAW PROMPT vs ENHANCED PROMPT                         │
├───────────────────────────────┬─────────────────────────────────────────────┤
│ Raw Prompt                    │ Enhanced Prompt                             │
├───────────────────────────────┼─────────────────────────────────────────────┤
│ ❌ No clear role definition   │ ✅ Role primer sets agent expertise         │
│ ❌ Vague task description     │ ✅ Specific task with issue reference       │
│ ❌ Missing context            │ ✅ Dependencies, specs, history included    │
│ ❌ Unclear expectations       │ ✅ Defined inputs and outputs               │
│ ❌ No boundaries              │ ✅ Explicit constraints                     │
│ ❌ No success criteria        │ ✅ Measurable success criteria              │
│ ❌ No guidance                │ ✅ Approach hints and pitfalls              │
│ ❌ No workflow awareness      │ ✅ Handoff requirements for next role       │
├───────────────────────────────┴─────────────────────────────────────────────┤
│ Result: Higher quality, more consistent agent outputs                       │
└─────────────────────────────────────────────────────────────────────────────┘
""")

print("\n✅ Demo complete! See https://github.com/jnPiyush/ContextMD for full documentation.")
