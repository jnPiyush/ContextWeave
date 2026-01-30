# 4-Layer AI Context Architecture

> **Purpose**: Document the foundational architecture for AI agent context management in Context.md.

## Overview

Context.md implements a **4-Layer AI Context Architecture** that provides structured context to AI agents for achieving >95% success rate in production code generation.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        4-LAYER AI CONTEXT ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 1: SYSTEM CONTEXT                                            │   │
│  │  ──────────────────────────────────────────────────────────────────│   │
│  │  Purpose: Governs AI behavior and capabilities                      │   │
│  │  Source:  .github/agents/{role}.agent.md                           │   │
│  │  Content: Role instructions, constraints, guidelines                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 2: USER PROMPT                                               │   │
│  │  ──────────────────────────────────────────────────────────────────│   │
│  │  Purpose: What the user asks / task requirements                    │   │
│  │  Source:  Issue metadata, Git notes, branch info                   │   │
│  │  Content: Title, description, acceptance criteria, labels          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 3: MEMORY                                                    │   │
│  │  ──────────────────────────────────────────────────────────────────│   │
│  │  Purpose: Persistent knowledge across sessions                      │   │
│  │  Source:  .agent-context/memory.json                               │   │
│  │  Content: Lessons learned, session history, success metrics        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 4: RETRIEVAL CONTEXT                                         │   │
│  │  ──────────────────────────────────────────────────────────────────│   │
│  │  Purpose: Knowledge grounding from documentation                    │   │
│  │  Source:  .github/skills/{category}/{skill}/SKILL.md               │   │
│  │  Content: Technical guidelines, best practices, standards          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Layer Details

### Layer 1: System Context

**Purpose**: Defines the AI agent's role, capabilities, and behavioral constraints.

**Implementation**: [context.py#L177-L178](../context_md/commands/context.py#L177-L178)

```
Location: .github/agents/{role}.agent.md
Roles:    engineer, pm, architect, reviewer, ux
```

**Content Examples**:
- Role-specific instructions ("You are a Software Engineer...")
- Output constraints ("Produce code with tests...")
- Quality requirements ("All code must pass security checks...")
- Workflow rules ("Follow the issue-first workflow...")

**Files**:
| File | Purpose |
|------|---------|
| `.github/agents/engineer.agent.md` | Software Engineer behavior |
| `.github/agents/pm.agent.md` | Product Manager behavior |
| `.github/agents/architect.agent.md` | Solution Architect behavior |
| `.github/agents/reviewer.agent.md` | Code Reviewer behavior |
| `.github/agents/ux.agent.md` | UX Designer behavior |

---

### Layer 2: User Prompt (Enhanced with Prompt Engineering)

**Purpose**: Contains the specific task requirements - what the user is asking the agent to do.

**Implementation**: 
- Raw Extraction: [context.py#L195-L213](../context_md/commands/context.py#L195-L213)
- Prompt Enhancement: [prompt.py](../context_md/prompt.py)

```
Sources: Git branch name, Git notes, issue metadata
Enhancement: PromptEngineer class applies prompt engineering best practices
```

**Raw Content**:
| Field | Source | Description |
|-------|--------|-------------|
| Title | Git notes / branch | Issue title |
| Description | Git notes | Detailed requirements |
| Labels | Git notes | Type, priority, category |
| Status | Git notes | Current workflow state |
| Dependencies | Git notes | Related issues/PRs |
| Acceptance Criteria | Git notes | Definition of done |

#### Prompt Engineering Enhancement

Before handing context to role-based agents, raw prompts are enhanced using the `PromptEngineer` class:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PROMPT ENGINEERING PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Raw Prompt (from issue/Git notes)                                         │
│        ↓                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PromptEngineer.enhance_prompt()                                    │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  1. Apply role-specific template                                    │   │
│  │  2. Add context summary (dependencies, specs)                       │   │
│  │  3. Define inputs and outputs                                       │   │
│  │  4. Extract constraints from prompt                                 │   │
│  │  5. Add success criteria by issue type                              │   │
│  │  6. Add label-specific approach hints                               │   │
│  │  7. Define handoff requirements for next role                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│        ↓                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  validate_prompt_completeness()                                     │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  - Check required elements present                                  │   │
│  │  - Generate warnings for missing optional elements                  │   │
│  │  - Calculate completeness score (0-100%)                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│        ↓                                                                    │
│  Enhanced Prompt (structured for role-based agent)                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Enhanced Prompt Structure**:
```python
@dataclass
class EnhancedPrompt:
    role_primer: str          # Sets agent's persona and expertise
    task_statement: str       # Clear, specific task description
    context_summary: str      # Relevant background information
    inputs: List[str]         # What's provided to the agent
    outputs: List[str]        # Expected deliverables
    constraints: List[str]    # Boundaries and limitations
    success_criteria: List[str]   # How to measure success
    quality_checklist: List[str]  # Quality gates to pass
    approach_hints: List[str]     # Suggested approach
    pitfalls_to_avoid: List[str]  # Common mistakes
    next_role: Optional[str]      # Who receives output
    handoff_requirements: List[str]  # What next role needs
```

**Role Templates**:
| Role | Primer Focus | Default Outputs | Next Role |
|------|--------------|-----------------|-----------|
| PM | Product vision, user needs | PRD, child issues | Architect |
| Architect | System design, patterns | ADR, tech spec | Engineer |
| Engineer | Implementation, quality | Code, tests, docs | Reviewer |
| Reviewer | Quality assurance, security | Review, decision | None |
| UX | User experience, accessibility | Wireframes, flows | Architect |

**Label-Specific Enhancements**:
| Label | Additional Hints |
|-------|------------------|
| `security` | OWASP Top 10, input validation, auth patterns |
| `api` | REST best practices, versioning, rate limiting |
| `database` | Query optimization, indexing, migrations |
| `performance` | Profiling, caching, async patterns |
| `testing` | TDD, mocking, coverage |

**Issue Type-Specific Success Criteria**:
| Issue Type | Auto-Added Criteria |
|------------|---------------------|
| `bug` | Root cause identified, regression test added |
| `feature` | Architecture documented, security reviewed |
| `story` | Tests pass, documentation updated |
| `epic` | PRD complete, child issues created |

**Example - Raw vs Enhanced**:

*Raw Prompt*:
```json
{
  "title": "Add JWT authentication",
  "description": "Implement JWT-based auth for API endpoints",
  "labels": ["api", "security"]
}
```

*Enhanced Prompt (for Engineer)*:
```markdown
### 🎯 Role
You are a **Software Engineer** focused on clean, secure, maintainable code.

### 📋 Task
**Issue #100**: Add JWT authentication

Implement JWT-based auth for API endpoints

### 📥 Inputs
- Technical specification at docs/specs/SPEC-100.md
- Existing codebase patterns

### 📤 Expected Outputs
- Production-ready code
- Unit tests (≥80% coverage)
- Integration tests
- Updated documentation

### 🚧 Constraints
- Follow existing code patterns
- No breaking changes to existing API
- All tests must pass

### 🎯 Success Criteria
- All tests pass with ≥80% coverage
- No security vulnerabilities (OWASP Top 10)
- PR created and ready for review

### 💡 Suggested Approach
- Follow REST best practices (proper status codes, versioning)
- Use parameterized queries for all database operations
- Follow OWASP Top 10 security guidelines
- Implement proper authentication/authorization checks

### ⚡ Pitfalls to Avoid
- Don't skip input validation
- Don't hardcode secrets or credentials
- Avoid N+1 query patterns

### 🔄 Handoff to Reviewer
- [ ] All tests passing in CI
- [ ] Code follows project patterns
- [ ] Documentation updated
- [ ] Security considerations addressed
```
```

---

### Layer 3: Memory

**Purpose**: Provides persistent knowledge that spans across sessions - the "learning loop".

**Implementation**: [memory.py](../context_md/memory.py)

```
Location: .agent-context/memory.json
CLI:      context-md memory <subcommand>
```

**Components**:

#### 3.1 Lessons Learned
Captures insights from past executions to prevent repeated mistakes.

```python
LessonLearned:
    id: str           # Unique identifier
    issue: int        # Related issue
    issue_type: str   # bug, story, feature
    role: str         # engineer, pm, etc.
    category: str     # security, testing, api
    lesson: str       # The actual lesson
    context: str      # What triggered this
    outcome: str      # success, failure, partial
    effectiveness: float  # 0.0-1.0
    applied_count: int    # Times applied
```

#### 3.2 Execution History
Tracks what was attempted and outcomes for pattern analysis.

```python
ExecutionRecord:
    issue: int
    role: str
    action: str       # What was attempted
    outcome: str      # success, failure, partial
    error_type: str   # Classification if failed
    error_message: str
    duration_seconds: float
    tokens_used: int
```

#### 3.3 Session Context
Maintains continuity between work sessions on the same issue.

```python
SessionContext:
    issue: int
    session_id: str
    summary: str      # What was done
    progress: str     # Where we left off
    blockers: list    # Current blockers
    next_steps: list  # What to do next
    files_modified: list
```

#### 3.4 Metrics
Aggregate success/failure metrics for monitoring and optimization.

```python
Metrics:
    total_executions: int
    success_count: int
    failure_count: int
    by_role: dict[role -> stats]
    by_category: dict[category -> stats]
```

**CLI Commands**:
```bash
# Show memory summary
context-md memory show

# List lessons learned
context-md memory lessons list --role engineer --category security

# Add a lesson
context-md memory lessons add \
    --issue 100 \
    --category security \
    --lesson "Always validate input" \
    --context "Found XSS vulnerability" \
    --outcome failure

# Record execution outcome
context-md memory record 100 \
    --role engineer \
    --action "implement feature" \
    --outcome success

# Show metrics
context-md memory metrics --role engineer

# Save session context
context-md memory session save 100 \
    --summary "Completed auth module" \
    --progress "Starting tests" \
    --blocker "Need API key"

# View session history
context-md memory session show 100 --history
```

---

### Layer 4: Retrieval Context

**Purpose**: Grounds the AI in domain knowledge through dynamically loaded skills.

**Implementation**: [context.py#L324-L374](../context_md/commands/context.py#L324-L374)

```
Location: .github/skills/{category}/{skill}/SKILL.md
Routing:  config.get_skills_for_labels(labels)
```

**Skill Routing Table**:
| Label | Skills Loaded | Description |
|-------|---------------|-------------|
| `api` | #09, #04, #02, #11 | API Design, Security, Testing, Docs |
| `database` | #06, #04, #02 | Database, Security, Testing |
| `security` | #04, #10, #02, #13, #15 | Security, Config, Testing, Types, Logging |
| `frontend` | #21, #22, #02, #11 | Frontend, React, Testing, Docs |
| `bug` | #03, #02, #15 | Error Handling, Testing, Logging |
| `performance` | #05, #06, #02, #15 | Performance, Database, Testing, Logging |
| `ai` | #17, #04 | AI Agent Dev, Security |
| `default` | #02, #04, #11 | Testing, Security, Documentation |

**Available Skills** (25 total):
```
Architecture:
  #01 Core Principles    #04 Security        #07 Scalability
  #05 Performance        #06 Database        #08 Code Organization
  #09 API Design

Development:
  #02 Testing           #03 Error Handling   #10 Configuration
  #11 Documentation     #12 Version Control  #13 Type Safety
  #14 Dependencies      #15 Logging          #18 Code Review
  #19 C# Development    #20 Python           #21 Frontend/UI
  #22 React             #23 Blazor           #24 PostgreSQL
  #25 SQL Server

Operations:
  #16 Remote Git Ops

AI Systems:
  #17 AI Agent Development
```

---

## Context Generation Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      CONTEXT GENERATION FLOW                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  INPUT: context-md context generate <issue>                              │
│                                                                          │
│  1. DETECT ROLE                                                          │
│     ├─ From worktree info                                                │
│     ├─ From Git notes                                                    │
│     └─ Default: engineer                                                 │
│                                                                          │
│  2. LOAD LAYER 1: System Context                                         │
│     └─ Read .github/agents/{role}.agent.md                               │
│                                                                          │
│  3. EXTRACT LAYER 2: User Prompt                                         │
│     ├─ Parse branch name for issue number                                │
│     ├─ Read Git notes for metadata                                       │
│     └─ Extract title, description, criteria                              │
│                                                                          │
│  4. QUERY LAYER 3: Memory                                                │
│     ├─ Get latest session context                                        │
│     ├─ Get relevant lessons learned                                      │
│     ├─ Get success metrics                                               │
│     └─ Get common failure patterns                                       │
│                                                                          │
│  5. ROUTE LAYER 4: Retrieval Context                                     │
│     ├─ Map labels → skill numbers                                        │
│     ├─ Load skill content                                                │
│     └─ Estimate token count                                              │
│                                                                          │
│  6. ASSEMBLE CONTEXT                                                     │
│     └─ Write to .agent-context/context-{issue}.md                        │
│                                                                          │
│  OUTPUT: Complete context file with all 4 layers                         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Generated Context Structure

```markdown
# Context - Issue #<number>

## Metadata
| Field | Value |
|-------|-------|
| Generated | <timestamp> |
| Issue | #<number> |
| Type | <issue_type> |
| Role | <role> |
| Branch | <branch> |
| Skills | <skill_numbers> |

---

## Layer 1: System Context (Governs Behavior)
<role_instructions from .github/agents/{role}.agent.md>

---

## Layer 2: User Prompt (Task Requirements)
### Title
<issue title>

### Description
<issue description>

### Labels
<issue labels>

### Status
<workflow status>

### Dependencies
<related issues>

### Acceptance Criteria
<definition of done>

---

## Layer 3: Memory (Persistent Knowledge)
### Previous Session
<last session summary and progress>

### Lessons Learned
<relevant lessons from past executions>

### Performance
<success rate metrics>

### Common Pitfalls to Avoid
<failure patterns to watch for>

---

## Layer 4: Retrieval Context (Knowledge Grounding)
<loaded skill content based on labels>

---

## References
<external links and documentation>

---

## Execution Checklist
- [ ] Review this context completely
- [ ] Check Layer 3 Memory for lessons learned
- [ ] Generate execution plan
- [ ] Pass pre-flight validation
- [ ] Execute work
- [ ] Pass handoff validation (DoD)
- [ ] Record outcome to Memory layer
- [ ] Update status
```

---

## Benefits of 4-Layer Architecture

### 1. Separation of Concerns
Each layer has a distinct purpose, making the system maintainable and extensible.

### 2. Dynamic Context Assembly
Only loads relevant skills based on task type, reducing token waste.

### 3. Learning Loop
Memory layer enables agents to improve over time through lesson tracking.

### 4. Session Continuity
Agents can resume work with full context of previous sessions.

### 5. Measurable Quality
Metrics tracking enables data-driven optimization.

### 6. Consistent Behavior
System context ensures agents follow workflows regardless of task.

---

## Implementation Files

| Component | File | Purpose |
|-----------|------|---------|
| Context Generation | `context_md/commands/context.py` | Assembles 4 layers |
| Memory Layer | `context_md/memory.py` | Lessons, sessions, metrics |
| Memory CLI | `context_md/commands/memory.py` | Memory management commands |
| Config/Routing | `context_md/config.py` | Skill routing table |
| State Management | `context_md/state.py` | Git-derived state |

---

## Future Enhancements

### Planned
1. **RAG Integration** - Semantic search over codebase for Layer 4
2. **Auto-Lesson Detection** - Automatically extract lessons from outcomes
3. **Cross-Issue Learning** - Share lessons across similar issue types
4. **Memory Summarization** - Compress old memories to save tokens

### Under Consideration
1. **External Knowledge** - Integrate documentation APIs
2. **Team Memory** - Shared lessons across team members
3. **Memory Pruning** - Age-based lesson retirement

---

*Last Updated*: January 30, 2026
*Version*: 1.0
