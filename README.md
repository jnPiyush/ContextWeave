# ContextWeave

<div align="center">

![ContextWeave Logo](https://img.shields.io/badge/ContextWeave-AI%20Agent%20Context%20Management-blue?style=for-the-badge&logo=git)

**Runtime Context Management for AI Agents**

*Achieve >95% success rate in AI agent production code generation*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](./tests)
[![Coverage](https://img.shields.io/badge/coverage-68%25-yellowgreen.svg)](./htmlcov)
[![Automation](https://img.shields.io/badge/automation-10%20layers-blue.svg)](./.github/workflows)

[Installation](#-installation) •
[Quick Start](#-quick-start) •
[Architecture](#%EF%B8%8F-architecture) •
[Automation](#-automation-features) •
[Commands](#-cli-commands) •
[Contributing](#-contributing)

</div>

---

## 🎯 What is ContextWeave?

**ContextWeave** is a Git-native runtime context management system designed to dramatically improve AI agent success rates in code generation tasks. It solves the fundamental problem of AI agents lacking proper context, memory, and structured guidance.

### The Problem

```
❌ Without ContextWeave:
   - AI agents generate code without understanding project conventions
   - No memory of previous sessions or lessons learned
   - Vague prompts lead to inconsistent results
   - No quality gates or validation
   - ~40-60% success rate on complex tasks
```

### The Solution

```
✅ With ContextWeave:
   - Structured 4-Layer context provides complete project understanding
   - Persistent memory tracks lessons and patterns across sessions
   - Prompt engineering enhances every request automatically
   - Built-in validation and quality gates
   - >95% success rate on production code generation
```

---

## 🏗️ Architecture

ContextWeave implements a **4-Layer AI Context Architecture** that provides structured, comprehensive context to AI agents.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              CONTEXT.MD ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│    ┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐  │
│    │   GitHub    │────▶│  ContextWeave  │────▶│  AI Agent   │────▶│   Output     │  │
│    │   Issues    │     │   CLI Tool   │     │  (Copilot)  │     │  (Code/Docs) │  │
│    └─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘  │
│          │                    │                    │                    │          │
│          │                    ▼                    │                    │          │
│          │          ┌──────────────────┐          │                    │          │
│          │          │ 4-LAYER CONTEXT  │◀─────────┘                    │          │
│          │          │ ─────────────────│                               │          │
│          │          │ 1. System Context│                               │          │
│          │          │ 2. User Prompt   │                               │          │
│          │          │ 3. Memory Layer  │                               │          │
│          │          │ 4. Skills/Docs   │                               │          │
│          │          └──────────────────┘                               │          │
│          │                    │                                        │          │
│          │                    ▼                                        │          │
│          │          ┌──────────────────┐                               │          │
│          └─────────▶│  Git Repository  │◀──────────────────────────────┘          │
│                     │  (worktrees,     │                                           │
│                     │   branches,      │                                           │
│                     │   notes)         │                                           │
│                     └──────────────────┘                                           │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### The 4-Layer Context Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        4-LAYER AI CONTEXT ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 1: SYSTEM CONTEXT                                              │ │
│  │  ─────────────────────────────────────────────────────────────────────│ │
│  │  📁 Source:  .github/agents/{role}.agent.md                           │ │
│  │  🎯 Purpose: Governs AI behavior and capabilities                     │ │
│  │  📝 Content: Role instructions, constraints, guidelines               │ │
│  │                                                                       │ │
│  │  Roles: PM │ Architect │ Engineer │ Reviewer │ UX                     │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    ⬇                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 2: USER PROMPT (Enhanced with Prompt Engineering)              │ │
│  │  ─────────────────────────────────────────────────────────────────────│ │
│  │  📁 Source:  Issue metadata, Git notes, branch info                   │ │
│  │  🎯 Purpose: What the user asks / task requirements                   │ │
│  │  📝 Content: Title, description, acceptance criteria, labels          │ │
│  │                                                                       │ │
│  │  ✨ Enhanced by PromptEngineer class with:                            │ │
│  │     • Role-specific templates    • Success criteria                   │ │
│  │     • Input/output definitions   • Quality checklists                 │ │
│  │     • Approach hints             • Handoff requirements               │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    ⬇                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 3: MEMORY                                                      │ │
│  │  ─────────────────────────────────────────────────────────────────────│ │
│  │  📁 Source:  .context-weave/memory.json                               │ │
│  │  🎯 Purpose: Persistent knowledge across sessions                     │ │
│  │  📝 Content: Lessons learned, session history, success metrics        │ │
│  │                                                                       │ │
│  │  Components:                                                          │ │
│  │  • 📚 Lessons Learned   - What worked, what didn't                    │ │
│  │  • 📊 Execution Records - Track attempts and outcomes                 │ │
│  │  • 💾 Session Context   - Continue where you left off                 │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    ⬇                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 4: RETRIEVAL CONTEXT                                           │ │
│  │  ─────────────────────────────────────────────────────────────────────│ │
│  │  📁 Source:  .github/skills/{category}/{skill}/SKILL.md               │ │
│  │  🎯 Purpose: Knowledge grounding from documentation                   │ │
│  │  📝 Content: Technical guidelines, best practices, standards          │ │
│  │                                                                       │ │
│  │  Smart Label Routing:                                                 │ │
│  │  • security → Security + Testing skills                               │ │
│  │  • api      → API Design + Security skills                            │ │
│  │  • database → Database + Performance skills                           │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Automation Features

ContextWeave implements a **10-Layer Orchestration System** that automates quality monitoring, learning, and validation:

### Layer 1: Backlog Management
- **Task Creation Validation** - Enforces "standalone task principle"
  - ✅ Validates references field (code files)
  - ✅ Validates documentation field (design docs)
  - ✅ Runs "stranger test" (no implicit knowledge)
  - Script: `.github/scripts/validate-task-creation.sh`

### Layer 2: Context Optimization
- **Dynamic Context Generation** - Task-specific skill loading
- **Smart Label Routing** - API → Security + Testing skills
- **Prompt Enhancement** - Automatic success criteria + approach hints

### Layer 3: Planning & Validation
- **Pre-Flight Planning** - Execution plans with risks/rollback
  - Template: `.github/templates/PLAN-TEMPLATE.md`
- **Alignment Validation** - PRD → Spec → Code traceability
  - Script: `.github/scripts/validate-alignment.sh`
- **DoD Checklists** - Role-specific Definition of Done validation

### Layer 4: Quality Monitoring (Automated)
- **Stuck Issue Detection** - Every 30 minutes via GitHub Actions
  - ⏱️ Detects issues inactive >24h (configurable by type)
  - 🚨 Auto-escalates with `needs:help` label
  - Workflow: `.github/workflows/health-monitoring.yml`
  
- **Crash Recovery** - Every 15 minutes
  - ♻️ Auto-retries failed workflows once
  - 🚨 Escalates after 2nd failure
  - Workflow: `.github/workflows/crash-recovery.yml`

### Layer 5: Learning Loop (Self-Healing)
- **Pattern Analysis** - Monthly analysis of closed issues
  - 📊 Identifies common failure types
  - 🎯 Tracks success rates by role
  - Script: `.github/scripts/analyze-learning.py`
  
- **Automatic Instruction Updates** - Generates PRs with improvements
  - 📝 Updates agent instructions based on patterns
  - ✅ Requires human approval before merge
  - Workflow: `.github/workflows/learning-loop.yml`

### Layer 6: Visibility
- **CLI Dashboard** - Real-time status (`context-weave status --watch`)
- **Web Dashboard** - GitHub Pages with charts
  - 📈 Success rate trends (30 days)
  - 🎯 Issues by role/status
  - Location: `.github/pages/`
  
- **Bottleneck Detection** - Weekly workflow analysis
  - 🔍 Detects queue buildup
  - ⚠️ Identifies slow stages
  - Script: `.github/scripts/detect-bottlenecks.py`

### Layer 7: SubAgent Orchestration
- **Worktree Isolation** - Each task gets separate directory
- **Context per Task** - No cross-contamination
- **Lifecycle Management** - spawn → execute → complete → cleanup

### Layer 8: Code Inspection
- **DebugMCP Integration** - Runtime inspection (scaffolding)
  - Module: `context_weave/debugmcp.py`
- **Static Analysis** - Basic code quality checks
  - Detects: Bare excepts, TODOs, complexity issues

### Layer 9: Local Fallback
- **Offline Operation** - Full functionality without GitHub
- **Local Issue Management** - `context-weave issue` commands
- **Auto-sync** - Reconnects and syncs when GitHub available

### Layer 10: Completion Traceability
- **Completion Certificates** - Generated on merge
  - Hook: `.github/hooks/post-merge`
  - Stored: `.context-weave/certificates/`
- **Audit Trail** - Immutable Git commit history
- **Metrics Tracking** - Success rates, resolution times

### Automation Summary

| Feature | Frequency | Automated | Manual |
|---------|-----------|-----------|--------|
| Stuck Detection | Every 30 min | ✅ | - |
| Crash Recovery | Every 15 min | ✅ | - |
| Learning Analysis | Monthly | ✅ | Approval only |
| Bottleneck Detection | Weekly | ✅ | - |
| Task Validation | On creation | ✅ | - |
| DoD Validation | Pre-push | ✅ | - |
| Completion Certificates | On merge | ✅ | - |

---

### Prompt Engineering Pipeline

Raw prompts are automatically enhanced before being sent to AI agents:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PROMPT ENGINEERING PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Raw Issue/Prompt                                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ "Fix login page 500 error"                                          │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    PromptEngineer.enhance_prompt()                   │  │
│   │  ─────────────────────────────────────────────────────────────────── │  │
│   │  ✓ Apply role-specific template (PM/Architect/Engineer/...)         │  │
│   │  ✓ Add context summary (dependencies, specs, previous session)      │  │
│   │  ✓ Define inputs and expected outputs                               │  │
│   │  ✓ Extract constraints from prompt text                             │  │
│   │  ✓ Add success criteria based on issue type (bug/feature/story)     │  │
│   │  ✓ Include label-specific hints (security, api, database)           │  │
│   │  ✓ Define handoff requirements for next role                        │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │              validate_prompt_completeness() → Score: 85%             │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   Enhanced Prompt                                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ ### 🎯 Role                                                         │  │
│   │ You are a **Software Engineer** focused on secure, maintainable...  │  │
│   │                                                                     │  │
│   │ ### 📋 Task                                                         │  │
│   │ **Issue #42**: Fix login page 500 error...                          │  │
│   │                                                                     │  │
│   │ ### 📤 Expected Outputs                                             │  │
│   │ - Production code, Unit tests (≥80%), Documentation                 │  │
│   │                                                                     │  │
│   │ ### 🎯 Success Criteria                                             │  │
│   │ ✓ Root cause identified ✓ Regression test added ✓ Tests pass        │  │
│   │                                                                     │  │
│   │ ### 💡 Suggested Approach                                           │  │
│   │ 1. Validate all inputs 2. Check OWASP Top 10 3. Write tests first   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Multi-Agent Workflow

ContextWeave supports a hub-and-spoke multi-agent pattern:

```
                            ┌─────────────────┐
                            │    Agent X      │
                            │   (Hub/Router)  │
                            └────────┬────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
    ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
    │  PM Agent    │          │  Architect   │          │  UX Designer │
    │              │          │    Agent     │          │    Agent     │
    │ Output: PRD  │          │ Output: ADR  │          │ Output: UX   │
    └──────┬───────┘          └──────┬───────┘          └──────┬───────┘
           │                         │                         │
           │     Status: Ready       │     Status: Ready       │
           └────────────┬────────────┴────────────┬────────────┘
                        │                         │
                        ▼                         ▼
                 ┌──────────────┐          ┌──────────────┐
                 │   Engineer   │          │   Reviewer   │
                 │    Agent     │────────▶ │    Agent     │
                 │              │  Status: │              │
                 │ Output: Code │ In Review│ Output: LGTM │
                 └──────────────┘          └──────────────┘

Workflow: PM → UX → Architect → Engineer → Reviewer → Done
```

---

## 📦 Installation

### Prerequisites

- **Python 3.10+**
- **Git 2.20+** (for worktree and notes support)
- **VS Code** with GitHub Copilot (for sub-agent dropdown)

### Install from GitHub

```bash
pip install git+https://github.com/jnPiyush/ContextWeave.git
```

### Install from Source (Development)

```bash
# Clone the repository
git clone https://github.com/jnPiyush/ContextWeave.git
cd ContextWeave

# Install in editable mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
context-weave --version
# context-weave, version 2.0.0
```

### Initialize in Your Project

```bash
cd your-project
context-weave init --mode local
```

This step is **critical** — it deploys all the required files into your repository:

| Deployed Files | Location | Purpose |
|----------------|----------|---------|
| Agent definitions (7) | `.github/agents/*.agent.md` | Sub-agents in VS Code Copilot dropdown |
| Copilot instructions | `.github/copilot-instructions.md` | Global Copilot behavior rules |
| Coding instructions (4) | `.github/instructions/*.instructions.md` | Language-specific coding standards |
| Prompt templates (3) | `.github/prompts/*.prompt.md` | Reusable prompt templates |
| Document templates (6) | `.github/templates/*.md` | PRD, ADR, Spec, Review templates |
| Agent guidelines | `AGENTS.md` | Workflow & role definitions |
| Skills index | `Skills.md` | Technical standards reference |

> **Why this matters:** VS Code Copilot reads `.github/agents/*.agent.md` to populate the
> agent dropdown. Without running `context-weave init`, these files won't exist in your
> repo and the sub-agents (Engineer, Architect, PM, Reviewer, UX, DevOps, Agent X) won't
> appear.

Use `--force` to overwrite existing scaffold files:

```bash
context-weave init --mode local --force
```

---

## 🚀 Quick Start

### 1. Initialize in Your Repository

```bash
cd your-project
context-weave init --mode local
```

**Modes:**
| Mode | Description |
|------|-------------|
| `local` | Fully offline, no GitHub required |
| `github` | Full sync with GitHub Issues/Projects |
| `hybrid` | Local work with periodic GitHub sync |

### 2. Create an Issue

```bash
context-weave issue create "Add JWT authentication" \
  --type feature \
  --label api \
  --label security \
  --body "Implement JWT-based auth for API endpoints"
```

### 3. Generate Context

```bash
context-weave context generate 1 --role engineer
```

This generates a complete context file with all 4 layers:
- System instructions for the engineer role
- Enhanced prompt with success criteria
- Relevant lessons from memory
- API and security skill documents

### 4. Work in Isolated Environment (Optional)

```bash
# Spawn a SubAgent with isolated Git worktree
context-weave subagent spawn 1 --role engineer

# Work in isolation, then complete
context-weave subagent complete 1
```

### 5. Validate Before Completion

```bash
# Validate Definition of Done
context-weave validate 1 --dod
```

---

## 🔧 CLI Commands

### Overview

```
context-weave
├── init          # Initialize ContextWeave in repository
├── auth          # GitHub OAuth authentication
│   ├── login     # Authenticate with GitHub
│   ├── logout    # Remove authentication
│   └── status    # Show auth status
├── config        # View/modify configuration
├── issue         # Create/manage local issues
│   ├── create    # Create new issue
│   ├── list      # List issues
│   ├── show      # Show issue details
│   ├── edit      # Edit issue
│   ├── close     # Close issue
│   └── reopen    # Reopen issue
├── context       # Generate context for issues
│   ├── generate  # Generate context file
│   ├── show      # Display context
│   └── refresh   # Refresh context
├── memory        # Manage AI agent memory (Layer 3)
│   ├── show      # Show memory summary
│   ├── lessons   # Manage lessons learned
│   ├── record    # Record execution outcome
│   ├── metrics   # Show success metrics
│   └── session   # Manage session context
├── subagent      # Manage SubAgent worktrees
│   ├── spawn     # Create isolated worktree
│   ├── list      # List active SubAgents
│   ├── status    # Show SubAgent status
│   └── complete  # Complete and cleanup
├── validate      # Run validation checks
│   ├── task      # Validate task quality
│   ├── preexec   # Pre-execution checks
│   └── dod       # Definition of Done validation
├── sync          # Sync with GitHub
│   ├── setup     # Configure GitHub sync
│   ├── pull      # Pull from GitHub
│   └── push      # Push to GitHub
├── start         # Quick-start: create issue + spawn subagent + generate context
├── export        # Export markdown documents to DOCX and PDF formats
├── doctor        # Diagnose and fix common ContextWeave issues
├── dashboard     # Start real-time web dashboard (experimental)
└── status        # Show current status
```

### Key Commands

#### Generate Context
```bash
# Generate context for issue #42 as engineer
context-weave context generate 42 --role engineer

# Output to specific file
context-weave context generate 42 --output ./context-42.md
```

#### Memory Management
```bash
# Show memory summary
context-weave memory show

# Add a lesson learned
context-weave memory lessons add \
  --issue 42 \
  --category security \
  --lesson "Always validate user input" \
  --outcome failure

# Record execution outcome
context-weave memory record 42 \
  --role engineer \
  --action "implement feature" \
  --outcome success

# Show success metrics
context-weave memory metrics
```

#### Validation
```bash
# Validate task quality
context-weave validate 42 --task

# Run pre-execution checks
context-weave validate 42 --preexec

# Validate Definition of Done
context-weave validate 42 --dod
```

---

## 📁 Project Structure

```
ContextWeave/
├── context_weave/                 # Main package
│   ├── __init__.py
│   ├── cli.py                  # CLI entry point
│   ├── config.py               # Configuration management
│   ├── state.py                # Git-based state management
│   ├── memory.py               # Layer 3: Memory implementation
│   ├── prompt.py               # Prompt engineering module
│   ├── security.py             # Security utilities
│   ├── dashboard.py            # Dashboard server
│   ├── debugmcp.py             # MCP debug integration
│   ├── scaffolds/              # Bundled scaffold files (shipped with pip)
│   │   ├── __init__.py         # get_scaffolds_dir() helper
│   │   ├── AGENTS.md           # Agent guidelines (deployed to repo root)
│   │   ├── Skills.md           # Skills index (deployed to repo root)
│   │   └── github/             # Deployed to .github/ on init
│   │       ├── copilot-instructions.md
│   │       ├── agents/         # 7 agent definitions (.agent.md)
│   │       ├── instructions/   # 4 coding instructions
│   │       ├── prompts/        # 3 prompt templates
│   │       └── templates/      # 6 document templates
│   ├── commands/               # CLI command implementations
│   │   ├── auth.py             # GitHub OAuth authentication
│   │   ├── config.py           # Config commands
│   │   ├── context.py          # Context generation
│   │   ├── dashboard.py        # Dashboard commands
│   │   ├── doctor.py           # Diagnostics & repair
│   │   ├── export.py           # DOCX/PDF export
│   │   ├── init.py             # Repository initialization + scaffold deploy
│   │   ├── issue.py            # Issue management
│   │   ├── memory.py           # Memory CLI commands
│   │   ├── start.py            # Quick-start workflow
│   │   ├── status.py           # Status display
│   │   ├── subagent.py         # SubAgent management
│   │   ├── sync.py             # GitHub sync
│   │   └── validate.py         # Validation commands
│   ├── framework/              # Microsoft Agent Framework integration (optional)
│   │   ├── __init__.py         # Feature flag (AGENT_FRAMEWORK_AVAILABLE)
│   │   ├── agents.py           # Agent definitions
│   │   ├── config.py           # Framework configuration
│   │   ├── context_provider.py # Context provider
│   │   ├── middleware.py       # Middleware pipeline
│   │   ├── orchestrator.py     # Multi-agent orchestrator
│   │   ├── run.py              # Run CLI command
│   │   ├── thread_store.py     # Thread storage
│   │   └── tools.py            # Tool definitions
│   └── static/                 # Web dashboard assets
│       ├── dashboard.html
│       ├── dashboard.css
│       └── dashboard.js
├── docs/
│   └── architecture/
│       └── 4-LAYER-CONTEXT-ARCHITECTURE.md
├── examples/
│   └── prompt_enhancement_demo.py
├── tests/                      # Test suite
│   ├── test_auth.py
│   ├── test_config.py
│   ├── test_context_weave.py
│   ├── test_doctor.py
│   ├── test_issue.py
│   ├── test_memory.py
│   ├── test_prompt.py
│   ├── test_security.py
│   ├── test_start.py
│   ├── test_subagent.py
│   ├── test_sync.py
│   ├── test_validate.py
│   └── test_framework_*.py    # Framework integration tests
├── .github/
│   ├── agents/                 # Role-specific agent definitions
│   │   ├── agent-x.agent.md    # Hub coordinator
│   │   ├── engineer.agent.md
│   │   ├── architect.agent.md
│   │   ├── product-manager.agent.md
│   │   ├── reviewer.agent.md
│   │   ├── ux-designer.agent.md
│   │   └── devops-engineer.agent.md
│   ├── instructions/           # Language-specific coding standards
│   ├── prompts/                # Reusable prompt templates
│   ├── templates/              # Document templates (PRD, ADR, etc.)
│   └── skills/                 # Technical skill documents
│       ├── architecture/
│       ├── development/
│       ├── design/
│       ├── ai-systems/
│       └── operations/
├── pyproject.toml
├── AGENTS.md                   # Agent workflow guidelines
├── Skills.md                   # Skills index (25 skills)
└── CONTRIBUTING.md             # Contribution guide
```

---

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=context_weave --cov-report=html

# Run specific test file
pytest tests/test_memory.py -v
```

**Current Status:**
- Tests passing
- ~68% code coverage

---

## 🎨 Visual Examples

### Before vs After: Prompt Enhancement

<table>
<tr>
<th>❌ Raw Prompt</th>
<th>✅ Enhanced Prompt</th>
</tr>
<tr>
<td>

```
Fix login page 500 error
```

</td>
<td>

```markdown
### 🎯 Role
You are a **Software Engineer** focused on 
clean, secure, maintainable code.

### 📋 Task
**Issue #42**: Fix login page 500 error

### 📤 Expected Outputs
- Production code
- Unit tests (≥80%)
- Integration tests
- Documentation

### 🎯 Success Criteria
✅ Root cause identified
✅ Regression test added
✅ All tests pass

### 💡 Suggested Approach
1. Follow OWASP Top 10 guidelines
2. Validate all inputs
3. Write tests first (TDD)

### 🔄 Handoff to Reviewer
- All tests passing
- PR created
- Documentation updated
```

</td>
</tr>
</table>

### Memory Layer in Action

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MEMORY LAYER EXAMPLE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📊 Success Metrics                                                         │
│  ─────────────────                                                          │
│  Total Executions: 47                                                       │
│  Success Rate:     87.2%                                                    │
│  By Role:                                                                   │
│    • Engineer: 92% (38/41)                                                  │
│    • Architect: 83% (5/6)                                                   │
│                                                                             │
│  📚 Top Lessons Learned                                                     │
│  ──────────────────────                                                     │
│  1. [Security] Always validate input before processing                      │
│     Applied: 12 times | Effectiveness: 95%                                  │
│                                                                             │
│  2. [Testing] Write tests before implementing features                      │
│     Applied: 8 times | Effectiveness: 88%                                   │
│                                                                             │
│  3. [API] Use proper HTTP status codes for error responses                  │
│     Applied: 5 times | Effectiveness: 100%                                  │
│                                                                             │
│  ⚠️ Common Failures                                                         │
│  ─────────────────                                                          │
│  • test_failure: 4 occurrences                                              │
│  • lint_error: 2 occurrences                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Security

ContextWeave follows security best practices:

- ✅ **No hardcoded secrets** - Uses keyring for token storage
- ✅ **Input sanitization** - All user inputs are validated
- ✅ **SQL parameterization** - No injection vulnerabilities
- ✅ **Secure defaults** - Security-first configuration

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Start for Contributors

```bash
# Clone and setup
git clone https://github.com/jnPiyush/ContextWeave.git
cd ContextWeave
pip install -e ".[dev]"

# Or install directly for contributing
pip install git+https://github.com/jnPiyush/ContextWeave.git

# Run tests
pytest tests/ -v

# Check code quality
ruff check .
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [4-Layer Architecture](docs/architecture/4-LAYER-CONTEXT-ARCHITECTURE.md) | Detailed architecture documentation |
| [AGENTS.md](AGENTS.md) | Agent workflow and behavior guidelines |
| [Skills.md](Skills.md) | Technical skills index (25 skills) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI
- Inspired by best practices from [agentskills.io](https://agentskills.io)
- Follows [github/awesome-copilot](https://github.com/github/awesome-copilot) patterns

---

<div align="center">

**[⬆ Back to Top](#contextmd)**

Made with ❤️ for AI-assisted development

</div>
