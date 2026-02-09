# ContextWeave - Runtime Context Management for AI Agents

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Achieve >95% success rate in AI agent production code generation** through Git-native state management, worktree-based isolation, and automated quality gates.

## 🎯 Key Features

- **Git-Native**: Zero external dependencies - uses Git branches, worktrees, notes, and hooks
- **SubAgent Isolation**: True directory separation via Git worktrees
- **Hook-Based Automation**: Event-driven validation, no polling required
- **Mode Selection**: Local-only, GitHub-connected, or Hybrid operation
- **Full Traceability**: Immutable audit log via Git commit history

## 📦 Installation

```bash
pip install git+https://github.com/jnPiyush/ContextWeave.git
```

## 🚀 Quick Start

```bash
# Initialize in your Git repository
context-weave init --mode local

# Create a SubAgent for issue #456
context-weave subagent spawn 456 --role engineer --title jwt-auth

# Generate context
context-weave context generate 456

# Check status
context-weave status

# Diagnose issues
context-weave doctor

# Validate Definition of Done
context-weave validate 456 --dod

# Complete the SubAgent
context-weave subagent complete 456
```

## 📖 Commands

### `context-weave init`
Initialize ContextWeave in a Git repository.

```bash
context-weave init [--mode local|github|hybrid] [--force]
```

**Modes:**
- `local` - Works fully offline, no GitHub required
- `github` - Full sync with GitHub Issues and Projects
- `hybrid` - Local work with periodic GitHub sync

### `context-weave subagent`
Manage SubAgent worktrees for isolated task execution.

```bash
# Create a SubAgent with isolated worktree
context-weave subagent spawn <issue> --role <role> [--title <description>]

# List active SubAgents
context-weave subagent list [--json]

# Show SubAgent details
context-weave subagent status <issue>

# Complete and cleanup
context-weave subagent complete <issue> [--force] [--keep-branch]

# Recover corrupted worktree
context-weave subagent recover <issue>
```

**Roles:** `pm`, `architect`, `engineer`, `reviewer`, `ux`

### `context-weave context`
Generate and manage context files.

```bash
# Generate context for an issue
context-weave context generate <issue> [--role <role>] [--output <path>]

# Show context file
context-weave context show <issue> [--metadata]

# Refresh/regenerate
context-weave context refresh <issue>
```

### `context-weave validate`
Run validation checks.

```bash
# Validate task quality
context-weave validate <issue> --task

# Pre-flight validation
context-weave validate <issue> --pre-exec

# Definition of Done
context-weave validate <issue> --dod [--certificate]

# All validations
context-weave validate <issue> --all
```

### `context-weave status`
Show current status and dashboard.

```bash
context-weave status [--json] [--watch]
```

### `context-weave config`
View and modify configuration.

```bash
# Show current mode
context-weave config

# List all settings
context-weave config --list

# Get specific setting
context-weave config hooks.pre_push

# Set a value
context-weave config mode github
```

## 🏗️ Architecture

ContextWeave uses a **Git-Native** architecture:

| Need | Git Feature | Benefit |
|------|-------------|---------|
| Issue tracking | Branches | `issue-456-jwt-auth` |
| Audit log | Commit history | Immutable, SHA-256 hashed |
| Metadata | Git Notes | JSON attached to commits |
| SubAgent isolation | Worktrees | Separate directories |
| Event triggers | Hooks | Instant, no polling |
| Sync | Push/Pull | Native GitHub/GitLab support |

### Directory Structure

```
Repository/
├── .context-weave/           # Minimal runtime state
│   ├── state.json            # Active worktrees
│   ├── config.json           # Configuration
│   └── context-{issue}.md    # Generated context files
│
├── .git/hooks/               # Automation
│   ├── prepare-commit-msg    # Auto-add issue reference
│   ├── pre-commit            # Validate context
│   ├── post-commit           # Update activity
│   ├── pre-push              # DoD validation
│   └── post-merge            # Certificate generation
│
└── ../worktrees/             # SubAgent isolation
    ├── 456/                  # Issue 456 worktree
    └── 457/                  # Issue 457 worktree
```

## 🔧 Git Hooks

ContextWeave installs these Git hooks for automation:

| Hook | Purpose |
|------|---------|
| `prepare-commit-msg` | Auto-adds issue reference from branch name |
| `pre-commit` | Validates context file exists, runs linters |
| `post-commit` | Updates Git notes with activity timestamp |
| `pre-push` | **Validates Definition of Done** (blocks if incomplete) |
| `post-merge` | Generates completion certificate |

## 📊 Validation

### Task Quality Validation
- Title and description exist
- Acceptance criteria defined
- No implicit knowledge (stranger test)

### Pre-Flight Validation
- Context file generated
- SubAgent spawned
- Worktree accessible
- Branch exists

### Definition of Done (by role)

**Engineer:**
- [ ] Code committed and pushed
- [ ] Tests written (>=80% coverage)
- [ ] Tests passing
- [ ] Documentation updated
- [ ] No linter errors
- [ ] Security scan passed

**PM:**
- [ ] PRD created
- [ ] Child issues created
- [ ] Acceptance criteria defined
- [ ] Success metrics specified

**Architect:**
- [ ] ADR created
- [ ] Tech Spec created
- [ ] Options documented
- [ ] Decision rationale clear

## 🔗 Integration with AgentX

ContextWeave is designed to work with the [ContextWeave](https://github.com/jnPiyush/ContextWeave) multi-agent workflow:

1. **PM Agent** creates Epic → PRD
2. **Architect Agent** designs → ADR + Spec
3. **Engineer Agent** implements → Code + Tests
4. **Reviewer Agent** reviews → Approval

Each agent runs in an isolated SubAgent worktree with task-specific context.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Documentation:** [Architecture](docs/architecture/ARCHITECTURE-CONTEXT-WEAVE.md) | [PRD](docs/prd/PRD-CONTEXT-WEAVE.md) | [ADR](docs/adr/ADR-CONTEXT-WEAVE.md)
