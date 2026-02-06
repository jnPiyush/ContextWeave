# ADR-CONTEXT-WEAVE: ContextWeave System Architecture

**Status**: Accepted  
**Date**: 2026-01-29  
**Updated**: 2026-01-29  
**Epic**: #CONTEXT-WEAVE  
**PRD**: [PRD-CONTEXT-WEAVE.md](../prd/PRD-CONTEXT-WEAVE.md)

---

## Table of Contents

1. [Context](#context)
2. [Decision](#decision)
3. [Options Considered](#options-considered)
4. [Rationale](#rationale)
5. [Consequences](#consequences)
6. [Implementation](#implementation)
7. [References](#references)
8. [Review History](#review-history)

---

## Context

**Problem**: Current AgentX implementation achieves ~70-80% success rate in production code generation due to:
- Poor backlog quality (tasks lack complete context)
- Inefficient context management (loading irrelevant skills)
- No pre-execution planning or validation
- Missing quality monitoring and stuck detection
- No learning loops for continuous improvement
- Limited visibility into agent progress

**Requirements (from PRD)**:
- Achieve >95% success rate on production code generation
- 100% of tasks pass "stranger test" (executable without creator)
- Stuck issues detected within 1 hour
- Zero manual quality checks (fully automated)
- Context size naturally bounded by task scope
- SubAgent isolation per task
- **Must work without GitHub** (fully local operation)
- Complete audit trail and traceability

**Constraints**:
- Must work within VS Code extension model
- **Zero external dependencies** (only Git required)
- Must support offline/local operation as primary mode
- Scripts must be cross-platform (PowerShell + Bash)
- **GitHub optional** (not required for core functionality)

**Background**:
AgentX uses a hub-and-spoke architecture with Agent X as coordinator. The system needs enhanced context management to ensure each agent receives complete, focused context for their specific task without cross-contamination between concurrent tasks.

---

## Decision

We will implement a **Git-Native architecture** leveraging Git's built-in capabilities for state management, with hook-based automation and true SubAgent isolation via Git worktrees.

**Key architectural choices:**

1. **Git-Native State Management**: Use Git branches, commits, notes, and worktrees instead of external databases
2. **Hook-Based Automation**: Git hooks replace cron jobs for event-driven operation
3. **Worktree-Based SubAgent Isolation**: Each SubAgent operates in its own Git worktree (true directory isolation)
4. **Mode Selection**: Local-only, GitHub-connected, or Hybrid operation
5. **Minimal State File**: Only `.context-weave/state.json` for runtime state (active worktrees)
6. **CLI-First Interface**: `context-weave` command for all operations

---

## Options Considered

### Option 1: Monolithic Agent with Shared Context

**Description:**
Single agent handles all tasks with shared context across sessions.

**Pros:**
- Simple implementation
- No coordination overhead

**Cons:**
- Context contamination between tasks
- Cannot parallelize work
- Difficult to debug

**Effort**: S  
**Risk**: High (context contamination)

---

### Option 2: SQLite-Based State Management

**Description:**
Use SQLite for all state management with SQL queries for analytics.

**Pros:**
- ACID transactions
- Query capabilities
- Familiar tooling

**Cons:**
- Additional dependency
- Not version-controllable
- Duplicate source of truth (Git + SQLite)

**Effort**: M  
**Risk**: Medium (complexity, dual state)

---

### Option 3: JSON/File-Based State Management

**Description:**
Use JSON/Markdown files in `.context-weave/` for all state.

**Pros:**
- Human-readable
- No dependencies
- Works offline

**Cons:**
- No ACID transactions
- Race conditions with concurrent writes
- Not queryable
- Audit log immutability must be enforced manually

**Effort**: M  
**Risk**: Medium (concurrency, auditability)

---

### Option 4: Git-Native State Management (Selected)

**Description:**
Leverage Git's built-in features for all state management:
- **Branches** = Issues/Tasks
- **Commits** = Audit log (already immutable!)
- **Git Notes** = Metadata (JSON attached to commits)
- **Worktrees** = SubAgent isolation (separate directories)
- **Hooks** = Event-driven automation

**Pros:**
- Zero external dependencies (Git already required)
- Immutable audit log built-in (commit hashes)
- True SubAgent isolation via worktrees
- Native GitHub/GitLab integration (push/pull)
- Offline-first by design
- Human-readable (git log, git show)
- ACID at commit level

**Cons:**
- Learning curve for Git notes and worktrees
- Complex queries require git log parsing
- Branch management overhead

**Effort**: M  
**Risk**: Low (proven technology)

---

### Option 5: MCP-Native State Management

**Description:**
Build ContextWeave as full MCP server.

**Pros:**
- Native VS Code integration
- Tool-based API

**Cons:**
- Significant implementation effort
- VS Code specific
- Requires MCP server maintenance

**Effort**: XL  
**Risk**: Medium (new technology)
- Requires MCP server maintenance
- Less portable (VS Code specific)
- Steeper learning curve

**Effort**: XL  
**Risk**: Medium (new technology)

---

## Rationale

We chose **Option 4: Git-Native State Management** because:

1. **Zero Dependencies**: Git is already required - no additional tools needed
2. **True Immutability**: Git commit history is cryptographically immutable (SHA-256 hashes)
3. **Worktree Isolation**: Git worktrees provide TRUE directory-level isolation for SubAgents
4. **Native Sync**: GitHub/GitLab integration is just `git push/pull`
5. **Offline-First**: Git was designed for offline operation
6. **Human-Readable**: `git log`, `git show`, `git notes` all produce readable output
7. **Event-Driven**: Git hooks replace polling/cron with instant event response

**Key decision factors:**
- Simplicity (leverage what Git already does)
- Reliability (Git is battle-tested)
- Transparency (state visible via standard Git commands)
- No vendor lock-in (works with any Git host or none)

**Git Features Utilized:**

| Feature | Purpose |
|---------|---------|
| Branches | Issue/task tracking (`issue-456-jwt-auth`) |
| Commits | Immutable audit log |
| Git Notes | Metadata (JSON attached to commits) |
| Worktrees | SubAgent isolation (separate directories) |
| Hooks | Event-driven automation |
| Tags | Milestones, certificates |

---

## Consequences

### Positive
- Zero external dependencies beyond Git
- Truly immutable audit trail (Git's core design)
- SubAgent isolation via worktrees (different directories, same repo)
- Works fully offline with any Git remote (GitHub, GitLab, local)
- Mode selection: Local-only, GitHub, or Hybrid
- Hook-based = instant response (no polling delays)
- Human-readable via standard Git commands

### Negative
- Learning curve for Git worktrees and notes
- Complex queries require parsing `git log` output
- Branch management overhead (many branches)

### Neutral
- Minimal state file (`.context-weave/state.json`) for runtime worktree tracking
- Context files (`.context-weave/context-{issue}.md`) remain for agent consumption

---

## Implementation

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    GIT-NATIVE ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MODE SELECTION                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │   LOCAL     │ │   GITHUB    │ │   HYBRID    │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
│                                                                  │
│  GIT-BASED STORAGE                                              │
│  ─────────────────                                              │
│  • Issues     → Branches (issue-{id}-{slug})                   │
│  • Status     → Branch lifecycle + commit markers               │
│  • Audit Log  → Git commit history (immutable!)                │
│  • Metadata   → Git notes (JSON on commits)                    │
│  • SubAgents  → Git worktrees (true isolation!)                │
│                                                                  │
│  HOOK-BASED AUTOMATION                                          │
│  ─────────────────────                                          │
│  • prepare-commit-msg → Auto-add issue reference               │
│  • pre-commit        → Validate context exists                 │
│  • post-commit       → Update activity, log audit              │
│  • pre-push          → Handoff validation (DoD)                │
│  • post-merge        → Certificate, metrics                    │
│                                                                  │
│  MINIMAL STATE FILE                                             │
│  ─────────────────────                                          │
│  .context-weave/state.json                                      │
│  • Active worktrees                                             │
│  • Mode configuration                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### SubAgent Isolation via Worktrees

```
Main Repo (./)
├── .git/                      # Shared Git database
├── .context-weave/
│   ├── state.json             # Active worktrees
│   └── context-456.md         # Generated (gitignored)
└── src/, docs/                # Main working directory

SubAgent-456 Worktree (../.worktrees/subagent-456/)
├── .git → ../../repo/.git     # Points to same Git DB
└── src/, docs/                # Checked out to issue-456 branch
                               # TRUE ISOLATION!

SubAgent-457 Worktree (../.worktrees/subagent-457/)
└── (Different branch, different files, same repo)
```

### CLI Interface

```bash
context-weave init [--mode local|github|hybrid]
context-weave issue create "Title" --type story
context-weave issue list [--status in_progress]
context-weave context generate <issue>
context-weave subagent start <issue>
context-weave subagent stop <issue>
context-weave validate task <issue>
context-weave validate handoff <issue>
context-weave status
context-weave dashboard [--watch]
context-weave metrics [--period 30d]
context-weave sync  # hybrid mode
```

**Detailed specification**: [SPEC-CONTEXT-WEAVE.md](../specs/SPEC-CONTEXT-WEAVE.md)  
**Full architecture**: [ARCHITECTURE-CONTEXT-WEAVE.md](../architecture/ARCHITECTURE-CONTEXT-WEAVE.md)

---

## References

### Internal
- [PRD-CONTEXT-WEAVE.md](../prd/PRD-CONTEXT-WEAVE.md) - Product Requirements
- [ARCHITECTURE-CONTEXT-WEAVE.md](../architecture/ARCHITECTURE-CONTEXT-WEAVE.md) - Full Architecture
- [AGENTS.md](../../AGENTS.md) - Agent Workflows

### External
- [Git Worktrees](https://git-scm.com/docs/git-worktree)
- [Git Notes](https://git-scm.com/docs/git-notes)
- [Git Hooks](https://git-scm.com/docs/githooks)

---

## Review History

| Date | Reviewer | Status | Notes |
|------|----------|--------|-------|
| 2026-01-29 | Architect Agent | Draft | Initial file-based architecture |
| 2026-01-29 | Architect Agent | Revised | Updated to Git-Native with worktrees |

---

**Author**: Architect Agent  
**Last Updated**: 2026-01-29
