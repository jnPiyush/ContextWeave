# Context.md - Complete Architecture & Implementation Plan

**Version**: 2.0  
**Date**: 2026-01-29  
**Updated**: 2026-01-29  
**Author**: Architect Agent  
**Status**: Approved  
**Related Documents**:
- [PRD-CONTEXT-MD.md](../prd/PRD-CONTEXT-MD.md)
- [ADR-CONTEXT-MD.md](../adr/ADR-CONTEXT-MD.md)
- [SPEC-CONTEXT-MD.md](../specs/SPEC-CONTEXT-MD.md)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Architecture Principles](#3-architecture-principles)
4. [High-Level Architecture](#4-high-level-architecture)
5. [Git-Native Design](#5-git-native-design)
6. [SubAgent Isolation via Worktrees](#6-subagent-isolation-via-worktrees)
7. [Hook-Based Automation](#7-hook-based-automation)
8. [Mode Selection](#8-mode-selection)
9. [CLI Interface](#9-cli-interface)
10. [Data Architecture](#10-data-architecture)
11. [Implementation Plan](#11-implementation-plan)
12. [Risk Management](#12-risk-management)
13. [Success Metrics](#13-success-metrics)

---

## 1. Executive Summary

### 1.1 Purpose

Context.md is a runtime context management and quality orchestration system designed to achieve **>95% success rate** in AI agent production code generation through:

- **Git-Native state management** (zero external dependencies)
- **Worktree-based SubAgent isolation** (true directory separation)
- **Hook-based automation** (instant event response, no polling)
- **Mode selection** (Local / GitHub / Hybrid operation)
- **Full traceability** (Git's immutable commit history)

### 1.2 Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **State Management** | Git-Native (branches, notes, worktrees) | Zero dependencies, immutable audit |
| **SubAgent Isolation** | Git Worktrees | True directory isolation |
| **Automation** | Git Hooks | Event-driven, no polling |
| **Operations Mode** | Selectable (Local/GitHub/Hybrid) | Works without GitHub |
| **Interface** | CLI (`context-md`) | Cross-platform, scriptable |

### 1.3 What Git Provides (Free)

| Need | Git Feature | Benefit |
|------|-------------|---------|
| Issue tracking | Branches | `issue-456-jwt-auth` |
| Audit log | Commit history | Immutable, SHA-256 hashed |
| Metadata | Git Notes | JSON attached to commits |
| SubAgent isolation | Worktrees | Separate directories |
| Event triggers | Hooks | Instant, no polling |
| Sync | Push/Pull | Native GitHub/GitLab support |
| Offline | Core design | Works without network |

### 1.4 Timeline Overview

```
Week 1-2   │ Week 3-4   │ Week 5-6   │ Week 7-8   │ Week 9-10  │ Week 11-12
───────────┼────────────┼────────────┼────────────┼────────────┼────────────
PHASE 1    │ PHASE 2    │ PHASE 3    │ PHASE 4    │ PHASE 5    │ PHASE 6
Foundation │ Worktrees  │ Hooks &    │ Learning   │ CLI &      │ Polish &
& CLI      │ SubAgents  │ Validation │ Loop       │ Dashboard  │ Docs
```

---

## 2. System Overview

### 2.1 Problem Statement

Current AgentX achieves ~70-80% success rate due to:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         CURRENT STATE PROBLEMS                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. POOR BACKLOG QUALITY                    Impact: 40% handoff failures   │
│     └─ Tasks assume creator will execute                                    │
│     └─ Dependencies without integration points                              │
│     └─ Missing references and documentation                                 │
│                                                                             │
│  2. INEFFICIENT CONTEXT                     Impact: 30% token waste        │
│     └─ Loading all 25 skills regardless of task                            │
│     └─ No task-specific assembly                                           │
│     └─ Context carryover between tasks                                     │
│                                                                             │
│  3. NO PRE-FLIGHT VALIDATION                Impact: Late failures          │
│     └─ No execution plan generation                                        │
│     └─ No pre-work validation                                              │
│     └─ Issues discovered at handoff                                        │
│                                                                             │
│  4. NO QUALITY MONITORING                   Impact: Stuck issues           │
│     └─ No stuck detection                                                  │
│     └─ No crash recovery                                                   │
│     └─ Manual quality checks                                               │
│                                                                             │
│  5. NO LEARNING                             Impact: Repeated failures      │
│     └─ Same mistakes recur                                                 │
│     └─ No pattern analysis                                                 │
│     └─ Manual instruction updates                                          │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Solution: Ten-Layer Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         CONTEXT.MD SOLUTION                                 │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ L1: BACKLOG MANAGEMENT ─────────── Standalone task enforcement      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ L2: CONTEXT OPTIMIZATION ───────── Task-specific context assembly   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ L3: PLANNING & VALIDATION ──────── Pre-flight checks, DoD          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ L4: QUALITY MONITORING ─────────── Stuck detection, crash recovery │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ L5: LEARNING LOOP ──────────────── Pattern analysis, auto-update   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ L6: VISIBILITY ─────────────────── CLI & Web dashboards            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ L7: SUBAGENT ORCHESTRATION ─────── Isolated context per task       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ L8: CODE INSPECTION ────────────── DebugMCP, static analysis       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ L9: LOCAL FALLBACK ─────────────── Offline mode, GitHub sync       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ L10: COMPLETION TRACEABILITY ───── Audit trail, certificates       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Architecture Principles

### 3.1 Design Principles

| Principle | Description | Implementation |
|-----------|-------------|----------------|
| **Simplicity** | Minimize dependencies and complexity | Git-native features, minimal state file |
| **Transparency** | Human-readable state for debugging | Git history, notes, branch names |
| **Isolation** | No cross-contamination between tasks | **Git Worktrees** (TRUE directory isolation) |
| **Resilience** | Work offline, recover from failures | Git is offline-first by design |
| **Automation** | No manual quality checks | **Git Hooks** (event-driven) |
| **Traceability** | Full audit trail | **Git commits** (immutable, SHA-hashed) |

### 3.2 Non-Negotiable Requirements

```
┌────────────────────────────────────────────────────────────────────────────┐
│                       NON-NEGOTIABLE REQUIREMENTS                           │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ✓ ZERO EXTERNAL DEPENDENCIES                                               │
│    └─ ONLY Git required (already present in dev environment)               │
│    └─ No databases, message queues, cloud services, or Docker              │
│    └─ GitHub CLI optional (for GitHub mode only)                           │
│                                                                             │
│  ✓ GIT-NATIVE DESIGN                                                        │
│    └─ Branches = Issues/Tasks                                               │
│    └─ Commits = Immutable audit log (already SHA-256 hashed!)              │
│    └─ Git Notes = Metadata (JSON attached to commits)                      │
│    └─ Worktrees = SubAgent isolation (separate directories)                │
│    └─ Hooks = Event-driven automation (no polling)                         │
│                                                                             │
│  ✓ MODE SELECTION                                                           │
│    └─ Local-only: Works without any network, no GitHub required            │
│    └─ GitHub-connected: Full sync with GitHub Issues/Projects              │
│    └─ Hybrid: Local work + periodic GitHub sync                            │
│                                                                             │
│  ✓ OFFLINE-FIRST                                                            │
│    └─ Core functionality works without any network                         │
│    └─ GitHub integration is OPTIONAL enhancement, not requirement          │
│                                                                             │
│  ✓ HOOK-BASED AUTOMATION                                                    │
│    └─ prepare-commit-msg: Auto-add issue reference                         │
│    └─ pre-commit: Validate context exists                                  │
│    └─ post-commit: Update activity, log audit                              │
│    └─ pre-push: Handoff validation (DoD check)                             │
│    └─ post-merge: Generate certificate, update metrics                     │
│                                                                             │
│  ✓ BACKWARD COMPATIBLE                                                      │
│    └─ Works with existing AgentX workflow                                  │
│    └─ Opt-in for new features                                              │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. High-Level Architecture

### 4.1 System Context Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           SYSTEM CONTEXT                                    │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                           ┌──────────────────┐                              │
│                           │    DEVELOPER     │                              │
│                           │    (Human)       │                              │
│                           └────────┬─────────┘                              │
│                                    │                                        │
│                         Creates issues, reviews PRs                         │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────┐    ┌─────────────────────┐    ┌──────────────────┐   │
│  │    VS CODE       │◄──►│    CONTEXT.MD       │◄──►│     GITHUB       │   │
│  │                  │    │    SYSTEM           │    │                  │   │
│  │  • Agent Mode    │    │                     │    │  • Issues        │   │
│  │  • Copilot Chat  │    │  • Context Gen      │    │  • Projects V2   │   │
│  │  • Terminal      │    │  • Validation       │    │  • Actions       │   │
│  │  • File System   │    │  • SubAgent Mgmt    │    │  • Pages         │   │
│  │                  │    │  • Quality Monitor  │    │                  │   │
│  └──────────────────┘    └─────────────────────┘    └──────────────────┘   │
│           ▲                        ▲                        ▲               │
│           │                        │                        │               │
│           │              ┌─────────┴─────────┐              │               │
│           │              │                   │              │               │
│           ▼              ▼                   ▼              ▼               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         LOCAL FILE SYSTEM                             │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │ .agent-context/ │  │ .github/scripts/│  │ docs/dashboard/     │   │  │
│  │  │ (Runtime State) │  │ (Automation)    │  │ (Web UI)            │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Container Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                       GIT-NATIVE ARCHITECTURE                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                        VS CODE EXTENSION HOST                          │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │                      AGENT X (Orchestrator)                      │  │ │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │  │ │
│  │  │  │ Issue Router│  │ SubAgent    │  │ Status Monitor          │  │  │ │
│  │  │  │ (Branches)  │  │ Spawner     │  │ (Hook Events)           │  │  │ │
│  │  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │  │ │
│  │  └──────────────────────────┬──────────────────────────────────────┘  │ │
│  │                             │                                          │ │
│  │         ┌───────────────────┼───────────────────┐                      │ │
│  │         │                   │                   │                      │ │
│  │         ▼                   ▼                   ▼                      │ │
│  │  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐              │ │
│  │  │  WORKTREE   │     │  WORKTREE   │     │  WORKTREE   │              │ │
│  │  │ (Issue 456) │     │ (Issue 457) │     │ (Issue 458) │              │ │
│  │  │             │     │             │     │             │              │ │
│  │  │ ../wt/456/  │     │ ../wt/457/  │     │ ../wt/458/  │              │ │
│  │  │ PM Agent    │     │ Engineer    │     │ Reviewer    │              │ │
│  │  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘              │ │
│  │         │                   │                   │                      │ │
│  └─────────┼───────────────────┼───────────────────┼──────────────────────┘ │
│            │                   │                   │                        │
│            ▼                   ▼                   ▼                        │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                         GIT NATIVE STORAGE                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │ │
│  │  │ BRANCHES    │  │ COMMITS     │  │ GIT NOTES   │  │ GIT HOOKS   │  │ │
│  │  │             │  │             │  │             │  │             │  │ │
│  │  │ issue-456-* │  │ Audit Log   │  │ Metadata    │  │ Automation  │  │ │
│  │  │ issue-457-* │  │ (Immutable) │  │ (JSON)      │  │ (Events)    │  │ │
│  │  │ issue-458-* │  │ SHA-256     │  │ refs/notes/ │  │ .git/hooks/ │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│            │                                                                │
│            ▼                                                                │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                     MINIMAL STATE FILE                                │ │
│  │                                                                        │ │
│  │  .agent-context/state.json                                            │ │
│  │  ├─ Active worktrees: [{issue: 456, path: "../wt/456", role: "pm"}]  │ │
│  │  └─ (Only runtime info that can't be derived from git)               │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```
│  │  │ analyze-    │  │ sync-to-    │  │ dashboard-  │  │ audit-      │  │ │
│  │  │ learning    │  │ github      │  │ cli         │  │ logger      │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│            │                   │                   │                        │
│            ▼                   ▼                   ▼                        │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                       FILE-BASED STATE STORE                          │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │ │
│  │  │ context-    │  │ subagent-   │  │ audit-      │  │ metrics-    │  │ │
│  │  │ {issue}.md  │  │ status.json │  │ log.json    │  │ {date}.json │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │ │
│  │  │ plan-       │  │ local-      │  │ learning-   │  │certificates/│  │ │
│  │  │ {issue}.md  │  │ issues.json │  │ {date}.json │  │ cert-*.json │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Complete Flow Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         COMPLETE EXECUTION FLOW                             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 1: ISSUE CREATION                                             │    │
│  │                                                                      │    │
│  │  Developer          validate-task.sh         GitHub                 │    │
│  │      │                     │                    │                   │    │
│  │      │──Create Issue───────────────────────────>│                   │    │
│  │      │                     │<──Webhook──────────│                   │    │
│  │      │                     │                    │                   │    │
│  │      │                     │──Validate Fields───│                   │    │
│  │      │                     │                    │                   │    │
│  │      │                     │──PASS? ────────────│                   │    │
│  │      │                     │  │                 │                   │    │
│  │      │<──Error + Guidance──│  │ YES             │                   │    │
│  │      │   (if FAIL)         │  │                 │                   │    │
│  │      │                     │  ▼                 │                   │    │
│  │      │                     │──Add to Backlog────>│                   │    │
│  │                                                                      │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│                                      ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 2: CONTEXT GENERATION                                         │    │
│  │                                                                      │    │
│  │  Agent X           generate-context.sh       .agent-context/        │    │
│  │      │                     │                      │                 │    │
│  │      │──Assign Issue───────│                      │                 │    │
│  │      │                     │                      │                 │    │
│  │      │                     │──Fetch Issue─────────│                 │    │
│  │      │                     │                      │                 │    │
│  │      │                     │──Determine Role──────│                 │    │
│  │      │                     │                      │                 │    │
│  │      │                     │──Load Skills─────────│                 │    │
│  │      │                     │  (label → skill map) │                 │    │
│  │      │                     │                      │                 │    │
│  │      │                     │──Fetch Deliverables──│                 │    │
│  │      │                     │  (PRD, ADR, Spec)    │                 │    │
│  │      │                     │                      │                 │    │
│  │      │                     │──Write context-{n}.md>│                 │    │
│  │      │                     │                      │                 │    │
│  │      │<──Context Ready─────│                      │                 │    │
│  │                                                                      │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│                                      ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 3: SUBAGENT SPAWN                                             │    │
│  │                                                                      │    │
│  │  Agent X           runSubagent            SubAgent-{N}              │    │
│  │      │                  │                      │                    │    │
│  │      │──Spawn───────────>│                      │                    │    │
│  │      │  (context path)   │                      │                    │    │
│  │      │                   │──Create Instance─────>│                    │    │
│  │      │                   │                      │                    │    │
│  │      │                   │──Load Context────────>│                    │    │
│  │      │                   │                      │                    │    │
│  │      │──Update Status───────────────────────────>│                    │    │
│  │      │  (subagent-status.json)                  │                    │    │
│  │                                                                      │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│                                      ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 4: PRE-FLIGHT VALIDATION                                      │    │
│  │                                                                      │    │
│  │  SubAgent          validate-pre-execution.sh       Result           │    │
│  │      │                     │                         │              │    │
│  │      │──Request Validation─>│                         │              │    │
│  │      │                     │                         │              │    │
│  │      │                     │──Check Context Complete──│              │    │
│  │      │                     │──Check Dependencies Met──│              │    │
│  │      │                     │──Check No Blockers───────│              │    │
│  │      │                     │                         │              │    │
│  │      │<─────────────────────│──PASS/FAIL─────────────│              │    │
│  │      │                     │                         │              │    │
│  │      │  IF PASS: Generate Plan                       │              │    │
│  │      │  IF FAIL: Return error + guidance             │              │    │
│  │                                                                      │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│                                      ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 5: EXECUTION                                                  │    │
│  │                                                                      │    │
│  │  SubAgent          Code/Docs           GitHub              Audit    │    │
│  │      │                 │                  │                  │      │    │
│  │      │──Write Code/Docs>│                  │                  │      │    │
│  │      │                 │                  │                  │      │    │
│  │      │                 │──Commit──────────>│                  │      │    │
│  │      │                 │                  │                  │      │    │
│  │      │──Log Action────────────────────────────────────────────>│      │    │
│  │      │                 │                  │                  │      │    │
│  │      │──Update Status──────────────────────>│                  │      │    │
│  │      │  (In Progress)  │                  │                  │      │    │
│  │                                                                      │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│                                      ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 6: HANDOFF VALIDATION                                         │    │
│  │                                                                      │    │
│  │  SubAgent          validate-handoff.sh         Result               │    │
│  │      │                     │                      │                 │    │
│  │      │──Request Handoff────>│                      │                 │    │
│  │      │                     │                      │                 │    │
│  │      │                     │──Check DoD Checklist──│                 │    │
│  │      │                     │  • Code committed     │                 │    │
│  │      │                     │  • Tests ≥80%         │                 │    │
│  │      │                     │  • Tests passing      │                 │    │
│  │      │                     │  • Docs updated       │                 │    │
│  │      │                     │  • No lint errors     │                 │    │
│  │      │                     │                      │                 │    │
│  │      │<─────────────────────│──PASS/FAIL──────────│                 │    │
│  │      │                     │                      │                 │    │
│  │      │  IF PASS: Update status to "In Review"     │                 │    │
│  │      │           Generate certificate              │                 │    │
│  │      │  IF FAIL: Return remediation guidance       │                 │    │
│  │                                                                      │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│                                      ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 7: COMPLETION                                                 │    │
│  │                                                                      │    │
│  │  Agent X           SubAgent            Certificate      Metrics     │    │
│  │      │                │                     │              │        │    │
│  │      │<──Complete─────│                     │              │        │    │
│  │      │                │                     │              │        │    │
│  │      │──Generate Certificate────────────────>│              │        │    │
│  │      │                │                     │              │        │    │
│  │      │──Update Metrics──────────────────────────────────────>│        │    │
│  │      │                │                     │              │        │    │
│  │      │──Terminate SubAgent                  │              │        │    │
│  │      │                │                     │              │        │    │
│  │      │──Remove from Status                  │              │        │    │
│  │                                                                      │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Git-Native Design

### 5.1 Core Concept: Git IS the Database

Instead of building custom state management, we leverage Git's built-in capabilities:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                      GIT-NATIVE STATE MANAGEMENT                            │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   NEED                    GIT FEATURE              BENEFIT                  │
│   ─────────────────────   ─────────────────────   ──────────────────────   │
│                                                                             │
│   Issue Tracking          Branches                 issue-456-jwt-auth       │
│                           git checkout -b          Natural grouping         │
│                                                                             │
│   Audit Log               Commit History           Already immutable!       │
│                           git log                  SHA-256 hashed           │
│                                                    Timestamped              │
│                                                                             │
│   Metadata                Git Notes                JSON attached to         │
│                           git notes add            commits/refs             │
│                           refs/notes/context       Queryable                │
│                                                                             │
│   SubAgent Isolation      Worktrees                REAL directories!        │
│                           git worktree add         ../worktrees/456/        │
│                                                    TRUE file isolation      │
│                                                                             │
│   Event Automation        Git Hooks                Instant triggers         │
│                           .git/hooks/              No polling needed        │
│                                                    Cross-platform           │
│                                                                             │
│   Status                  Branch Lifecycle         Created → Merged         │
│                           + Git Notes              + status metadata        │
│                                                                             │
│   Sync                    Push/Pull                Native!                  │
│                           git push/pull            Works with any remote    │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Branch Naming Convention

```
issue-{issue_number}-{short_description}

Examples:
  issue-456-jwt-auth-validation
  issue-457-user-dashboard-api
  issue-458-fix-login-error
  epic-100-authentication-system
```

### 5.3 Git Notes for Metadata

```bash
# Store context metadata on a branch tip
git notes --ref=context add -m '{"role":"engineer","skills":["#04","#02"],"status":"in_progress"}' issue-456-jwt

# Query metadata
git notes --ref=context show issue-456-jwt | jq .

# Update metadata
git notes --ref=context add -f -m '{"role":"engineer","skills":["#04","#02"],"status":"completed"}' issue-456-jwt
```

### 5.4 Directory Structure (Minimal)

```
Repository Root/
│
├── .agent-context/                    # Minimal runtime state
│   ├── state.json                     # Active worktrees only
│   └── context-{issue}.md             # Generated context files
│
├── .git/
│   ├── hooks/                         # Event automation
│   │   ├── prepare-commit-msg         # Auto-add issue reference
│   │   ├── pre-commit                 # Validate context exists
│   │   ├── post-commit                # Log activity
│   │   ├── pre-push                   # Handoff validation
│   │   └── post-merge                 # Certificate generation
│   │
│   └── refs/notes/
│       └── context                    # Metadata storage
│
├── ../worktrees/                      # SubAgent isolation (OUTSIDE repo)
│   ├── 456/                           # Worktree for issue 456
│   │   └── [complete repo checkout]
│   ├── 457/                           # Worktree for issue 457
│   │   └── [complete repo checkout]
│   └── 458/                           # Worktree for issue 458
│       └── [complete repo checkout]
│
└── .github/
    └── scripts/
        └── context-md/                # CLI implementation
            └── context-md.py          # Main CLI tool
```

---

## 6. SubAgent Isolation via Worktrees

### 6.1 Why Worktrees?

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        WORKTREE ISOLATION BENEFITS                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PROBLEM: Shared working directory                                          │
│  ═════════════════════════════════                                          │
│    ✗ SubAgent A modifies file.ts                                           │
│    ✗ SubAgent B sees A's uncommitted changes                               │
│    ✗ Context contamination!                                                │
│                                                                             │
│  SOLUTION: Git Worktrees                                                    │
│  ═══════════════════════                                                    │
│    ✓ Each SubAgent gets SEPARATE directory                                 │
│    ✓ ../worktrees/456/ ← SubAgent A (PM)                                   │
│    ✓ ../worktrees/457/ ← SubAgent B (Engineer)                             │
│    ✓ TRUE file system isolation                                            │
│    ✓ Can work in parallel without conflicts                                │
│    ✓ Share the same .git (efficient)                                       │
│                                                                             │
│  WORKFLOW:                                                                  │
│    1. context-md subagent spawn 456                                        │
│    2. Creates branch: issue-456-jwt                                        │
│    3. Creates worktree: ../worktrees/456/                                  │
│    4. SubAgent operates in that directory                                  │
│    5. On completion: merge branch, remove worktree                         │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Worktree Lifecycle

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        WORKTREE LIFECYCLE                                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CREATE                                                                     │
│  ──────                                                                     │
│    $ context-md subagent spawn 456 --role engineer                         │
│                                                                             │
│    Internally:                                                              │
│      1. git checkout -b issue-456-jwt-auth                                 │
│      2. git worktree add ../worktrees/456 issue-456-jwt-auth               │
│      3. Update .agent-context/state.json                                   │
│      4. Generate context file in worktree                                  │
│                                                                             │
│  OPERATE                                                                    │
│  ───────                                                                    │
│    SubAgent works in ../worktrees/456/                                     │
│    All file operations isolated to that directory                          │
│    Commits go to issue-456-jwt-auth branch                                 │
│                                                                             │
│  COMPLETE                                                                   │
│  ────────                                                                   │
│    $ context-md subagent complete 456                                      │
│                                                                             │
│    Internally:                                                              │
│      1. pre-push hook validates DoD                                        │
│      2. git push origin issue-456-jwt-auth                                 │
│      3. git worktree remove ../worktrees/456                               │
│      4. Update state.json                                                  │
│      5. (GitHub mode) Create PR or update status                           │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 State File Schema

The ONLY runtime state file needed:

```json
{
  "$schema": "https://context.md/schemas/state-v1.json",
  "version": "1.0",
  "mode": "local",
  "worktrees": [
    {
      "issue": 456,
      "branch": "issue-456-jwt-auth",
      "path": "../worktrees/456",
      "role": "engineer",
      "created_at": "2026-01-29T10:00:00Z"
    }
  ],
  "github": {
    "enabled": false,
    "last_sync": null
  }
}
```

---

## 7. Hook-Based Automation

### 7.1 Git Hooks Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        GIT HOOKS AUTOMATION                                 │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  HOOK                  TRIGGER                    ACTION                    │
│  ────────────────────  ───────────────────────   ──────────────────────    │
│                                                                             │
│  prepare-commit-msg    Before commit message      Auto-add issue ref        │
│                        editor opens               from branch name          │
│                                                                             │
│  pre-commit            Before commit created      Validate context exists   │
│                                                   Run linters               │
│                                                   Check for secrets         │
│                                                                             │
│  post-commit           After commit created       Update Git Notes          │
│                                                   (activity timestamp)      │
│                                                   Update metrics            │
│                                                                             │
│  pre-push              Before push to remote      Handoff validation        │
│                                                   DoD checklist             │
│                                                   Block if incomplete       │
│                                                                             │
│  post-merge            After merge completed      Generate certificate      │
│                                                   Update metrics            │
│                                                   Cleanup worktree          │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Hook Implementations

#### prepare-commit-msg
```bash
#!/bin/bash
# .git/hooks/prepare-commit-msg
# Auto-add issue reference from branch name

COMMIT_MSG_FILE=$1
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Extract issue number from branch name (e.g., issue-456-jwt → 456)
if [[ $BRANCH =~ ^issue-([0-9]+) ]]; then
    ISSUE_NUM="${BASH_REMATCH[1]}"
    # Only add if not already present
    if ! grep -q "#$ISSUE_NUM" "$COMMIT_MSG_FILE"; then
        sed -i.bak "1s/$/ (#$ISSUE_NUM)/" "$COMMIT_MSG_FILE"
    fi
fi
```

#### pre-push (Handoff Validation)
```bash
#!/bin/bash
# .git/hooks/pre-push
# Validate Definition of Done before push

BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Only validate issue branches
if [[ ! $BRANCH =~ ^issue-([0-9]+) ]]; then
    exit 0  # Not an issue branch, allow push
fi

ISSUE_NUM="${BASH_REMATCH[1]}"

# Run DoD validation
context-md validate $ISSUE_NUM --dod

if [ $? -ne 0 ]; then
    echo "❌ Handoff validation failed. Fix issues before pushing."
    echo "   Run: context-md validate $ISSUE_NUM --dod --verbose"
    exit 1
fi

echo "✅ DoD validation passed"
exit 0
```

---

## 8. Mode Selection

### 8.1 Operating Modes

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          MODE SELECTION                                     │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MODE 1: LOCAL-ONLY                                                         │
│  ══════════════════                                                         │
│    • Works without any network connection                                   │
│    • Issues = Git branches                                                  │
│    • Status = Git notes                                                     │
│    • No GitHub required at all                                              │
│                                                                             │
│    Use case: Air-gapped environments, offline work, privacy                │
│                                                                             │
│  MODE 2: GITHUB-CONNECTED                                                   │
│  ════════════════════════                                                   │
│    • Full sync with GitHub Issues and Projects V2                          │
│    • Branches mirror GitHub Issues                                          │
│    • PRs created on handoff                                                │
│    • Status synced to Projects board                                       │
│                                                                             │
│    Use case: Team collaboration, full GitHub workflow                      │
│                                                                             │
│  MODE 3: HYBRID                                                             │
│  ═════════════                                                              │
│    • Work locally (branches, worktrees, hooks)                             │
│    • Periodic sync to GitHub                                                │
│    • Local issues → GitHub issues on sync                                  │
│    • Push triggers GitHub sync                                              │
│                                                                             │
│    Use case: Intermittent connectivity, prefer local + cloud backup        │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Mode Configuration

```bash
# Set mode during initialization
context-md init --mode local
context-md init --mode github
context-md init --mode hybrid

# Check current mode
context-md config mode

# Switch mode
context-md config mode github
```

---

## 9. CLI Interface

### 9.1 Command Overview

```
context-md - Runtime context management for AI agents

USAGE:
    context-md <command> [options]

COMMANDS:
    init            Initialize Context.md in repository
    issue           Create/manage local issues (local mode)
    context         Generate context for an issue
    subagent        Manage SubAgent worktrees
    validate        Run validation checks
    status          Show current status
    dashboard       Display CLI dashboard
    metrics         Show/export metrics
    sync            Sync with GitHub (hybrid/github mode)
    config          View/modify configuration

GLOBAL OPTIONS:
    --verbose, -v   Verbose output
    --quiet, -q     Suppress non-error output
    --help, -h      Show help
    --version       Show version
```

### 9.2 Core Commands

#### init
```bash
context-md init [--mode local|github|hybrid]

Initialize Context.md in current repository:
  • Creates .agent-context/ directory
  • Installs Git hooks
  • Sets up Git notes refs
  • Configures mode
```

#### issue (Local Mode)
```bash
context-md issue create --title "Add JWT validation" --type story
context-md issue list [--status in_progress]
context-md issue show 456
context-md issue close 456

# Creates branch: issue-456-add-jwt-validation
# Stores metadata in Git notes
```

#### context
```bash
context-md context generate 456 [--output path]
context-md context show 456
context-md context refresh 456

# Generates .agent-context/context-456.md with:
# - Role instructions
# - Issue details
# - Relevant skills
# - Dependencies
# - References
```

#### subagent
```bash
context-md subagent spawn 456 --role engineer
context-md subagent list
context-md subagent status 456
context-md subagent complete 456

# Creates worktree at ../worktrees/456/
# Tracks in .agent-context/state.json
```

#### validate
```bash
context-md validate 456 --task        # Validate task quality
context-md validate 456 --pre-exec    # Pre-flight validation
context-md validate 456 --dod         # Definition of Done
context-md validate 456 --all         # All validations

# Exit codes:
#   0 = Pass
#   1 = Fail with remediation guidance
#   2 = Error
```

#### status
```bash
context-md status

Output:
┌─────────────────────────────────────────────────────────┐
│ Context.md Status                                        │
├─────────────────────────────────────────────────────────┤
│ Mode: local                                              │
│ Active Worktrees: 2                                      │
│                                                          │
│ Issue 456 (Engineer) - In Progress                       │
│   Branch: issue-456-jwt-auth                             │
│   Path: ../worktrees/456                                 │
│   Last commit: 2h ago                                    │
│                                                          │
│ Issue 457 (Reviewer) - In Review                         │
│   Branch: issue-457-user-api                             │
│   Path: ../worktrees/457                                 │
│   Last commit: 30m ago                                   │
└─────────────────────────────────────────────────────────┘
```

#### sync (Hybrid/GitHub Mode)
```bash
context-md sync [--push] [--pull]

# Push: Local → GitHub
#   - Create GitHub issues from local branches
#   - Update GitHub Projects status
#   - Push branches to remote
#
# Pull: GitHub → Local
#   - Fetch new GitHub issues as branches
#   - Update local notes with GitHub status
```

---

## 10. Data Architecture

### 5.1 Directory Structure

```
Repository Root/
│
├── .agent-context/                    # Runtime state (git-ignored)
│   ├── context-{issue}.md             # Per-task context files
│   ├── plan-{issue}.md                # Execution plans
│   ├── analysis-{issue}.json          # Code analysis results
│   ├── subagent-status.json           # Active SubAgent tracking
│   ├── local-issues.json              # Offline issue storage
│   ├── local-status.json              # Offline status
│   ├── audit-log.json                 # Append-only action log
│   ├── metrics-{YYYY-MM-DD}.json      # Daily metrics
│   ├── learning-{YYYY-MM}.json        # Monthly learning reports
│   └── certificates/                  # Completion certificates
│       └── cert-{issue}.json
│
├── .github/
│   ├── scripts/                       # Automation scripts
│   │   ├── context-manager/           # Core Context.md scripts
│   │   │   ├── generate-context.sh    # Context generation (Bash)
│   │   │   ├── generate-context.ps1   # Context generation (PowerShell)
│   │   │   ├── validate-task.sh       # Task validation
│   │   │   ├── validate-task.ps1
│   │   │   ├── validate-pre-exec.sh   # Pre-flight validation
│   │   │   ├── validate-pre-exec.ps1
│   │   │   ├── validate-handoff.sh    # Handoff validation
│   │   │   ├── validate-handoff.ps1
│   │   │   ├── detect-stuck.sh        # Stuck issue detection
│   │   │   ├── detect-stuck.ps1
│   │   │   ├── analyze-learning.sh    # Learning analysis
│   │   │   ├── analyze-learning.ps1
│   │   │   ├── sync-to-github.sh      # Local → GitHub sync
│   │   │   ├── sync-to-github.ps1
│   │   │   ├── dashboard-cli.sh       # CLI dashboard
│   │   │   ├── dashboard-cli.ps1
│   │   │   ├── audit-logger.sh        # Audit logging
│   │   │   └── lib/                   # Shared libraries
│   │   │       ├── common.sh          # Common functions
│   │   │       ├── common.ps1
│   │   │       ├── github-api.sh      # GitHub API helpers
│   │   │       ├── github-api.ps1
│   │   │       ├── json-utils.sh      # JSON manipulation
│   │   │       └── json-utils.ps1
│   │   └── validate-handoff.sh        # Existing (enhanced)
│   │
│   ├── workflows/                     # GitHub Actions
│   │   ├── context-manager.yml        # Main orchestration
│   │   ├── stuck-detection.yml        # Cron: every 30 min
│   │   ├── learning-analysis.yml      # Cron: monthly
│   │   ├── crash-recovery.yml         # Cron: every 15 min
│   │   └── metrics-collection.yml     # Cron: daily
│   │
│   ├── templates/                     # Document templates
│   │   ├── PLAN-TEMPLATE.md           # Execution plan template
│   │   ├── CONTEXT-TEMPLATE.md        # Context file template
│   │   └── ... (existing)
│   │
│   ├── ISSUE_TEMPLATE/
│   │   ├── story.yml                  # Enhanced with validation
│   │   ├── bug.yml                    # Enhanced
│   │   └── feature.yml                # Enhanced
│   │
│   └── agents/                        # Agent definitions
│       └── ... (existing)
│
├── docs/
│   ├── dashboard/                     # Web dashboard (GitHub Pages)
│   │   ├── index.html                 # Dashboard home
│   │   ├── trends.html                # Metrics trends
│   │   ├── agents.html                # Agent status
│   │   ├── quality.html               # Quality metrics
│   │   ├── css/
│   │   │   └── dashboard.css
│   │   └── js/
│   │       ├── dashboard.js           # Dashboard logic
│   │       └── charts.js              # Chart rendering
│   │
│   ├── prd/
│   │   └── PRD-CONTEXT-MD.md
│   ├── adr/
│   │   └── ADR-CONTEXT-MD.md
│   ├── specs/
│   │   └── SPEC-CONTEXT-MD.md
│   └── architecture/
│       └── ARCHITECTURE-CONTEXT-MD.md  # This document
│
└── .gitignore                         # Updated to exclude .agent-context/
```

### 5.2 Component Specifications

#### 5.2.1 Context Generator

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         CONTEXT GENERATOR                                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT:                                                                     │
│    • Issue number                                                           │
│    • GitHub token (env var)                                                 │
│                                                                             │
│  PROCESS:                                                                   │
│    1. Fetch issue from GitHub API                                           │
│    2. Extract metadata (type, labels, assignee, status)                    │
│    3. Determine role from issue type                                        │
│    4. Load role instructions from .github/agents/{role}.agent.md            │
│    5. Map labels to skills using SKILL_ROUTING table                        │
│    6. Load complete skill files (NEVER truncate)                           │
│    7. Fetch previous deliverables (PRD, ADR, Spec)                         │
│    8. Parse references from issue body                                     │
│    9. Calculate token count                                                 │
│   10. Validate size (warn >100K, block >150K)                              │
│   11. Write context file to .agent-context/context-{issue}.md              │
│   12. Log generation to audit                                              │
│                                                                             │
│  OUTPUT:                                                                    │
│    • .agent-context/context-{issue}.md                                      │
│    • Exit code (0=success, 1=warning, 2=error)                             │
│                                                                             │
│  SKILL ROUTING TABLE:                                                       │
│    ┌─────────────┬─────────────────────────────────────────┐               │
│    │ Label       │ Skills Loaded                           │               │
│    ├─────────────┼─────────────────────────────────────────┤               │
│    │ api         │ #09 (API), #04 (Security), #02 (Test),  │               │
│    │             │ #11 (Docs)                              │               │
│    │ database    │ #06 (DB), #04 (Security), #02 (Test)    │               │
│    │ security    │ #04 (Security), #10 (Config), #02,      │               │
│    │             │ #13 (Type), #15 (Logging)               │               │
│    │ frontend    │ #21 (Frontend), #22 (React), #02, #11   │               │
│    │ bug         │ #03 (Error), #02 (Test), #15 (Logging)  │               │
│    │ performance │ #05 (Perf), #06 (DB), #02, #15          │               │
│    │ ai          │ #17 (AI Agent), #04 (Security)          │               │
│    │ default     │ #02 (Test), #04 (Security), #11 (Docs)  │               │
│    └─────────────┴─────────────────────────────────────────┘               │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

#### 5.2.2 Task Validator

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           TASK VALIDATOR                                    │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT:                                                                     │
│    • Issue number or issue JSON                                             │
│                                                                             │
│  VALIDATION RULES:                                                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ RULE 1: REFERENCES FIELD (Required for code tasks)                   │   │
│  │   ✓ Field exists                                                     │   │
│  │   ✓ Contains valid file paths                                        │   │
│  │   ✓ Files exist in repository                                        │   │
│  │   ERROR: "Missing References field. Add code files to modify."       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ RULE 2: DOCUMENTATION FIELD (Required for Features/Stories)          │   │
│  │   ✓ Field exists                                                     │   │
│  │   ✓ Contains links to PRD/ADR/Spec                                  │   │
│  │   ✓ Linked documents exist                                           │   │
│  │   ERROR: "Missing Documentation field. Link PRD/ADR/Spec."          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ RULE 3: DEPENDENCIES (Structured format required)                    │   │
│  │   ✓ Each dependency has: provides, integration_point, verification   │   │
│  │   ✗ Reject vague: "Depends on #123"                                 │   │
│  │   ERROR: "Dependencies must include provides/integration/verify."    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ RULE 4: ACCEPTANCE CRITERIA (Specific and testable)                  │   │
│  │   ✓ At least one criterion                                           │   │
│  │   ✓ Criteria are measurable                                          │   │
│  │   ✗ Reject vague: "Works correctly"                                 │   │
│  │   ERROR: "Acceptance criteria must be specific and testable."        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ RULE 5: STRANGER TEST (No implicit knowledge)                        │   │
│  │   ✗ Detect phrases: "as discussed", "like before", "you know"       │   │
│  │   ✗ Detect undefined acronyms                                        │   │
│  │   ✗ Detect references without context                                │   │
│  │   ERROR: "Task contains implicit knowledge. Add explicit details."   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  OUTPUT:                                                                    │
│    • Exit code (0=valid, 1=invalid)                                        │
│    • JSON report with pass/fail per rule                                   │
│    • Remediation guidance for failures                                     │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

#### 5.2.3 Handoff Validator

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          HANDOFF VALIDATOR                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT:                                                                     │
│    • Issue number                                                           │
│    • Current role (pm, architect, engineer, reviewer)                      │
│                                                                             │
│  DEFINITION OF DONE CHECKLISTS:                                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PRODUCT MANAGER                                                      │   │
│  │   □ PRD created at docs/prd/PRD-{issue}.md                          │   │
│  │   □ Child issues created (Features/Stories)                          │   │
│  │   □ Acceptance criteria defined for each                             │   │
│  │   □ Success metrics specified                                        │   │
│  │   □ Timeline with phases documented                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ARCHITECT                                                            │   │
│  │   □ ADR created at docs/adr/ADR-{issue}.md                          │   │
│  │   □ Tech Spec at docs/specs/SPEC-{issue}.md                         │   │
│  │   □ Options with pros/cons documented                                │   │
│  │   □ Decision rationale clear                                         │   │
│  │   □ NO CODE EXAMPLES (diagrams only)                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ENGINEER                                                             │   │
│  │   □ Code committed and pushed                                        │   │
│  │   □ Tests written (≥80% coverage)                                   │   │
│  │   □ Tests passing in CI                                              │   │
│  │   □ Documentation updated (README, inline)                           │   │
│  │   □ No compiler warnings or linter errors                            │   │
│  │   □ Security scan passed                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ REVIEWER                                                             │   │
│  │   □ Review document at docs/reviews/REVIEW-{issue}.md               │   │
│  │   □ All checklist items verified                                     │   │
│  │   □ Approval or rejection decision documented                        │   │
│  │   □ Feedback provided for rejections                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  OUTPUT:                                                                    │
│    • Exit code (0=pass, 1=fail)                                            │
│    • Detailed checklist results                                            │
│    • Certificate (if pass)                                                 │
│    • Remediation guidance (if fail)                                        │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

#### 5.2.4 Stuck Detector

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           STUCK DETECTOR                                    │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TRIGGER: GitHub Actions cron (every 30 minutes)                           │
│                                                                             │
│  ALGORITHM:                                                                 │
│                                                                             │
│    1. Query GitHub for issues with Status = "In Progress"                  │
│                                                                             │
│    2. For each issue:                                                       │
│       │                                                                     │
│       ├─► Get last commit timestamp (from linked branch)                   │
│       ├─► Get last comment timestamp                                        │
│       ├─► Get last label change timestamp                                  │
│       │                                                                     │
│       └─► last_activity = MAX(commit, comment, label)                      │
│                                                                             │
│    3. Calculate hours_stuck = NOW - last_activity                          │
│                                                                             │
│    4. Apply thresholds:                                                     │
│       ┌─────────────────────────────────────────────────────────────┐      │
│       │ Issue Type  │ Threshold │ Override Field                   │      │
│       ├─────────────┼───────────┼──────────────────────────────────┤      │
│       │ type:bug    │ 12 hours  │ stuck_threshold: X               │      │
│       │ type:story  │ 24 hours  │ stuck_threshold: X               │      │
│       │ type:feature│ 48 hours  │ stuck_threshold: X               │      │
│       │ type:epic   │ 72 hours  │ stuck_threshold: X               │      │
│       └─────────────┴───────────┴──────────────────────────────────┘      │
│                                                                             │
│    5. If hours_stuck > threshold:                                          │
│       │                                                                     │
│       ├─► Create escalation issue:                                         │
│       │     Title: "⚠️ Stuck: Issue #{N} for {hours}h"                     │
│       │     Labels: needs:help, priority:p1                                │
│       │     Assignee: @AgentX, @original_assignee                          │
│       │                                                                     │
│       ├─► Post comment to original issue:                                  │
│       │     "⚠️ This issue has been stuck for {hours}h.                   │
│       │      Last activity: {timestamp}                                    │
│       │      Escalation: #{escalation_id}                                 │
│       │      Please update status or request help."                        │
│       │                                                                     │
│       └─► Log to audit-log.json                                            │
│                                                                             │
│  OUTPUT:                                                                    │
│    • Escalation issues created                                             │
│    • Comments posted                                                        │
│    • Detection summary in workflow logs                                    │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Data Architecture

### 6.1 File Schemas

#### Context File (Markdown)

```markdown
# Context - Issue #{issue_number}

## Metadata
| Field | Value |
|-------|-------|
| Generated | {ISO timestamp} |
| Issue | #{issue_number} |
| Type | {story|bug|feature|epic} |
| Role | {pm|architect|engineer|reviewer|ux} |
| Token Count | {count} |
| Skills | {#XX, #YY, ...} |

---

## Role Instructions

{Complete content from .github/agents/{role}.agent.md}

---

## Issue Details

### Title
{Issue title}

### Description
{Full issue body/description}

### Labels
`{label1}`, `{label2}`, ...

### Assignee
{Assignee username}

### Status
{GitHub Projects V2 Status}

---

## Dependencies

### #{dep_number} - {dep_title}
| Field | Value |
|-------|-------|
| **Provides** | {What this dependency provides} |
| **Integration** | {How to integrate} |
| **Verification** | {How to verify it's ready} |

---

## Acceptance Criteria

- [ ] {Criterion 1}
- [ ] {Criterion 2}
- [ ] {Criterion 3}

---

## Previous Deliverables

### PRD
- **Path**: docs/prd/PRD-{epic}.md
- **Summary**: {Key requirements relevant to this task}

### ADR
- **Path**: docs/adr/ADR-{feature}.md
- **Summary**: {Key decisions relevant to this task}

### Tech Spec
- **Path**: docs/specs/SPEC-{feature}.md
- **Summary**: {Key technical details}

---

## Relevant Skills

### Skill #XX: {Skill Name}

{Complete skill content - NEVER truncated}

### Skill #YY: {Skill Name}

{Complete skill content - NEVER truncated}

---

## References

### Code Files
- `{path/to/file1.ts}` - {purpose}
- `{path/to/file2.ts}` - {purpose}

### Documentation
- `{path/to/doc.md}` - {purpose}

---

## Execution Checklist

- [ ] Review this context completely
- [ ] Generate execution plan (plan-{issue}.md)
- [ ] Pass pre-flight validation
- [ ] Execute work
- [ ] Pass handoff validation
- [ ] Update status

---

*Generated by Context.md v1.0*
```

#### SubAgent Status (JSON)

```json
{
  "$schema": "https://context.md/schemas/subagent-status-v1.json",
  "last_updated": "2026-01-29T14:35:00Z",
  "subagents": [
    {
      "id": "subagent-456",
      "issue": 456,
      "issue_title": "Add JWT validation",
      "role": "engineer",
      "status": "in_progress",
      "phase": "coding",
      "started_at": "2026-01-29T10:00:00Z",
      "last_activity": "2026-01-29T14:35:00Z",
      "context_file": ".agent-context/context-456.md",
      "plan_file": ".agent-context/plan-456.md",
      "branch": "issue-456-jwt-validation",
      "commits": 3,
      "errors": [],
      "warnings": [],
      "metrics": {
        "files_changed": 5,
        "lines_added": 234,
        "lines_removed": 12,
        "tests_added": 8,
        "test_coverage": 82
      }
    }
  ],
  "summary": {
    "total_active": 3,
    "by_role": {
      "pm": 0,
      "architect": 1,
      "engineer": 2,
      "reviewer": 0,
      "ux": 0
    },
    "by_status": {
      "planning": 1,
      "coding": 1,
      "testing": 0,
      "reviewing": 1
    },
    "completed_today": 5,
    "stuck": 0,
    "failed": 0
  }
}
```

#### Audit Log (JSON)

```json
{
  "$schema": "https://context.md/schemas/audit-log-v1.json",
  "version": "1.0",
  "entries": [
    {
      "id": "audit-20260129143500-001",
      "timestamp": "2026-01-29T14:35:00.123Z",
      "event_type": "context_generated",
      "agent": "agent-x",
      "subagent_id": null,
      "issue": 456,
      "details": {
        "context_file": ".agent-context/context-456.md",
        "token_count": 62000,
        "skills_loaded": ["#04", "#02", "#09", "#11"],
        "generation_time_ms": 2340
      },
      "result": "success",
      "error": null
    },
    {
      "id": "audit-20260129143505-002",
      "timestamp": "2026-01-29T14:35:05.456Z",
      "event_type": "subagent_spawned",
      "agent": "agent-x",
      "subagent_id": "subagent-456",
      "issue": 456,
      "details": {
        "role": "engineer",
        "context_file": ".agent-context/context-456.md"
      },
      "result": "success",
      "error": null
    },
    {
      "id": "audit-20260129183000-003",
      "timestamp": "2026-01-29T18:30:00.789Z",
      "event_type": "handoff_validated",
      "agent": "engineer",
      "subagent_id": "subagent-456",
      "issue": 456,
      "details": {
        "checklist": {
          "code_committed": true,
          "tests_coverage": 85,
          "tests_passing": true,
          "docs_updated": true,
          "lint_errors": 0,
          "security_scan": "passed"
        },
        "certificate_id": "CERT-456-2026012918"
      },
      "result": "success",
      "error": null
    }
  ]
}
```

#### Metrics (JSON)

```json
{
  "$schema": "https://context.md/schemas/metrics-v1.json",
  "date": "2026-01-29",
  "period": "daily",
  "generated_at": "2026-01-30T00:00:00Z",
  
  "success_metrics": {
    "total_issues_completed": 12,
    "success_rate": 91.7,
    "handoff_success_rate": 83.3,
    "first_attempt_pass_rate": 75.0,
    "post_merge_bugs": 1
  },
  
  "efficiency_metrics": {
    "avg_context_size_tokens": 58000,
    "avg_task_duration_hours": 4.2,
    "avg_revision_cycles": 1.2,
    "total_tokens_used": 696000,
    "context_generations": 15
  },
  
  "quality_metrics": {
    "validation_pass_rate": {
      "task_creation": 88.0,
      "pre_execution": 92.0,
      "handoff": 83.3
    },
    "avg_test_coverage": 84.2,
    "lint_error_rate": 1.8,
    "security_issues_found": 0
  },
  
  "health_metrics": {
    "stuck_issues": {
      "detected": 2,
      "resolved": 2,
      "avg_stuck_hours": 18.5
    },
    "crash_recoveries": 1,
    "failed_workflows": 1
  },
  
  "agent_metrics": {
    "pm": {
      "issues_completed": 2,
      "avg_duration_hours": 3.5,
      "success_rate": 100
    },
    "architect": {
      "issues_completed": 2,
      "avg_duration_hours": 5.0,
      "success_rate": 100
    },
    "engineer": {
      "issues_completed": 6,
      "avg_duration_hours": 4.5,
      "success_rate": 83.3
    },
    "reviewer": {
      "issues_completed": 2,
      "avg_duration_hours": 2.0,
      "success_rate": 100
    }
  },
  
  "failure_analysis": {
    "top_failure_types": [
      {
        "type": "missing_tests",
        "count": 2,
        "issues": [445, 449]
      },
      {
        "type": "lint_errors",
        "count": 1,
        "issues": [451]
      }
    ],
    "common_patterns": [
      "Tests not written for edge cases",
      "Missing null checks in validation"
    ]
  }
}
```

---

## 7. Integration Architecture

### 7.1 GitHub Integration

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          GITHUB INTEGRATION                                 │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ GITHUB ISSUES                                                        │   │
│  │                                                                       │   │
│  │   API: REST (gh issue list, gh issue view, gh issue create)         │   │
│  │                                                                       │   │
│  │   Operations:                                                         │   │
│  │     • Fetch issue metadata (title, body, labels, assignee)          │   │
│  │     • Create escalation issues                                       │   │
│  │     • Add comments to issues                                         │   │
│  │     • Update labels                                                  │   │
│  │                                                                       │   │
│  │   Rate Limit: 5000 requests/hour                                     │   │
│  │   Mitigation: Batch requests, cache results                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ GITHUB PROJECTS V2                                                   │   │
│  │                                                                       │   │
│  │   API: GraphQL (projectV2 queries and mutations)                    │   │
│  │                                                                       │   │
│  │   Operations:                                                         │   │
│  │     • Query issue status                                             │   │
│  │     • Update status field (Backlog → In Progress → Done)            │   │
│  │     • Query project items                                            │   │
│  │                                                                       │   │
│  │   GraphQL Query Example:                                             │   │
│  │   query {                                                            │   │
│  │     node(id: "PROJECT_ID") {                                         │   │
│  │       ... on ProjectV2 {                                             │   │
│  │         items(first: 100) {                                          │   │
│  │           nodes {                                                    │   │
│  │             fieldValueByName(name: "Status") {                       │   │
│  │               ... on ProjectV2ItemFieldSingleSelectValue {           │   │
│  │                 name                                                 │   │
│  │               }                                                      │   │
│  │             }                                                        │   │
│  │           }                                                          │   │
│  │         }                                                            │   │
│  │       }                                                              │   │
│  │     }                                                                │   │
│  │   }                                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ GITHUB ACTIONS                                                       │   │
│  │                                                                       │   │
│  │   Workflows:                                                         │   │
│  │     • stuck-detection.yml (cron: */30 * * * *)                      │   │
│  │     • crash-recovery.yml (cron: */15 * * * *)                       │   │
│  │     • learning-analysis.yml (cron: 0 0 1 * *)                       │   │
│  │     • metrics-collection.yml (cron: 0 0 * * *)                      │   │
│  │                                                                       │   │
│  │   Triggers:                                                          │   │
│  │     • workflow_dispatch (manual)                                     │   │
│  │     • issues.opened (task validation)                                │   │
│  │     • pull_request.opened (handoff validation)                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ GITHUB PAGES                                                         │   │
│  │                                                                       │   │
│  │   URL: https://{org}.github.io/{repo}/dashboard/                    │   │
│  │                                                                       │   │
│  │   Deployment:                                                        │   │
│  │     • Static HTML/CSS/JS in docs/dashboard/                         │   │
│  │     • Auto-deployed on push to main                                 │   │
│  │     • Fetches metrics from GitHub API                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 VS Code Integration

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          VS CODE INTEGRATION                                │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ SUBAGENT SPAWNING (runSubagent tool)                                │   │
│  │                                                                       │   │
│  │   Usage:                                                             │   │
│  │   runSubagent({                                                      │   │
│  │     agentName: "Engineer",                                          │   │
│  │     prompt: "Execute Issue #456 using context at                    │   │
│  │              .agent-context/context-456.md",                        │   │
│  │     description: "Implement JWT validation"                          │   │
│  │   })                                                                 │   │
│  │                                                                       │   │
│  │   Isolation:                                                         │   │
│  │     • Each SubAgent runs in separate context window                 │   │
│  │     • No shared memory between SubAgents                             │   │
│  │     • Context file is only accessible resource                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ FILE OPERATIONS (read_file, create_file, replace_string)            │   │
│  │                                                                       │   │
│  │   Used for:                                                          │   │
│  │     • Reading context files                                          │   │
│  │     • Creating execution plans                                       │   │
│  │     • Updating status files                                          │   │
│  │     • Writing audit logs                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ TERMINAL OPERATIONS (run_in_terminal)                                │   │
│  │                                                                       │   │
│  │   Used for:                                                          │   │
│  │     • Running validation scripts                                     │   │
│  │     • Executing tests                                                │   │
│  │     • Running linters                                                │   │
│  │     • Git operations                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ TODO MANAGEMENT (manage_todo_list)                                   │   │
│  │                                                                       │   │
│  │   Used for:                                                          │   │
│  │     • Tracking execution steps within session                        │   │
│  │     • Progress visibility                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Deployment Architecture

### 8.1 Deployment Model

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT ARCHITECTURE                             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                        ┌─────────────────────┐                              │
│                        │    GITHUB REPO      │                              │
│                        │                     │                              │
│                        │  • Scripts          │                              │
│                        │  • Workflows        │                              │
│                        │  • Templates        │                              │
│                        │  • Dashboard        │                              │
│                        └──────────┬──────────┘                              │
│                                   │                                         │
│              ┌────────────────────┼────────────────────┐                    │
│              │                    │                    │                    │
│              ▼                    ▼                    ▼                    │
│  ┌───────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │ DEVELOPER MACHINE │  │  GITHUB ACTIONS │  │  GITHUB PAGES   │           │
│  │                   │  │                 │  │                 │           │
│  │ • VS Code         │  │ • Cron Jobs     │  │ • Web Dashboard │           │
│  │ • Scripts (local) │  │ • Webhooks      │  │ • Metrics View  │           │
│  │ • .agent-context/ │  │ • Automation    │  │                 │           │
│  │                   │  │                 │  │                 │           │
│  └───────────────────┘  └─────────────────┘  └─────────────────┘           │
│                                                                             │
│  NO EXTERNAL SERVICES REQUIRED                                              │
│  ════════════════════════════════                                           │
│    ✓ No database servers                                                    │
│    ✓ No message queues                                                      │
│    ✓ No cloud functions                                                     │
│    ✓ No Docker containers                                                   │
│    ✓ Everything runs on GitHub or local machine                            │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Installation Process

```bash
# 1. Clone or update repository
git pull origin main

# 2. Run installation script
./install-context-md.sh  # or install-context-md.ps1 on Windows

# Installation script does:
#   • Creates .agent-context/ directory
#   • Updates .gitignore
#   • Installs GitHub Actions workflows
#   • Updates issue templates
#   • Validates prerequisites (git, gh cli)

# 3. Configure (one-time)
gh auth login  # If not already authenticated

# 4. Enable GitHub Pages (manual)
#   Settings → Pages → Source: main/docs
```

---

## 9. Security Architecture

### 9.1 Security Boundaries

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          SECURITY BOUNDARIES                                │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ BOUNDARY 1: SUBAGENT ISOLATION                                       │   │
│  │                                                                       │   │
│  │   Each SubAgent can ONLY access:                                     │   │
│  │     ✓ Its own context file (.agent-context/context-{N}.md)          │   │
│  │     ✓ Its own plan file (.agent-context/plan-{N}.md)                │   │
│  │     ✓ Files explicitly listed in References                          │   │
│  │     ✓ Public repository files                                        │   │
│  │                                                                       │   │
│  │   Each SubAgent CANNOT access:                                       │   │
│  │     ✗ Other SubAgents' context files                                │   │
│  │     ✗ Environment variables with secrets                             │   │
│  │     ✗ .git/config (credentials)                                     │   │
│  │     ✗ Files not in References                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ BOUNDARY 2: SECRETS MANAGEMENT                                       │   │
│  │                                                                       │   │
│  │   Secrets MUST be stored in:                                         │   │
│  │     ✓ GitHub Secrets (for Actions)                                   │   │
│  │     ✓ Environment variables (for local)                              │   │
│  │     ✓ Azure Key Vault (optional)                                     │   │
│  │                                                                       │   │
│  │   Secrets MUST NOT appear in:                                        │   │
│  │     ✗ Context files                                                  │   │
│  │     ✗ Audit logs                                                     │   │
│  │     ✗ Metrics files                                                  │   │
│  │     ✗ Dashboard displays                                             │   │
│  │     ✗ Git history                                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ BOUNDARY 3: AUDIT TRAIL INTEGRITY                                    │   │
│  │                                                                       │   │
│  │   Audit logs are:                                                    │   │
│  │     ✓ Append-only (no modifications/deletions)                      │   │
│  │     ✓ Hash-chained (tamper-evident)                                 │   │
│  │     ✓ Timestamped (UTC)                                              │   │
│  │                                                                       │   │
│  │   Audit logs are sanitized:                                          │   │
│  │     ✓ No secrets in details                                          │   │
│  │     ✓ No PII beyond usernames                                        │   │
│  │     ✓ No full file contents                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ BOUNDARY 4: WEB DASHBOARD                                            │   │
│  │                                                                       │   │
│  │   Dashboard is:                                                      │   │
│  │     ✓ Read-only (no write operations)                               │   │
│  │     ✓ Public data only (no secrets)                                 │   │
│  │     ✓ Static HTML (no server-side code)                             │   │
│  │                                                                       │   │
│  │   Dashboard cannot:                                                  │   │
│  │     ✗ Modify issues                                                  │   │
│  │     ✗ Access private repositories                                    │   │
│  │     ✗ Execute code                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Implementation Plan

### 11.1 Phase Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                       IMPLEMENTATION TIMELINE                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 1: FOUNDATION & CLI (Weeks 1-2)                                     │
│  ═════════════════════════════════════                                      │
│  Goal: Basic CLI and Git-native infrastructure                             │
│  Deliverables:                                                              │
│    • context-md CLI tool (Python)                                          │
│    • init, config commands                                                 │
│    • Git hooks installation                                                │
│    • .agent-context/ directory structure                                   │
│  Success Criteria:                                                          │
│    • context-md init works on Windows/Mac/Linux                            │
│    • Hooks installed and functional                                        │
│                                                                             │
│  PHASE 2: WORKTREE SUBAGENTS (Weeks 3-4)                                   │
│  ════════════════════════════════════════                                   │
│  Goal: SubAgent isolation via Git worktrees                                │
│  Deliverables:                                                              │
│    • subagent spawn/complete commands                                      │
│    • Worktree management                                                   │
│    • state.json tracking                                                   │
│    • context generation                                                    │
│  Success Criteria:                                                          │
│    • SubAgents fully isolated in worktrees                                 │
│    • No file cross-contamination                                           │
│                                                                             │
│  PHASE 3: HOOKS & VALIDATION (Weeks 5-6)                                   │
│  ════════════════════════════════════════                                   │
│  Goal: Automated quality gates via Git hooks                               │
│  Deliverables:                                                              │
│    • prepare-commit-msg hook                                               │
│    • pre-commit hook                                                       │
│    • pre-push hook (DoD validation)                                        │
│    • post-commit/post-merge hooks                                          │
│    • validate command                                                      │
│  Success Criteria:                                                          │
│    • 100% handoffs validated automatically                                 │
│    • Issue references auto-added to commits                                │
│                                                                             │
│  PHASE 4: LEARNING LOOP (Weeks 7-8)                                        │
│  ════════════════════════════════════                                       │
│  Goal: Pattern analysis and metrics                                        │
│  Deliverables:                                                              │
│    • metrics command                                                       │
│    • Git notes for metrics storage                                         │
│    • Pattern detection                                                     │
│    • Completion certificates                                               │
│  Success Criteria:                                                          │
│    • Metrics queryable from Git history                                    │
│    • Learning reports generated                                            │
│                                                                             │
│  PHASE 5: CLI DASHBOARD (Weeks 9-10)                                       │
│  ════════════════════════════════════                                       │
│  Goal: Rich CLI status and dashboard                                       │
│  Deliverables:                                                              │
│    • status command (rich output)                                          │
│    • dashboard command (live view)                                         │
│    • Bottleneck detection                                                  │
│    • Stuck issue detection                                                 │
│  Success Criteria:                                                          │
│    • Real-time status visibility                                           │
│    • Stuck issues detected via Git activity                                │
│                                                                             │
│  PHASE 6: GITHUB SYNC & POLISH (Weeks 11-12)                               │
│  ════════════════════════════════════════════                               │
│  Goal: Optional GitHub integration                                         │
│  Deliverables:                                                              │
│    • sync command (push/pull)                                              │
│    • GitHub mode                                                           │
│    • Hybrid mode                                                           │
│    • Documentation and examples                                            │
│  Success Criteria:                                                          │
│    • Seamless local ↔ GitHub sync                                          │
│    • System works 100% offline                                             │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Detailed Task Breakdown

#### Phase 1: Foundation & CLI (Weeks 1-2)

| ID | Task | Estimate | Dependencies | Deliverable |
|----|------|----------|--------------|-------------|
| 1.1 | Create Python package structure | 2h | None | context_md/ |
| 1.2 | Implement CLI entry point (Click) | 4h | 1.1 | context-md command |
| 1.3 | Implement `init` command | 6h | 1.2 | Directory, hooks |
| 1.4 | Implement `config` command | 4h | 1.2 | Mode management |
| 1.5 | Create Git hooks (prepare-commit-msg) | 4h | 1.3 | Hook script |
| 1.6 | Create Git hooks (pre-commit) | 4h | 1.5 | Hook script |
| 1.7 | Create Git hooks (post-commit) | 4h | 1.6 | Hook script |
| 1.8 | Create state.json schema | 2h | 1.1 | JSON schema |
| 1.9 | Implement state management | 6h | 1.8 | State class |
| 1.10 | Cross-platform testing | 8h | All | Test results |
| 1.11 | Documentation | 4h | All | README |

**Phase 1 Total**: ~48 hours

#### Phase 2: Worktree SubAgents (Weeks 3-4)

| ID | Task | Estimate | Dependencies | Deliverable |
|----|------|----------|--------------|-------------|
| 2.1 | Implement `subagent spawn` | 8h | 1.3 | Worktree creation |
| 2.2 | Implement `subagent list` | 4h | 2.1 | Status display |
| 2.3 | Implement `subagent status` | 4h | 2.1 | Details view |
| 2.4 | Implement `subagent complete` | 6h | 2.1 | Cleanup logic |
| 2.5 | Implement context generation | 12h | 2.1 | Context files |
| 2.6 | Skill routing table | 4h | 2.5 | Routing logic |
| 2.7 | Implement `context generate` | 6h | 2.5, 2.6 | CLI command |
| 2.8 | Implement `context show` | 2h | 2.7 | Display command |
| 2.9 | Unit tests | 8h | All | Test suite |
| 2.10 | Integration tests | 6h | All | Test results |
| 2.11 | Documentation | 4h | All | Usage guide |

**Phase 2 Total**: ~64 hours

#### Phase 3: Hooks & Validation (Weeks 5-6)

| ID | Task | Estimate | Dependencies | Deliverable |
|----|------|----------|--------------|-------------|
| 3.1 | Implement pre-push hook | 8h | 1.3 | DoD validation |
| 3.2 | Implement post-merge hook | 4h | 1.3 | Certificate gen |
| 3.3 | Implement `validate --task` | 6h | 2.5 | Task validation |
| 3.4 | Implement `validate --pre-exec` | 6h | 3.3 | Pre-flight check |
| 3.5 | Implement `validate --dod` | 8h | 3.1 | DoD checklist |
| 3.6 | DoD checklists (PM) | 4h | 3.5 | Checklist |
| 3.7 | DoD checklists (Architect) | 4h | 3.5 | Checklist |
| 3.8 | DoD checklists (Engineer) | 4h | 3.5 | Checklist |
| 3.9 | DoD checklists (Reviewer) | 4h | 3.5 | Checklist |
| 3.10 | Unit tests | 8h | All | Test suite |
| 3.11 | Documentation | 4h | All | Validation guide |

**Phase 3 Total**: ~60 hours

#### Phase 4: Learning Loop (Weeks 7-8)

| ID | Task | Estimate | Dependencies | Deliverable |
|----|------|----------|--------------|-------------|
| 4.1 | Implement Git notes for metrics | 6h | 1.3 | Notes storage |
| 4.2 | Implement `metrics collect` | 8h | 4.1 | Collection logic |
| 4.3 | Implement `metrics show` | 4h | 4.2 | Display command |
| 4.4 | Implement `metrics export` | 4h | 4.2 | Export formats |
| 4.5 | Pattern detection algorithm | 8h | 4.2 | Analysis logic |
| 4.6 | Certificate schema | 2h | 3.2 | JSON schema |
| 4.7 | Certificate generation | 4h | 4.6 | Cert command |
| 4.8 | Instruction update suggestions | 6h | 4.5 | PR generation |
| 4.9 | Unit tests | 6h | All | Test suite |
| 4.10 | Documentation | 4h | All | Learning guide |

**Phase 4 Total**: ~52 hours

#### Phase 5: CLI Dashboard (Weeks 9-10)

| ID | Task | Estimate | Dependencies | Deliverable |
|----|------|----------|--------------|-------------|
| 5.1 | Design CLI UI (Rich library) | 4h | None | UI design |
| 5.2 | Implement `status` command | 6h | 5.1, 2.2 | Status display |
| 5.3 | Implement `dashboard` command | 8h | 5.1, 4.2 | Live dashboard |
| 5.4 | Real-time refresh | 4h | 5.3 | Watch mode |
| 5.5 | Bottleneck detection | 6h | 4.2 | Detection logic |
| 5.6 | Stuck detection (Git activity) | 6h | 4.2 | Last commit check |
| 5.7 | Color coding | 2h | 5.2, 5.3 | Visual indicators |
| 5.8 | Unit tests | 6h | All | Test suite |
| 5.9 | Documentation | 4h | All | Dashboard guide |

**Phase 5 Total**: ~46 hours

#### Phase 6: GitHub Sync & Polish (Weeks 11-12)

| ID | Task | Estimate | Dependencies | Deliverable |
|----|------|----------|--------------|-------------|
| 6.1 | Implement `issue` command (local) | 8h | 1.3 | Local issues |
| 6.2 | Implement `sync --push` | 10h | 6.1 | Local → GitHub |
| 6.3 | Implement `sync --pull` | 8h | 6.2 | GitHub → Local |
| 6.4 | Conflict detection | 4h | 6.2, 6.3 | Conflict logic |
| 6.5 | Hybrid mode logic | 6h | 6.2, 6.3 | Mode switching |
| 6.6 | GitHub PR creation | 6h | 6.2 | PR automation |
| 6.7 | End-to-end testing | 8h | All | Full workflow |
| 6.8 | Final documentation | 8h | All | Complete docs |
| 6.9 | Release preparation | 4h | All | Release notes |

**Phase 6 Total**: ~62 hours

### 11.3 Resource Requirements

| Resource | Requirement | Notes |
|----------|-------------|-------|
| **Engineer Time** | ~332 hours total | 1 engineer @ 12 weeks |
| **Architect Time** | ~20 hours | Design reviews, ADR updates |
| **PM Time** | ~10 hours | Acceptance testing |
| **Testing** | ~50 hours | Included in phase estimates |

### 11.4 Milestones & Gates

| Milestone | Week | Gate Criteria |
|-----------|------|---------------|
| **M1: CLI Foundation** | Week 2 | `context-md init` works, hooks install |
| **M2: SubAgent Isolation** | Week 4 | Worktrees create/destroy, context generated |
| **M3: Automated Validation** | Week 6 | pre-push blocks invalid handoffs |
| **M4: Learning Active** | Week 8 | Metrics in Git notes, patterns detected |
| **M5: Dashboard Live** | Week 10 | Rich CLI status, stuck detection works |
| **M6: Release** | Week 12 | GitHub sync optional, docs complete |
| 6.15 | Release preparation | 4h | 6.14 | Release notes |

**Phase 6 Total**: ~94 hours

### 10.3 Resource Requirements

| Resource | Requirement | Notes |
|----------|-------------|-------|
| **Engineer Time** | ~480 hours total | 1 engineer @ 12 weeks |
| **Architect Time** | ~40 hours | Design reviews, ADR updates |
| **PM Time** | ~20 hours | PRD updates, acceptance testing |
| **Testing** | ~80 hours | Included in phase estimates |

### 10.4 Milestones & Gates

| Milestone | Week | Gate Criteria |
|-----------|------|---------------|
| **M1: Foundation Complete** | Week 2 | Task validation working, templates updated |
| **M2: Context Working** | Week 4 | Context generation <30s, SubAgents isolated |
| **M3: Quality Automated** | Week 6 | Stuck detection active, handoffs validated |
| **M4: Learning Active** | Week 8 | Monthly reports generating, certificates working |
| **M5: Offline Ready** | Week 10 | Full offline operation, sync working |
| **M6: Release** | Week 12 | Dashboards live, documentation complete |

---

## 12. Risk Management

### 12.1 Risk Register

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| R1 | Worktree disk space | Medium | Medium | Cleanup on complete, limit concurrent |
| R2 | Git hook compatibility | Medium | Medium | Test on Windows/Mac/Linux, fallback |
| R3 | Token counting inaccuracy | Low | Medium | Use tiktoken library, validate |
| R4 | Git notes sync issues | Low | Medium | Push notes with refs |
| R5 | Worktree corruption | Low | High | Auto-recovery, re-create option |
| R6 | Performance with many branches | Low | Medium | Branch cleanup, archiving |
| R7 | GitHub API rate limits (github mode) | Medium | Low | Batch requests, cache |

### 12.2 Contingency Plans

| Risk | Contingency |
|------|-------------|
| R1: Disk space | `context-md cleanup --all` command |
| R2: Hook compatibility | Provide hook disable option |
| R5: Corruption | `context-md subagent recover` command |
| R6: Many branches | Archive old issues: `context-md archive` |

---

## 13. Success Metrics

### 13.1 Key Performance Indicators

| KPI | Baseline | Target | Measurement |
|-----|----------|--------|-------------|
| **Success Rate** | 70-80% | >95% | (Completed - Post-merge bugs) / Completed |
| **Handoff Success** | ~60% | >90% | First-attempt handoff passes |
| **Stuck Detection** | Manual | <1 hour | Time from stuck to escalation |
| **Context Efficiency** | ~100K tokens | Task-appropriate | Avg tokens per task type |
| **Quality Gate Pass** | ~30% auto | 100% auto | Automated validations / Total |
| **Learning Adoption** | 0% | 80% | Auto-updated instructions / Total updates |

### 13.2 Measurement Schedule

| Metric | Frequency | Owner |
|--------|-----------|-------|
| Success rate | Weekly | PM |
| Handoff success | Per-push | Automated (pre-push hook) |
| Stuck detection | Per-commit | Automated (Git activity) |
| Context efficiency | Per-task | Automated |
| Quality gates | Per-handoff | Automated (hooks) |
| Learning metrics | Monthly | PM |

---

## Appendix A: CLI Reference

### context-md init

```bash
Usage: context-md init [OPTIONS]

Initialize Context.md in the current Git repository.

Options:
  --mode [local|github|hybrid]  Operating mode (default: local)
  --force                       Overwrite existing configuration
  --help                        Show this help

Examples:
  context-md init
  context-md init --mode github
```

### context-md subagent

```bash
Usage: context-md subagent <command> [OPTIONS]

Commands:
  spawn     Create a new SubAgent with isolated worktree
  list      List active SubAgents
  status    Show SubAgent details
  complete  Mark SubAgent work as complete
  recover   Recover corrupted worktree

Options:
  --role [pm|architect|engineer|reviewer|ux]  Agent role
  --help                                       Show this help

Examples:
  context-md subagent spawn 456 --role engineer
  context-md subagent list
  context-md subagent complete 456
```

### context-md validate

```bash
Usage: context-md validate <issue> [OPTIONS]

Run validation checks for an issue.

Options:
  --task       Validate task quality (required fields, stranger test)
  --pre-exec   Pre-flight validation (context, dependencies)
  --dod        Definition of Done checklist
  --all        Run all validations
  --verbose    Show detailed output
  --help       Show this help

Exit Codes:
  0  Pass
  1  Fail (with remediation guidance)
  2  Error

Examples:
  context-md validate 456 --dod
  context-md validate 456 --all --verbose
```

### context-md status

```bash
Usage: context-md status [OPTIONS]

Show current Context.md status.

Options:
  --json       Output as JSON
  --watch      Continuously update
  --help       Show this help

Examples:
  context-md status
  context-md status --watch
```

### context-md sync (GitHub/Hybrid mode)

```bash
Usage: context-md sync [OPTIONS]

Synchronize with GitHub.

Options:
  --push       Push local changes to GitHub
  --pull       Pull GitHub changes to local
  --all        Push and pull
  --help       Show this help

Examples:
  context-md sync --push
  context-md sync --all
```

---

## Appendix B: Git Notes Usage

### Storing Metadata

```bash
# Add metadata to a branch tip
git notes --ref=context add -m '{"status":"in_progress","role":"engineer"}' refs/heads/issue-456-jwt

# View metadata
git notes --ref=context show refs/heads/issue-456-jwt

# Update metadata
git notes --ref=context add -f -m '{"status":"completed"}' refs/heads/issue-456-jwt

# List all context notes
git notes --ref=context list
```

### Pushing Notes

```bash
# Push notes to remote
git push origin refs/notes/context

# Pull notes from remote
git fetch origin refs/notes/context:refs/notes/context
```

---

## Appendix C: Worktree Commands

### Basic Operations

```bash
# Create worktree
git worktree add ../worktrees/456 issue-456-jwt

# List worktrees
git worktree list

# Remove worktree
git worktree remove ../worktrees/456

# Prune stale worktree entries
git worktree prune
```

### Worktree Locations

```
Repository: /projects/myrepo/
Worktrees:  /projects/worktrees/
            ├── 456/    ← SubAgent for issue 456
            ├── 457/    ← SubAgent for issue 457
            └── 458/    ← SubAgent for issue 458
```

---

**Document Version**: 2.0  
**Last Updated**: 2026-01-29  
**Author**: Architect Agent  
**Approved By**: [Pending]

---

**Architecture**: Git-Native (branches, worktrees, notes, hooks)  
**Mode**: Local-first with optional GitHub sync  
**Automation**: Event-driven via Git hooks  
**Dependencies**: Git only
