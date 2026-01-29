# Technical Specification: Context.md System

**Issue**: #CONTEXT-MD  
**Epic**: #CONTEXT-MD  
**Status**: Draft  
**Author**: Architect Agent  
**Date**: 2026-01-29  
**Related ADR**: [ADR-CONTEXT-MD.md](../adr/ADR-CONTEXT-MD.md)  
**Related PRD**: [PRD-CONTEXT-MD.md](../prd/PRD-CONTEXT-MD.md)

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [Component Design](#3-component-design)
4. [Data Models](#4-data-models)
5. [Script Specifications](#5-script-specifications)
6. [Integration Points](#6-integration-points)
7. [Security Design](#7-security-design)
8. [Performance](#8-performance)
9. [Testing Strategy](#9-testing-strategy)
10. [Rollout Plan](#10-rollout-plan)
11. [Monitoring & Observability](#11-monitoring--observability)

---

## 1. Overview

Context.md is a runtime context management and quality orchestration system that enables AI agents to achieve >95% success rate in production-ready code generation.

**Scope:**
- In scope: All 10 layers defined in PRD (Backlog, Context, Planning, Quality, Learning, Visibility, SubAgent, Code Inspection, Local Fallback, Traceability)
- Out of scope: External tool integrations (Jira, Linear), custom LLM hosting, multi-language support

**Success Criteria:**
- >95% production code success rate (measured by post-merge bug count)
- <10% handoff clarification rate (measured by issue comments)
- <1 hour stuck issue detection time
- 100% automated quality gate coverage

---

## 2. System Architecture

### 2.1 Ten-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONTEXT.MD SYSTEM ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 1: BACKLOG MANAGEMENT                      │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │ │
│  │  │  Task Validation │  │ Dependency Check │  │ Standalone Enforcer  │  │ │
│  │  │  (story.yml)     │  │ (provides/integ) │  │ (stranger test)      │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 2: CONTEXT OPTIMIZATION                    │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │ │
│  │  │ Context Generator│  │  Skill Router    │  │  Size Monitor        │  │ │
│  │  │ (per-task .md)   │  │ (label→skills)   │  │ (warning/block)      │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 3: PLANNING & VALIDATION                   │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │ │
│  │  │ Execution Planner│  │ Pre-Flight Check │  │  DoD Checklists      │  │ │
│  │  │ (plan-{issue}.md)│  │ (validate-pre)   │  │ (per deliverable)    │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 4: QUALITY MONITORING                      │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │ │
│  │  │ Stuck Detection  │  │ Crash Recovery   │  │ Alignment Validator  │  │ │
│  │  │ (cron 30min)     │  │ (auto-restart)   │  │ (PRD→Spec→Code)      │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 5: LEARNING LOOP                           │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │ │
│  │  │ Pattern Analyzer │  │ Instruction Gen  │  │ Metrics Tracker      │  │ │
│  │  │ (monthly report) │  │ (auto-update PR) │  │ (trends/regression)  │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 6: VISIBILITY                              │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │ │
│  │  │  CLI Dashboard   │  │  Web Dashboard   │  │ Bottleneck Detector  │  │ │
│  │  │ (terminal UI)    │  │ (GitHub Pages)   │  │ (weekly report)      │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 7: SUBAGENT ORCHESTRATION                  │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │ │
│  │  │ SubAgent Spawner │  │ Context Isolator │  │ Status Coordinator   │  │ │
│  │  │ (runSubagent)    │  │ (per-task scope) │  │ (subagent-status)    │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 8: CODE INSPECTION                         │ │
│  │  ┌──────────────────┐  ┌──────────────────┐                            │ │
│  │  │  DebugMCP Client │  │ Static Analyzer  │                            │ │
│  │  │ (runtime inspect)│  │ (pre-handoff)    │                            │ │
│  │  └──────────────────┘  └──────────────────┘                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 9: LOCAL FALLBACK                          │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │ │
│  │  │ GitHub Detector  │  │ Local Issue Mgr  │  │  Sync Engine         │  │ │
│  │  │ (connectivity)   │  │ (local-issues)   │  │ (reconnect sync)     │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        LAYER 10: COMPLETION TRACEABILITY                │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │ │
│  │  │   Audit Logger   │  │ Certificate Gen  │  │ Timeline Visualizer  │  │ │
│  │  │ (append-only)    │  │ (quality proof)  │  │ (progress view)      │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Hub-and-Spoke SubAgent Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SUBAGENT ORCHESTRATION MODEL                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                          ┌─────────────────────┐                             │
│                          │      AGENT X        │                             │
│                          │   (Orchestrator)    │                             │
│                          │                     │                             │
│                          │  • Route issues     │                             │
│                          │  • Spawn SubAgents  │                             │
│                          │  • Monitor status   │                             │
│                          │  • Handle failures  │                             │
│                          │  • Coordinate sync  │                             │
│                          └──────────┬──────────┘                             │
│                                     │                                        │
│            ┌────────────────────────┼────────────────────────┐               │
│            │                        │                        │               │
│            ▼                        ▼                        ▼               │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐        │
│  │   SUBAGENT-456  │     │   SUBAGENT-457  │     │   SUBAGENT-458  │        │
│  │   (Engineer)    │     │   (Engineer)    │     │   (Reviewer)    │        │
│  ├─────────────────┤     ├─────────────────┤     ├─────────────────┤        │
│  │ Issue: #456     │     │ Issue: #457     │     │ Issue: #458     │        │
│  │ Task: JWT Valid │     │ Task: OAuth     │     │ Task: Review    │        │
│  │ Status: coding  │     │ Status: testing │     │ Status: review  │        │
│  ├─────────────────┤     ├─────────────────┤     ├─────────────────┤        │
│  │ CONTEXT:        │     │ CONTEXT:        │     │ CONTEXT:        │        │
│  │ • context-456   │     │ • context-457   │     │ • context-458   │        │
│  │ • plan-456      │     │ • plan-457      │     │ • review-458    │        │
│  │ • Skills #04,02 │     │ • Skills #09,04 │     │ • Skills #18,04 │        │
│  │                 │     │                 │     │                 │        │
│  │ ISOLATED:       │     │ ISOLATED:       │     │ ISOLATED:       │        │
│  │ No access to    │     │ No access to    │     │ No access to    │        │
│  │ other contexts  │     │ other contexts  │     │ other contexts  │        │
│  └────────┬────────┘     └────────┬────────┘     └────────┬────────┘        │
│           │                       │                       │                  │
│           ▼                       ▼                       ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    .agent-context/ (File System)                     │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────────┐  │    │
│  │  │context-456  │ │context-457  │ │context-458  │ │subagent-status│  │    │
│  │  │.md          │ │.md          │ │.md          │ │.json          │  │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └───────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Workflow Sequence: Task Execution

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TASK EXECUTION SEQUENCE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   PM           Agent X        Scripts        SubAgent       GitHub          │
│    │              │              │              │              │             │
│    │──Create Issue─────────────────────────────────────────>│             │
│    │              │              │              │              │             │
│    │              │<─Issue Event─┼──────────────┼──────────────│             │
│    │              │              │              │              │             │
│    │              │──Validate────>│              │              │             │
│    │              │  Task        │              │              │             │
│    │              │              │              │              │             │
│    │              │<─Pass/Fail───│              │              │             │
│    │              │              │              │              │             │
│    │              │──Generate────>│              │              │             │
│    │              │  Context     │              │              │             │
│    │              │              │              │              │             │
│    │              │<─context.md──│              │              │             │
│    │              │              │              │              │             │
│    │              │──Spawn SubAgent────────────>│              │             │
│    │              │  (with context)             │              │             │
│    │              │              │              │              │             │
│    │              │              │              │──Update Status────────────>│
│    │              │              │              │  In Progress  │             │
│    │              │              │              │              │             │
│    │              │              │──Pre-Flight──│              │             │
│    │              │              │  Validation  │              │             │
│    │              │              │              │              │             │
│    │              │              │              │──Execute Work─────────────>│
│    │              │              │              │  (commits)    │             │
│    │              │              │              │              │             │
│    │              │              │──Handoff─────│              │             │
│    │              │              │  Validation  │              │             │
│    │              │              │              │              │             │
│    │              │              │              │──Update Status────────────>│
│    │              │              │              │  In Review    │             │
│    │              │              │              │              │             │
│    │              │<─Complete────┼──────────────│              │             │
│    │              │              │              │              │             │
│    │              │──Terminate───┼──────────────>│              │             │
│    │              │  SubAgent    │   (cleanup)  │              │             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.4 Local Fallback Mode

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LOCAL FALLBACK MODE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CONNECTED MODE                      DISCONNECTED MODE                       │
│  ═══════════════                     ══════════════════                      │
│                                                                              │
│  ┌──────────────────┐                ┌──────────────────┐                   │
│  │     GitHub       │                │   Local Files    │                   │
│  │   ┌──────────┐   │                │   ┌──────────┐   │                   │
│  │   │  Issues  │   │  ──Offline──>  │   │local-    │   │                   │
│  │   └──────────┘   │                │   │issues.json   │                   │
│  │   ┌──────────┐   │                │   └──────────┘   │                   │
│  │   │ Projects │   │  ──Offline──>  │   ┌──────────┐   │                   │
│  │   │ (Status) │   │                │   │local-    │   │                   │
│  │   └──────────┘   │                │   │status.json   │                   │
│  │   ┌──────────┐   │                │   └──────────┘   │                   │
│  │   │   PRs    │   │  ──Offline──>  │   ┌──────────┐   │                   │
│  │   └──────────┘   │                │   │Git Branch│   │                   │
│  └──────────────────┘                │   └──────────┘   │                   │
│                                      └──────────────────┘                   │
│          │                                    │                              │
│          │                                    │                              │
│          └──────────── SYNC ON ──────────────┘                              │
│                      RECONNECT                                               │
│                                                                              │
│  Sync Process:                                                               │
│  1. Detect GitHub availability                                               │
│  2. For each local-only issue:                                              │
│     a. Create GitHub issue                                                  │
│     b. Update local record with github_id                                   │
│     c. Rewrite commit messages with issue references                        │
│  3. Sync status to GitHub Projects                                          │
│  4. Generate sync report                                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Design

### 3.1 Directory Structure

```
.agent-context/                     # Runtime state directory
├── context-{issue}.md              # Per-task context (generated)
├── plan-{issue}.md                 # Per-task execution plan
├── analysis-{issue}.json           # Code analysis results
├── subagent-status.json            # Active SubAgent tracking
├── local-issues.json               # Offline issue storage
├── local-status.json               # Offline status tracking
├── audit-log.json                  # Append-only action log
├── metrics-{date}.json             # Daily metrics snapshots
├── learning-{date}.json            # Learning analysis reports
└── certificates/                   # Completion certificates
    └── cert-{issue}.json

.github/
├── scripts/                        # Automation scripts
│   ├── generate-context.sh         # Context generation
│   ├── generate-context.ps1        # PowerShell variant
│   ├── validate-task-creation.sh   # Task validation
│   ├── validate-pre-execution.sh   # Pre-flight checks
│   ├── validate-handoff.sh         # Handoff validation
│   ├── detect-stuck-issues.sh      # Stuck detection
│   ├── analyze-learning.sh         # Learning analysis
│   ├── sync-to-github.sh           # Local→GitHub sync
│   └── dashboard-cli.sh            # CLI dashboard
├── workflows/                      # GitHub Actions
│   ├── context-manager.yml         # Main workflow
│   ├── stuck-detection.yml         # Cron: every 30 min
│   ├── learning-analysis.yml       # Cron: monthly
│   └── crash-recovery.yml          # Cron: every 15 min
├── templates/                      # Document templates
│   ├── PLAN-TEMPLATE.md            # Execution plan template
│   └── ... (existing templates)
└── ISSUE_TEMPLATE/
    └── story.yml                   # Enhanced with validation

docs/
├── dashboard/                      # Web dashboard (GitHub Pages)
│   ├── index.html
│   ├── trends.html
│   ├── agents.html
│   └── quality.html
└── ...
```

### 3.2 Component Responsibilities

| Component | Responsibility | Dependencies |
|-----------|---------------|--------------|
| **Context Generator** | Assemble task-specific context from role, issue, skills | GitHub API, Skills.md |
| **Task Validator** | Enforce standalone principle at issue creation | GitHub API, Issue Templates |
| **Pre-Flight Validator** | Check readiness before work starts | Context files, Issue state |
| **Handoff Validator** | Verify DoD completion before status transition | Git, Test results, Lint |
| **Stuck Detector** | Identify issues with no activity >24h | GitHub API, Cron |
| **Learning Analyzer** | Identify patterns from closed issues | GitHub API, Metrics |
| **SubAgent Coordinator** | Spawn/monitor/terminate SubAgents | runSubagent tool, Status file |
| **Audit Logger** | Record all actions immutably | File system |
| **Sync Engine** | Sync local state to GitHub on reconnect | GitHub API, Local files |
| **Dashboard (CLI)** | Real-time terminal UI | Status files, GitHub API |
| **Dashboard (Web)** | GitHub Pages visualizations | Metrics files, GitHub API |

---

## 4. Data Models

### 4.1 Context File Schema

**File**: `.agent-context/context-{issue}.md`

```markdown
# Context - Issue #{issue_number}

## Metadata
- **Generated**: {timestamp}
- **Issue**: #{issue_number}
- **Type**: {story|bug|feature|epic}
- **Role**: {pm|architect|engineer|reviewer|ux}
- **Token Count**: {count}

## Role Instructions
{Complete role instructions from .github/agents/{role}.agent.md}

## Issue Details
### Title
{Issue title}

### Description
{Full issue description}

### Labels
{label1}, {label2}, ...

### Dependencies
{Structured dependency list with provides/integration/verification}

### Acceptance Criteria
{List of acceptance criteria}

## Previous Deliverables
### PRD (if exists)
{Link and summary}

### ADR (if exists)
{Link and summary}

### Tech Spec (if exists)
{Link and summary}

## Relevant Skills
### Skill #XX: {Name}
{Complete skill content - never truncated}

### Skill #YY: {Name}
{Complete skill content - never truncated}

## References
{Code files, documentation links from issue}

## Execution Checklist
- [ ] Review context
- [ ] Generate execution plan
- [ ] Pass pre-flight validation
- [ ] Execute work
- [ ] Pass handoff validation
```

### 4.2 SubAgent Status Schema

**File**: `.agent-context/subagent-status.json`

```json
{
  "$schema": "subagent-status-v1",
  "last_updated": "2026-01-29T14:35:00Z",
  "subagents": [
    {
      "id": "subagent-456",
      "issue": 456,
      "role": "engineer",
      "status": "in_progress",
      "phase": "coding",
      "started_at": "2026-01-29T10:00:00Z",
      "last_activity": "2026-01-29T14:35:00Z",
      "context_file": ".agent-context/context-456.md",
      "plan_file": ".agent-context/plan-456.md",
      "errors": [],
      "metrics": {
        "commits": 3,
        "files_changed": 5,
        "tests_added": 12
      }
    }
  ],
  "summary": {
    "active": 3,
    "completed_today": 5,
    "stuck": 0,
    "failed": 0
  }
}
```

### 4.3 Audit Log Schema

**File**: `.agent-context/audit-log.json`

```json
{
  "$schema": "audit-log-v1",
  "entries": [
    {
      "id": "audit-2026012914350001",
      "timestamp": "2026-01-29T14:35:00Z",
      "agent": "engineer",
      "subagent_id": "subagent-456",
      "action": "handoff",
      "issue": 456,
      "details": "Completed coding, moving to review",
      "result": "success",
      "validation": {
        "tests_passed": true,
        "coverage": 85,
        "lint_errors": 0,
        "security_scan": "passed",
        "dod_complete": true
      },
      "duration_ms": 14400000,
      "token_usage": {
        "input": 45000,
        "output": 12000
      }
    }
  ]
}
```

### 4.4 Local Issues Schema

**File**: `.agent-context/local-issues.json`

```json
{
  "$schema": "local-issues-v1",
  "mode": "offline",
  "last_sync": null,
  "issues": [
    {
      "local_id": "LOCAL-001",
      "github_id": null,
      "title": "[Story] Add JWT validation",
      "body": "## Description\n...",
      "type": "story",
      "status": "in_progress",
      "assignee": "engineer",
      "labels": ["type:story", "api"],
      "created_at": "2026-01-29T10:00:00Z",
      "updated_at": "2026-01-29T14:00:00Z",
      "synced": false,
      "commits": ["abc123", "def456"]
    }
  ]
}
```

### 4.5 Metrics Schema

**File**: `.agent-context/metrics-{date}.json`

```json
{
  "$schema": "metrics-v1",
  "date": "2026-01-29",
  "period": "daily",
  "success_metrics": {
    "success_rate": 85.0,
    "handoff_success_rate": 78.5,
    "first_attempt_pass_rate": 72.0
  },
  "efficiency_metrics": {
    "avg_context_size_tokens": 62000,
    "avg_task_duration_hours": 4.5,
    "avg_revision_cycles": 1.3
  },
  "quality_metrics": {
    "quality_gate_pass_rate": 88.5,
    "test_coverage_avg": 82.0,
    "lint_error_rate": 2.1
  },
  "health_metrics": {
    "stuck_issues_detected": 2,
    "stuck_issues_resolved": 2,
    "crash_recoveries": 1
  },
  "learning_metrics": {
    "instruction_updates": 1,
    "pattern_detections": 3
  },
  "top_failure_types": [
    {"type": "missing_tests", "count": 3},
    {"type": "incomplete_context", "count": 2}
  ]
}
```

### 4.6 Completion Certificate Schema

**File**: `.agent-context/certificates/cert-{issue}.json`

```json
{
  "$schema": "certificate-v1",
  "certificate": {
    "id": "CERT-456-2026012914",
    "issue": 456,
    "type": "code_deliverable",
    "completed_at": "2026-01-29T14:30:00Z",
    "agent": "engineer",
    "subagent_id": "subagent-456",
    "validations": {
      "dod_checklist": "100%",
      "test_coverage": "85%",
      "tests_passing": true,
      "security_scan": "passed",
      "lint_errors": 0,
      "docs_updated": true
    },
    "artifacts": {
      "commits": ["abc123", "def456"],
      "files_changed": 8,
      "pr_number": 789
    },
    "hash": "sha256:abc123def456..."
  }
}
```

---

## 5. Script Specifications

### 5.1 generate-context.sh

**Purpose**: Generate task-specific context file

**Usage**: `./generate-context.sh <issue-number>`

**Algorithm**:
```
1. Fetch issue metadata from GitHub API
2. Determine role from issue type/labels
3. Load role instructions from .github/agents/{role}.agent.md
4. Determine required skills from label→skill routing table
5. Load complete skill files (never truncate)
6. Fetch previous deliverables (PRD, ADR, Spec) if exist
7. Extract references and documentation from issue body
8. Calculate total token count
9. If >150K tokens: ERROR, block execution, suggest split
10. If >100K tokens: WARNING, continue but log
11. Write to .agent-context/context-{issue}.md
12. Return success/failure
```

**Routing Table**:
```bash
declare -A SKILL_ROUTING=(
  ["api"]="#09,#04,#02,#11"
  ["database"]="#06,#04,#02"
  ["security"]="#04,#10,#02,#13,#15"
  ["frontend"]="#21,#22,#02,#11"
  ["bug"]="#03,#02,#15"
  ["performance"]="#05,#06,#02,#15"
  ["ai"]="#17,#04"
)
```

### 5.2 validate-task-creation.sh

**Purpose**: Validate task completeness before creation

**Usage**: `./validate-task-creation.sh <issue-number>`

**Validation Checks**:
```
1. References field exists and has valid file paths
2. Documentation field exists with links
3. Dependencies have structured format (provides/integration/verification)
4. Acceptance criteria are specific and testable
5. Stranger test: Can someone unfamiliar execute this?
6. No vague phrases ("as discussed", "like before", etc.)
```

**Exit Codes**:
- 0: Valid
- 1: Missing required fields
- 2: Invalid dependency format
- 3: Vague content detected

### 5.3 validate-handoff.sh

**Purpose**: Validate deliverable before status transition

**Usage**: `./validate-handoff.sh <issue-number> <role>`

**DoD Checklists by Role**:

**Engineer**:
```
- [ ] Code committed and pushed
- [ ] Tests written (≥80% coverage)
- [ ] Tests passing in CI
- [ ] Documentation updated
- [ ] No compiler warnings or linter errors
- [ ] Security scan passed
```

**Architect**:
```
- [ ] ADR created at docs/adr/ADR-{issue}.md
- [ ] Tech Spec created at docs/specs/SPEC-{issue}.md
- [ ] No code examples (diagrams only)
- [ ] Options with pros/cons documented
- [ ] Decision rationale clear
```

**PM**:
```
- [ ] PRD created at docs/prd/PRD-{issue}.md
- [ ] Child issues created (Features/Stories)
- [ ] Acceptance criteria defined for each
- [ ] Success metrics specified
```

### 5.4 detect-stuck-issues.sh

**Purpose**: Identify stuck issues for escalation

**Usage**: `./detect-stuck-issues.sh` (runs via cron)

**Algorithm**:
```
1. Query GitHub for issues with Status = "In Progress"
2. For each issue:
   a. Get last commit timestamp
   b. Get last comment timestamp
   c. Calculate hours since last activity
   d. If hours > 24:
      - Create escalation issue
      - Add "needs:help" label
      - Post comment to original issue
      - Notify Agent X
3. Log detection results
```

### 5.5 sync-to-github.sh

**Purpose**: Sync local issues to GitHub on reconnect

**Usage**: `./sync-to-github.sh`

**Algorithm**:
```
1. Check GitHub API availability
2. If unavailable, exit with status 1
3. Read .agent-context/local-issues.json
4. For each unsynced issue:
   a. Create GitHub issue via API
   b. Update local record with github_id
   c. Find commits referencing local_id
   d. Rewrite commit messages with github_id
5. Sync status to GitHub Projects via GraphQL
6. Generate sync report
7. Mark issues as synced
```

---

## 6. Integration Points

### 6.1 VS Code Integration

| Integration | Method | Notes |
|-------------|--------|-------|
| SubAgent Spawning | `runSubagent` tool | Pass context file path |
| File Operations | `read_file`, `create_file` | Access .agent-context/ |
| Terminal | `run_in_terminal` | Execute scripts |
| Todo List | `manage_todo_list` | Track within session |

### 6.2 GitHub Integration

| Integration | Method | Notes |
|-------------|--------|-------|
| Issues | REST API / `gh` CLI | CRUD operations |
| Projects V2 | GraphQL API | Status field updates |
| Actions | Workflows | Cron jobs for monitoring |
| Pages | Static site | Web dashboard |

### 6.3 MCP Integration (Future)

| Tool | Purpose |
|------|---------|
| `context_generate` | Generate context for issue |
| `context_validate` | Validate task/handoff |
| `subagent_spawn` | Create isolated SubAgent |
| `subagent_status` | Query SubAgent state |
| `metrics_query` | Get quality metrics |

### 6.4 DebugMCP Integration

| Feature | Integration Point |
|---------|-------------------|
| Breakpoints | Engineer SubAgent execution |
| Variable Inspection | Test debugging |
| Execution Trace | Performance analysis |
| Memory Profiling | Leak detection |

---

## 7. Security Design

### 7.1 Context Isolation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CONTEXT ISOLATION MODEL                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SubAgent-456 Boundary                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  ALLOWED:                                                               │ │
│  │  ✓ .agent-context/context-456.md                                       │ │
│  │  ✓ .agent-context/plan-456.md                                          │ │
│  │  ✓ docs/prd/PRD-{ref}.md (if in References)                            │ │
│  │  ✓ docs/adr/ADR-{ref}.md (if in References)                            │ │
│  │  ✓ src/auth/*.ts (if in References)                                    │ │
│  │                                                                         │ │
│  │  BLOCKED:                                                               │ │
│  │  ✗ .agent-context/context-457.md (other SubAgent)                      │ │
│  │  ✗ .agent-context/context-458.md (other SubAgent)                      │ │
│  │  ✗ Any file not in References field                                    │ │
│  │  ✗ Environment variables with secrets                                  │ │
│  │  ✗ .git/config (credentials)                                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Audit Trail Security

- **Append-only**: Audit log entries cannot be modified or deleted
- **Tamper-evident**: SHA-256 hash chain links entries
- **Timestamps**: UTC timestamps from trusted source
- **Identity**: Agent/SubAgent ID recorded for every action

### 7.3 Local Fallback Security

- **Credential isolation**: GitHub PAT never stored in local files
- **Sync validation**: All synced content validated before push
- **Conflict resolution**: Human review for conflicts

---

## 8. Performance

### 8.1 Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Context Generation | <30s (typical) | <60s for large tasks |
| Task Validation | <5s | Simple field checks |
| Handoff Validation | <30s | Includes test/lint checks |
| Stuck Detection | <2min | Per cron run |
| Dashboard Refresh | 10s | CLI polling interval |

### 8.2 Optimization Strategies

**Context Generation**:
- Cache skill files in memory during session
- Parallel fetch of issue + deliverables
- Incremental token counting

**Stuck Detection**:
- Batch GitHub API queries
- Cache issue state between runs
- Skip recently checked issues

**Dashboard**:
- Incremental updates (diff-based)
- Lazy load historical data
- Client-side caching

---

## 9. Testing Strategy

### 9.1 Test Pyramid

```
                    ┌───────────────┐
                    │     E2E       │  10%
                    │  (Full flows) │
                    └───────┬───────┘
                    ┌───────┴───────┐
                    │  Integration  │  20%
                    │  (Script+API) │
                    └───────┬───────┘
            ┌───────────────┴───────────────┐
            │           Unit Tests          │  70%
            │     (Script functions)        │
            └───────────────────────────────┘
```

### 9.2 Test Categories

**Unit Tests** (`tests/unit/`):
- Context generation logic
- Validation rules
- Routing table correctness
- Token counting accuracy

**Integration Tests** (`tests/integration/`):
- Script execution with mock GitHub
- File I/O operations
- SubAgent status coordination

**E2E Tests** (`tests/e2e/`):
- Full task creation → completion flow
- Stuck detection → escalation
- Local → GitHub sync

### 9.3 Test Coverage Targets

| Component | Target |
|-----------|--------|
| Scripts | ≥80% |
| Data schemas | 100% |
| Routing logic | 100% |
| Integration points | ≥70% |

---

## 10. Rollout Plan

### Phase 1: Foundation (Weeks 1-2)
- [ ] Create `.agent-context/` directory structure
- [ ] Implement `generate-context.sh`
- [ ] Implement `validate-task-creation.sh`
- [ ] Update issue templates with required fields
- [ ] Unit tests for Phase 1

### Phase 2: SubAgent Orchestration (Weeks 3-4)
- [ ] Implement SubAgent spawning
- [ ] Implement context isolation
- [ ] Create `subagent-status.json` management
- [ ] Implement `validate-pre-execution.sh`
- [ ] Integration tests for Phase 2

### Phase 3: Quality Monitoring (Weeks 5-6)
- [ ] Implement `detect-stuck-issues.sh`
- [ ] Create GitHub Actions workflows for cron jobs
- [ ] Implement `validate-handoff.sh`
- [ ] Implement crash recovery
- [ ] Deploy to production (monitoring only)

### Phase 4: Learning Loop (Weeks 7-8)
- [ ] Implement `analyze-learning.sh`
- [ ] Create metrics collection
- [ ] Implement instruction update PR generation
- [ ] Create audit logging
- [ ] E2E tests for learning flow

### Phase 5: Local Fallback (Weeks 9-10)
- [ ] Implement GitHub availability detection
- [ ] Create local issue management
- [ ] Implement `sync-to-github.sh`
- [ ] Test offline scenarios

### Phase 6: Visibility (Weeks 11-12)
- [ ] Implement CLI dashboard
- [ ] Create web dashboard (GitHub Pages)
- [ ] Implement bottleneck detection
- [ ] Polish and documentation
- [ ] Full E2E validation

---

## 11. Monitoring & Observability

### 11.1 Metrics to Track

| Metric | Collection | Alert Threshold |
|--------|------------|-----------------|
| Success Rate | Per issue close | <90% |
| Handoff Success | Per status transition | <80% |
| Stuck Issues | Per detection run | >3 active |
| Context Size | Per generation | >100K tokens |
| SubAgent Failures | Per termination | >2 per day |

### 11.2 Dashboards

**CLI Dashboard** (`dashboard-cli.sh`):
- Active issues by agent
- SubAgent status
- Today's metrics
- Stuck issue alerts

**Web Dashboard** (GitHub Pages):
- Success rate trend (30 days)
- Context size distribution
- Agent throughput
- Quality gate pass rates
- Bottleneck analysis

### 11.3 Alerting

| Alert | Trigger | Action |
|-------|---------|--------|
| Stuck Issue | No activity >24h | Create escalation issue |
| SubAgent Crash | Unexpected termination | Auto-restart (1x) |
| Success Drop | Rate <85% | Notify maintainers |
| Context Overflow | >150K tokens | Block execution |

---

**Author**: Architect Agent  
**Last Updated**: 2026-01-29  
**Version**: 1.0
