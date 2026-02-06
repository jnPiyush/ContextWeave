# Microsoft Agent Framework Analysis for Context.md

**Date**: 2026-02-06
**Last Updated**: 2026-02-06
**Scope**: Deep analysis of adopting Microsoft agent frameworks for Context.md functionality
**Frameworks Evaluated**: Semantic Kernel, AutoGen (AgentChat + Core), **Microsoft Agent Framework (Unified, NEW)**

---

## Executive Summary

Context.md implements a custom hub-and-spoke multi-agent orchestration system using Git as the state backbone. Microsoft offers agent frameworks that overlap with several Context.md subsystems. This report maps Context.md capabilities to framework features, evaluates fit, and recommends a **hybrid adoption strategy**.

**UPDATE**: Microsoft has released a **new unified Agent Framework** (`github.com/microsoft/agent-framework`) that converges AutoGen and Semantic Kernel into a single platform. This fundamentally changes the recommendation landscape.

**Bottom Line**: The new **Microsoft Agent Framework** is the preferred adoption target over standalone AutoGen or Semantic Kernel. It provides graph-based workflows, context providers (Mem0, Redis), thread suspend/resume, middleware pipeline, and declarative YAML agents -- all directly relevant to Context.md. The recommendation is to adopt the **Agent Framework** for orchestration, tool integration, and session management, while keeping Context.md's Git-native state, memory/learning, prompt engineering, and 4-layer context systems.

---

## 1. Framework Landscape (Current State)

### 1.1 The Convergence: AutoGen + SK -> Agent Framework

Microsoft previously maintained two separate agent frameworks:

| Framework | Status | Future |
|-----------|--------|--------|
| **Semantic Kernel** | v1.0+ (stable) | Being absorbed into Agent Framework |
| **AutoGen** | v0.4+ (stable) | Being absorbed into Agent Framework |
| **Microsoft Agent Framework** | **Preview** (active development) | **Unified successor to both** |

The new Agent Framework is the **strategic direction** for Microsoft's agent platform. It combines the best of both:
- AutoGen's multi-agent orchestration and Swarm patterns
- Semantic Kernel's plugin system and enterprise middleware
- New capabilities: graph workflows, context providers, thread management

### 1.2 Microsoft Agent Framework (NEW -- Recommended)

| Aspect | Details |
|--------|---------|
| **What** | Unified framework for building AI agents and multi-agent workflows |
| **Repository** | `github.com/microsoft/agent-framework` |
| **Languages** | Python, C# |
| **Status** | Public Preview (`pip install agent-framework --pre`) |
| **Core Strength** | Graph-based workflows, context providers, middleware, thread management |
| **Agent Types** | ChatAgent (base), with extensible agent patterns |
| **Orchestration** | Graph-based workflows with checkpointing and streaming |
| **Memory** | Context Providers (Mem0, Redis, Azure AI Search, Simple) |
| **State** | Thread suspend/resume with persistent storage (Redis, custom) |
| **Tools** | Native function calling, MCP integration |
| **Observability** | Built-in OpenTelemetry integration |
| **UI** | DevUI for debugging agent interactions |

**Key Components**:
- **ChatAgent** -- Base agent class with chat client integration
- **Workflows** -- Graph-based multi-step execution with edges, conditions, checkpointing
- **Context Providers** -- Pluggable memory/context injection (invoked before/after each turn)
- **Middleware Pipeline** -- Request/response processing chain (auth, logging, rate limiting)
- **Threads** -- Conversation state with suspend/resume and persistent backing stores
- **Tools** -- Python function-based tool definitions with auto-schema generation
- **Declarative Agents** -- YAML-based agent definitions (maps closely to `.agent.md` files)
- **DevUI** -- Web-based debugger for agent interactions

### 1.3 Semantic Kernel (SK) -- Legacy Analysis

| Aspect | Details |
|--------|---------|
| **What** | Lightweight SDK for building AI agents with LLM integration |
| **Languages** | Python, C#, Java |
| **Maturity** | v1.0+ (production-ready) |
| **Core Strength** | Plugin system, function calling, enterprise-grade middleware |
| **Agent Orchestration** | Sequential, Concurrent, Handoff, GroupChat, Magentic patterns |
| **Memory** | Plugin-based (vector stores, embeddings) -- experimental in Python |
| **Process Framework** | Event-driven workflow steps (experimental) |

### 1.4 AutoGen -- Legacy Analysis

| Aspect | Details |
|--------|---------|
| **What** | Framework for building multi-agent conversational applications |
| **Languages** | Python, .NET |
| **Maturity** | Stable (v0.4+) |
| **Core Strength** | Multi-agent conversation, Swarm handoffs, team orchestration |
| **Agent Types** | AssistantAgent, CodeExecutorAgent, UserProxyAgent |
| **State** | Full save/load state persistence (JSON serializable) |
| **Teams** | RoundRobinGroupChat, SelectorGroupChat, Swarm, MagenticOneGroupChat |

---

## 2. Feature Mapping: Context.md vs Microsoft Agent Framework

This section maps each Context.md subsystem against the **new unified Agent Framework** (primary) and the legacy frameworks (for reference).

### 2.1 Agent Orchestration & Routing

| Context.md Current | Agent Framework (NEW) | AutoGen (Legacy) | SK (Legacy) |
|-|-|-|-|
| Agent X hub routes by labels/status | **Graph-based workflows** with conditional edges | Swarm with HandoffMessage | HandoffOrchestration |
| Sequential: PM->UX->Architect->Engineer->Reviewer | **Workflow graph**: nodes = agents, edges = transitions | RoundRobinGroupChat | SequentialOrchestration |
| Label-based routing in agent-x.yml | **Conditional routing** in graph definition | SelectorGroupChat | KernelFunctionSelectionStrategy |
| Status-driven gates (Projects V2) | **Checkpointing** + conditional edge evaluation | Termination conditions | Process Framework (experimental) |

**Analysis**:

The Agent Framework's **graph-based workflows** are the most natural fit for Context.md's orchestration:

```python
from agent_framework import Workflow, ChatAgent

# Define the agent workflow as a graph
workflow = Workflow()

# Add agent nodes
workflow.add_node("pm", pm_agent)
workflow.add_node("architect", architect_agent)
workflow.add_node("engineer", engineer_agent)
workflow.add_node("reviewer", reviewer_agent)

# Define edges (routing)
workflow.add_edge("pm", "architect", condition=lambda result: "ready" in result)
workflow.add_edge("architect", "engineer", condition=lambda result: "spec_complete" in result)
workflow.add_edge("engineer", "reviewer")
workflow.add_edge("reviewer", "engineer", condition=lambda result: "rework" in result)
workflow.add_edge("reviewer", "__end__", condition=lambda result: "approved" in result)

# Run with streaming and checkpointing
result = await workflow.run(task="Implement feature #42", stream=True)
```

This maps directly to Context.md's hub-and-spoke pattern, with key advantages:
- **Conditional edges** replace static label routing with dynamic decisions
- **Checkpointing** allows resume from any point in the workflow
- **Streaming** provides real-time visibility into agent progress
- **Graph structure** matches the PM->Architect->Engineer->Reviewer flow exactly

**Recommendation**: **Adopt Agent Framework graph workflows** for orchestration. This is more powerful than AutoGen's Swarm (which only supports linear handoffs) and more mature than SK's Process Framework.

### 2.2 Agent Definitions & Instructions

| Context.md Current | Agent Framework (NEW) | AutoGen (Legacy) |
|-|-|-|
| `.github/agents/{role}.agent.md` with YAML frontmatter | **Declarative agents** (YAML-based definitions) | AssistantAgent with system_message |
| Constraints (CAN/CANNOT) in markdown | Tool whitelist + middleware enforcement | Tool whitelist per agent |
| Role-specific templates in prompt.py | System message + context providers | system_message per agent |

**Analysis**:

The Agent Framework introduces **declarative agents** -- YAML-based agent definitions:

```yaml
# declarative_agent.yaml
name: engineer
description: Software engineer focused on clean, maintainable code
instructions: |
  You are a Software Engineer. Follow TDD practices.
  Validate all inputs. Follow OWASP Top 10 guidelines.
tools:
  - run_tests
  - commit_code
  - lint_code
context_providers:
  - type: mem0
    config:
      user_id: "project-context"
```

This is closer to Context.md's `.agent.md` files than anything in AutoGen or SK. However, Context.md's agent definitions are still **richer**:

```markdown
# Context.md agent definition uniquely includes:
- Maturity level (stable/beta/scaffold)
- Trigger conditions (when agent activates)
- Validation scripts (pre/post execution)
- Constraints (CAN/CANNOT lists)
- File boundaries (can modify / cannot modify)
- Delivery specifications (required outputs)
- Handoff requirements (what to pass to next agent)
```

**Recommendation**: **Keep Context.md agent definitions** but add an adapter that generates Agent Framework declarative agent configs at runtime. Context.md `.agent.md` files serve as the source of truth; the adapter produces framework-compatible YAML.

### 2.3 Context & Memory

| Context.md Current | Agent Framework (NEW) | AutoGen (Legacy) | SK (Legacy) |
|-|-|-|-|
| `memory.py`: LessonLearned, ExecutionRecord, SessionContext | **Context Providers** (Mem0, Redis, Azure AI Search, Simple) | No persistent memory | Vector memory (experimental) |
| Lesson effectiveness scoring (0.0-1.0) | No equivalent | No equivalent | No equivalent |
| Learning loop (monthly pattern analysis) | No equivalent | No equivalent | No equivalent |
| 4-Layer Context assembly | Context Providers inject context per turn | No equivalent | No equivalent |

**Analysis**:

The Agent Framework's **Context Providers** are the most relevant new capability for Context.md:

```python
from agent_framework.context import Mem0ContextProvider, AggregateContextProvider

# Context providers inject context before each agent turn
class ContextMdProvider:
    """Custom context provider that injects Context.md's 4-layer context."""

    async def invoking(self, agent, thread, messages):
        """Called BEFORE each agent turn -- inject context."""
        # Layer 1: System Context (agent instructions)
        # Layer 2: Enhanced prompt (from PromptEngineer)
        # Layer 3: Memory (lessons, execution records)
        # Layer 4: Skills (relevant skill documents)
        context = generate_4layer_context(agent.name, thread.metadata)
        messages.insert(0, SystemMessage(content=context))

    async def invoked(self, agent, thread, messages, response):
        """Called AFTER each agent turn -- record outcomes."""
        record_execution_outcome(agent.name, response)

# Use with agent
agent = ChatAgent(
    name="engineer",
    context_providers=[
        ContextMdProvider(),           # Context.md's 4-layer context
        Mem0ContextProvider(user_id="project"),  # Vector similarity (optional)
    ]
)
```

The **Context Provider lifecycle** (`invoking`/`invoked`) maps naturally to Context.md's architecture:
- `invoking` = inject 4-layer context before the agent processes
- `invoked` = record outcomes to memory after the agent responds

Available built-in providers:

| Provider | What It Does | Relevance to Context.md |
|----------|--------------|------------------------|
| **Mem0** | Vector-based memory with semantic search | Could enhance Layer 4 (skill retrieval) with similarity search |
| **Redis** | Key-value context storage | Could cache generated context for faster re-use |
| **Azure AI Search** | Full-text + vector search over documents | Could power skill document retrieval at scale |
| **Simple** | In-memory context storage | Useful for session-scoped context |
| **Aggregate** | Combines multiple providers | Perfect for composing Context.md's 4 layers |

**However**, Context.md's memory system remains significantly more advanced:
1. **Lesson effectiveness scoring** (0.0-1.0 over time) -- no framework equivalent
2. **Execution history with error classification** -- no framework equivalent
3. **Learning loop automation** (monthly pattern analysis -> instruction PRs) -- no framework equivalent
4. **Contextual lesson relevance scoring** (issue type + role + category) -- no framework equivalent

**Recommendation**: **Keep Context.md's memory system** and implement it as a **custom Context Provider** for the Agent Framework. This gives the best of both worlds: Context.md's advanced learning + the framework's lifecycle hooks. Optionally add Mem0 as a supplementary provider for semantic search over skills.

### 2.4 State Management & Session Continuity

| Context.md Current | Agent Framework (NEW) | AutoGen (Legacy) |
|-|-|-|
| `.agent-context/state.json` + Git notes + worktrees | **Threads** with suspend/resume + persistent stores | save_state/load_state (JSON) |
| Keyring for secrets | Middleware pipeline (auth) | Environment variables |
| Split state (JSON + Git + GitHub API) | Thread stores (Redis, custom) | Unified JSON state |

**Analysis**:

The Agent Framework's **Thread management** directly addresses Context.md's session continuity needs:

```python
from agent_framework.threads import Thread, RedisThreadStore

# Create a persistent thread for an issue
thread = Thread(
    id=f"issue-{issue_number}",
    store=RedisThreadStore()  # or custom GitThreadStore
)

# Run agent with thread context
result = await agent.run(
    task="Implement feature",
    thread=thread
)

# Thread automatically persists conversation state
# Later: suspend and resume
await thread.suspend()  # Saves state to store

# ... time passes, session ends ...

# Resume exactly where we left off
thread = await Thread.resume(
    id=f"issue-{issue_number}",
    store=RedisThreadStore()
)
result = await agent.run(
    task="Continue implementation",
    thread=thread  # Full conversation history restored
)
```

The Thread system supports custom backing stores, enabling a **GitThreadStore**:

```python
class GitThreadStore:
    """Custom thread store that persists to Git notes."""

    def __init__(self, repo_root: Path, state: State):
        self.repo_root = repo_root
        self.state = state

    async def save(self, thread_id: str, data: dict):
        # Save to .agent-context/sessions/ + Git note
        session_file = self.repo_root / ".agent-context" / "sessions" / f"{thread_id}.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps(data, indent=2))
        self.state.set_branch_note(thread_id, {"session": str(session_file)})

    async def load(self, thread_id: str) -> Optional[dict]:
        session_file = self.repo_root / ".agent-context" / "sessions" / f"{thread_id}.json"
        if session_file.exists():
            return json.loads(session_file.read_text())
        return None
```

This is a major improvement over AutoGen's `save_state()`/`load_state()` because:
- **Suspend/resume is a first-class concept** (not manual JSON serialization)
- **Custom stores** allow Git-native persistence
- **Thread identity** maps naturally to issue numbers
- **Automatic state management** (no manual save calls needed)

**Recommendation**: **Adopt Agent Framework Threads** with a custom `GitThreadStore`. This bridges the framework's session management with Context.md's Git-native state, providing automatic suspend/resume without losing the Git audit trail.

### 2.5 Prompt Engineering

| Context.md Current | Agent Framework (NEW) | AutoGen (Legacy) | SK (Legacy) |
|-|-|-|-|
| PromptEngineer class with role templates | System message + context providers | system_message per agent | Kernel prompt templates |
| Constraint extraction from raw prompts | No equivalent | No equivalent | No equivalent |
| Chain-of-thought generation per role | No built-in | No built-in | No built-in |
| Success criteria generation | No equivalent | No equivalent | No equivalent |
| Prompt completeness validation (scoring) | No equivalent | No equivalent | No equivalent |

**Analysis**:

No Microsoft framework -- including the new Agent Framework -- provides anything comparable to Context.md's prompt engineering pipeline:

- **Context.md**: Raw prompt -> role template -> constraint extraction -> success criteria -> approach hints -> pitfalls -> handoff requirements -> completeness validation (scoring)
- **Agent Framework**: System message + context providers -> LLM
- **AutoGen**: system_message + task -> agent.run()
- **SK**: System message + user message -> LLM

The Context Provider mechanism could be used to inject enhanced prompts, but the **enhancement logic itself** must remain in Context.md.

**Recommendation**: **Keep Context.md prompt engineering entirely**. Implement it within a custom Context Provider so the enhanced prompt is injected into every Agent Framework agent turn automatically.

### 2.6 Tool Integration

| Context.md Current | Agent Framework (NEW) | AutoGen (Legacy) | SK (Legacy) |
|-|-|-|-|
| GitHub CLI (`gh`) via subprocess | **Python function tools** + **MCP integration** | Tools (Python functions, MCP) | Plugins (native, OpenAPI, MCP) |
| Git commands via subprocess | Declarative tool definitions | tools=[func1, func2] per agent | Kernel.add_plugin() |
| No structured tool registry | Auto-schema generation from type hints | Auto-schema generation | Auto-schema generation |
| No function calling | **Native function calling** | Native function calling | Native function calling |

**Analysis**:

The Agent Framework's tool system is straightforward and directly applicable:

```python
from agent_framework import ChatAgent

# Tools are just Python functions with type hints
async def run_tests(path: str = "tests/") -> str:
    """Run project test suite and return results."""
    result = subprocess.run(["pytest", path, "-v"], capture_output=True, text=True)
    return result.stdout

async def commit_code(message: str, issue: int) -> str:
    """Commit staged changes with issue reference."""
    full_msg = f"{message} (#{issue})"
    result = subprocess.run(["git", "commit", "-m", full_msg], capture_output=True, text=True)
    return result.stdout

async def create_branch(name: str) -> str:
    """Create and checkout a new Git branch."""
    result = subprocess.run(["git", "checkout", "-b", name], capture_output=True, text=True)
    return result.stdout

# Register tools with agent
agent = ChatAgent(
    name="engineer",
    tools=[run_tests, commit_code, create_branch],
    ...
)
```

The framework also supports **MCP (Model Context Protocol) integration**, which Context.md already has configured in `.vscode/mcp.json`:

```python
from agent_framework.tools import MCPToolProvider

# Connect to existing MCP servers
mcp_tools = MCPToolProvider(server_url="http://localhost:3000")
agent = ChatAgent(
    name="engineer",
    tools=[run_tests, commit_code] + mcp_tools.get_tools(),
)
```

**Recommendation**: **Adopt Agent Framework tools** for structured tool integration. Wrap existing subprocess calls as typed Python functions, and integrate MCP servers for extended tool availability.

### 2.7 Middleware Pipeline

| Context.md Current | Agent Framework (NEW) | AutoGen (Legacy) | SK (Legacy) |
|-|-|-|-|
| Git hooks (pre-commit, pre-push, post-merge) | **Middleware pipeline** (request/response processing) | No middleware | Plugin filters |
| Validation scripts (handoff, DoD, alignment) | Middleware intercepts every agent call | No equivalent | Basic filters |
| No request/response interception | Full lifecycle hooks | No equivalent | Limited |

**Analysis**:

The Agent Framework introduces a **middleware pipeline** -- a concept new across all Microsoft agent frameworks:

```python
from agent_framework.middleware import Middleware

class ValidationMiddleware(Middleware):
    """Validates agent actions against Context.md constraints."""

    async def process(self, request, next_handler):
        agent_name = request.agent.name

        # Pre-execution: check file boundaries
        if hasattr(request, 'tool_call'):
            tool = request.tool_call
            if not self._check_file_boundaries(agent_name, tool):
                return ErrorResponse("Action violates file boundary constraints")

        # Execute the next middleware/agent
        response = await next_handler(request)

        # Post-execution: record to memory
        self._record_execution(agent_name, request, response)

        return response

class SecurityMiddleware(Middleware):
    """Runs security checks on agent outputs."""

    async def process(self, request, next_handler):
        response = await next_handler(request)

        # Check for secrets in output
        if self._contains_secrets(response.content):
            return ErrorResponse("Output contains potential secrets")

        return response

# Apply middleware to all agents
agent = ChatAgent(
    name="engineer",
    middleware=[ValidationMiddleware(), SecurityMiddleware()],
)
```

This maps naturally to Context.md's validation infrastructure:
- **Pre-commit checks** -> SecurityMiddleware
- **File boundary enforcement** -> ValidationMiddleware
- **DoD validation** -> CompletionMiddleware
- **Handoff validation** -> HandoffMiddleware

**Recommendation**: **Adopt Agent Framework middleware** for agent-level validation. This complements (not replaces) Git hooks -- hooks validate at the Git level, middleware validates at the agent level.

### 2.8 Observability

| Context.md Current | Agent Framework (NEW) | AutoGen (Legacy) | SK (Legacy) |
|-|-|-|-|
| CLI dashboard (`context-md status --watch`) | **OpenTelemetry integration** + **DevUI** | Console streaming | No built-in |
| Web dashboard (GitHub Pages) | Traces, spans, metrics out of the box | No equivalent | Application Insights (Azure) |
| Metrics in `.agent-context/metrics.json` | Standard observability pipeline | No equivalent | Limited |

**Analysis**:

The Agent Framework provides built-in observability via **OpenTelemetry**:

```python
from agent_framework.observability import enable_telemetry

# Enable tracing for all agent operations
enable_telemetry(
    service_name="context-md",
    exporter="console"  # or jaeger, zipkin, azure_monitor
)

# Every agent call automatically generates:
# - Traces (full execution path)
# - Spans (individual tool calls, LLM requests)
# - Metrics (token usage, latency, success rates)
```

It also includes **DevUI** -- a web-based debugger:
- View agent conversation history
- Inspect tool calls and responses
- Debug routing decisions
- Replay agent interactions

**Recommendation**: **Adopt OpenTelemetry integration** for production monitoring. **Evaluate DevUI** as a complement to the existing dashboard -- it provides agent-level debugging that the current dashboard lacks.

---

## 3. Updated Recommended Architecture

### 3.1 Hybrid Architecture Overview (Agent Framework Edition)

```
+----------------------------------------------------------------------+
|                    CONTEXT.MD v2 ARCHITECTURE                          |
|              (with Microsoft Agent Framework integration)               |
+----------------------------------------------------------------------+
|                                                                        |
|  KEEP (Context.md Native)             ADOPT (Agent Framework)          |
|  ========================             ========================          |
|                                                                        |
|  [Git-Native State]                  [Graph Workflows]                 |
|  - Worktrees                         - Agent orchestration graphs      |
|  - Branches                          - Conditional edge routing        |
|  - Git notes                         - Checkpointing & resume          |
|  - Issue tracking                    - Streaming output                |
|                                                                        |
|  [Memory System]                     [Context Providers]               |
|  - LessonLearned                     - Custom ContextMdProvider        |
|  - ExecutionRecord                   - Mem0 (optional, for skills)     |
|  - SessionContext                    - Lifecycle hooks (invoking/       |
|  - Learning loop                       invoked)                        |
|                                                                        |
|  [Prompt Engineering]                [Threads]                         |
|  - PromptEngineer class              - Suspend/resume sessions         |
|  - Role templates                    - GitThreadStore (custom)         |
|  - Constraint extraction             - Issue-based thread identity     |
|  - Success criteria                                                    |
|                                                                        |
|  [4-Layer Context]                   [Tools & MCP]                     |
|  - System Context (L1)               - Typed Python function tools     |
|  - User Prompt (L2)                  - MCP server integration          |
|  - Memory (L3)                       - Auto-schema generation          |
|  - Skills (L4)                                                         |
|                                                                        |
|  [GitHub Integration]                [Middleware Pipeline]              |
|  - Projects V2 (GraphQL)             - Validation middleware           |
|  - Actions (CI/CD)                   - Security middleware             |
|  - Hooks (Git-level)                 - File boundary enforcement       |
|                                                                        |
|  [Skills Library]                    [Observability]                    |
|  - 27 skill documents                - OpenTelemetry integration       |
|  - Smart label routing               - DevUI (agent debugging)         |
|  - Category matching                                                   |
|                                                                        |
|  [Agent Definitions]                 [Declarative Agents]              |
|  - .agent.md files (source of truth) - YAML adapter (generated from   |
|  - Rich constraints & boundaries       .agent.md at runtime)           |
|                                                                        |
+----------------------------------------------------------------------+
```

### 3.2 What to Keep (Context.md Strengths)

| Component | Why Keep It |
|-----------|-------------|
| **Git-native state** | Unique differentiator. No framework offers Git worktree isolation, branch-per-issue, or git-notes metadata. Offline-capable. |
| **Memory system** | Most advanced learning system across all frameworks. Lesson effectiveness tracking, error classification, and automated learning loops have no equivalent. |
| **Prompt engineering** | Secret sauce for >95% success rate. No framework enhances prompts before LLM calls. |
| **4-layer context** | Comprehensive context assembly. Frameworks only provide system_message + context injection (2 layers). Context.md's structured 4-layer approach is more methodical. |
| **GitHub integration** | Projects V2, Actions, hooks -- deeply integrated with development workflow. |
| **Skills library** | 27 domain-specific knowledge documents with smart label routing. No framework equivalent. |
| **Agent definitions** | Richer than any framework (constraints, file boundaries, validation scripts, maturity levels, handoff specifications). |

### 3.3 What to Adopt (Agent Framework Strengths)

| Component | What It Provides | Why Adopt |
|-----------|-----------------|-----------|
| **Graph Workflows** | Multi-agent orchestration with conditional routing | Replaces static label routing with dynamic graph-based decisions. Checkpointing enables resume. |
| **Context Providers** | Lifecycle hooks for context injection | Natural integration point for Context.md's 4-layer context. `invoking`/`invoked` hooks align perfectly. |
| **Threads** | Session suspend/resume with custom stores | Addresses session continuity gap. Custom GitThreadStore preserves Git audit trail. |
| **Tools** | Typed Python functions with auto-schema | Replaces hardcoded subprocess calls with structured, LLM-callable tools. |
| **Middleware** | Request/response pipeline | Agent-level validation complements Git hooks. Enforces constraints programmatically. |
| **OpenTelemetry** | Built-in observability | Production monitoring and debugging without custom instrumentation. |
| **MCP Integration** | External tool protocol | Connects to existing MCP servers configured in `.vscode/mcp.json`. |

### 3.4 What NOT to Adopt

| Component | Why Skip |
|-----------|----------|
| **Agent Framework's built-in memory** | Context.md's structured memory with effectiveness tracking is far superior to Mem0/Redis for this domain |
| **Declarative agents as source of truth** | Context.md's `.agent.md` files are richer; use framework YAML as a generated output, not the source |
| **DevUI as primary dashboard** | Evaluate alongside existing dashboard, don't replace it yet |
| **Standalone AutoGen** | Superseded by Agent Framework; no reason to adopt legacy separately |
| **Standalone Semantic Kernel** | Superseded by Agent Framework; no reason to adopt legacy separately |
| **Azure-specific features** | Keep the system cloud-agnostic and offline-capable |

---

## 4. Implementation Plan

### Phase 1: Foundation -- Tool Registry + Agent Wrappers (Low Risk)

Create Agent Framework agents that wrap Context.md's existing functionality:

```python
# context_md/framework/agents.py
from agent_framework import ChatAgent
from context_md.prompt import PromptEngineer
from context_md.memory import Memory

class ContextMdAgentFactory:
    """Creates Agent Framework agents using Context.md's enhanced prompts."""

    def __init__(self, repo_root: Path, model_client):
        self.repo_root = repo_root
        self.memory = Memory(repo_root)
        self.prompt_engineer = PromptEngineer()
        self.model_client = model_client
        self.tool_registry = ToolRegistry(repo_root)

    def create_agent(self, role: str, issue_number: int, issue_type: str,
                     labels: list[str]) -> ChatAgent:
        """Create an agent with Context.md enhanced prompts and tools."""

        # Generate enhanced system message using Context.md's pipeline
        enhanced = self.prompt_engineer.enhance_prompt(
            raw_prompt="",
            role=role,
            issue_number=issue_number,
            issue_type=issue_type,
            labels=labels
        )

        # Get relevant lessons from memory
        lessons = self.memory.get_lessons_for_context(issue_type, role, labels)

        system_message = build_system_message(enhanced, lessons)

        return ChatAgent(
            name=role,
            model_client=self.model_client,
            system_message=system_message,
            tools=self.tool_registry.get_tools(role),
            context_providers=[ContextMdProvider(self.repo_root, self.memory)],
            middleware=[ValidationMiddleware(role, self.repo_root)],
        )
```

Tool registry wrapping existing subprocess calls:

```python
# context_md/framework/tools.py

class ToolRegistry:
    """Registry of tools available to Context.md agents."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def get_tools(self, role: str) -> list:
        """Get tools available for a specific role."""
        base = [self.run_tests, self.search_code]
        role_tools = {
            "pm": [self.create_issue, self.list_issues, self.create_prd],
            "architect": [self.create_adr, self.create_spec, self.analyze_deps],
            "engineer": [self.commit_code, self.lint_code, self.update_docs],
            "reviewer": [self.get_diff, self.add_comment, self.approve_pr],
            "ux": [self.create_wireframe, self.create_ux_doc],
        }
        return base + role_tools.get(role, [])

    async def run_tests(self, path: str = "tests/") -> str:
        """Run project test suite and return results."""
        result = subprocess.run(
            ["pytest", path, "-v"],
            cwd=self.repo_root, capture_output=True, text=True
        )
        return result.stdout if result.returncode == 0 else f"FAILED:\n{result.stderr}"

    async def commit_code(self, message: str, issue: int) -> str:
        """Commit staged changes with issue reference."""
        full_msg = f"{message} (#{issue})"
        result = subprocess.run(
            ["git", "commit", "-m", full_msg],
            cwd=self.repo_root, capture_output=True, text=True
        )
        return result.stdout

    # ... additional tools ...
```

**Risk**: Low -- wraps existing code, no replacement
**Value**: Structured tool calling, LLM-driven tool selection

### Phase 2: Graph Workflow Orchestration (Medium Risk)

Implement graph-based multi-agent orchestration:

```python
# context_md/framework/orchestrator.py
from agent_framework import Workflow

class IssueOrchestrator:
    """Orchestrates multi-agent workflow for an issue using graph workflows."""

    def __init__(self, factory: ContextMdAgentFactory, state: State):
        self.factory = factory
        self.state = state

    async def orchestrate(self, issue_number: int, issue_type: str,
                          labels: list[str]) -> dict:
        """Run full agent workflow for an issue."""

        # Create agents
        agents = {
            role: self.factory.create_agent(role, issue_number, issue_type, labels)
            for role in self._get_roles_for_type(issue_type)
        }

        # Build workflow graph
        workflow = Workflow()

        for name, agent in agents.items():
            workflow.add_node(name, agent)

        # Define routing based on issue type
        if issue_type == "story":
            workflow.add_edge("pm", "architect")
            workflow.add_edge("architect", "engineer")
            workflow.add_edge("engineer", "reviewer")
            workflow.add_edge("reviewer", "engineer",
                            condition=lambda r: "rework" in r.lower())
            workflow.add_edge("reviewer", "__end__",
                            condition=lambda r: "approved" in r.lower())
        elif issue_type == "bug":
            workflow.add_edge("engineer", "reviewer")
            workflow.add_edge("reviewer", "__end__")

        # Create thread for session persistence
        thread = Thread(
            id=f"issue-{issue_number}",
            store=GitThreadStore(self.factory.repo_root, self.state)
        )

        # Run with streaming
        result = await workflow.run(
            task=f"Complete issue #{issue_number}",
            thread=thread,
            stream=True
        )

        # Record outcome to memory
        self.factory.memory.record_execution(
            issue_number, "workflow", "orchestrate",
            "success" if result.success else "failure"
        )

        return result
```

**Risk**: Medium -- new orchestration path alongside existing GitHub Actions
**Value**: Dynamic routing, checkpointing, real-time streaming, conversation continuity

### Phase 3: Thread + State Integration (Low Risk)

Implement GitThreadStore bridging framework threads with Git-native state:

```python
# context_md/framework/thread_store.py
from agent_framework.threads import ThreadStore

class GitThreadStore(ThreadStore):
    """Thread store backed by Git notes and local JSON files."""

    def __init__(self, repo_root: Path, state: State):
        self.repo_root = repo_root
        self.state = state
        self.sessions_dir = repo_root / ".agent-context" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, thread_id: str, data: dict) -> None:
        """Persist thread state to file + Git note."""
        state_file = self.sessions_dir / f"{thread_id}.json"
        state_file.write_text(json.dumps(data, indent=2))

        # Cross-reference in Git note for discoverability
        self.state.set_branch_note(thread_id, {
            "session_file": str(state_file),
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(data.get("messages", []))
        })

    async def load(self, thread_id: str) -> Optional[dict]:
        """Load thread state from persistent storage."""
        state_file = self.sessions_dir / f"{thread_id}.json"
        if state_file.exists():
            return json.loads(state_file.read_text())
        return None

    async def delete(self, thread_id: str) -> None:
        """Remove thread state (e.g., on issue completion)."""
        state_file = self.sessions_dir / f"{thread_id}.json"
        if state_file.exists():
            state_file.unlink()
```

**Risk**: Low -- additive integration, no existing code replaced
**Value**: Session suspend/resume, conversation continuity across sessions

### Phase 4: Context Provider + Middleware (Low Risk)

Implement Context.md's 4-layer context as a Context Provider:

```python
# context_md/framework/context_provider.py
from agent_framework.context import ContextProvider

class ContextMdProvider(ContextProvider):
    """Injects Context.md's 4-layer context into every agent turn."""

    def __init__(self, repo_root: Path, memory: Memory):
        self.repo_root = repo_root
        self.memory = memory

    async def invoking(self, agent, thread, messages):
        """Inject context BEFORE agent processes."""
        issue_num = thread.metadata.get("issue_number")
        role = agent.name

        # Layer 3: Inject relevant lessons
        lessons = self.memory.get_lessons_for_context(
            thread.metadata.get("issue_type", ""),
            role,
            thread.metadata.get("labels", [])
        )
        if lessons:
            lesson_text = "\n".join(
                f"- [{l.category}] {l.lesson} (effectiveness: {l.effectiveness})"
                for l in lessons
            )
            messages.append(SystemMessage(
                content=f"## Relevant Lessons from Previous Work\n{lesson_text}"
            ))

    async def invoked(self, agent, thread, messages, response):
        """Record outcomes AFTER agent responds."""
        # Record execution for learning loop
        self.memory.record_execution(
            issue=thread.metadata.get("issue_number", 0),
            role=agent.name,
            action="agent_turn",
            outcome="success"
        )
```

Implement validation as middleware:

```python
# context_md/framework/middleware.py
from agent_framework.middleware import Middleware

class FileBarrierMiddleware(Middleware):
    """Enforces file boundary constraints from agent definitions."""

    def __init__(self, role: str, repo_root: Path):
        self.role = role
        self.boundaries = self._load_boundaries(role, repo_root)

    async def process(self, request, next_handler):
        # Check if tool call targets allowed files
        if hasattr(request, 'tool_call'):
            target_file = self._extract_file_target(request.tool_call)
            if target_file and not self._is_allowed(target_file):
                return ErrorResponse(
                    f"Agent '{self.role}' cannot modify '{target_file}'. "
                    f"Allowed: {self.boundaries['can_modify']}"
                )

        return await next_handler(request)
```

**Risk**: Low -- uses framework extension points, no core changes
**Value**: Automated context injection, constraint enforcement

### Phase 5: CLI Integration (Low Risk)

Add a new CLI command for live orchestration:

```python
# Addition to context_md/commands/run.py

@click.command("run")
@click.argument("issue_number", type=int)
@click.option("--role", help="Run single agent role")
@click.option("--stream/--no-stream", default=True, help="Enable streaming output")
@click.pass_context
async def run_cmd(ctx, issue_number, role, stream):
    """Run agent workflow for an issue using Microsoft Agent Framework.

    Examples:
        context-md run 42           # Full workflow
        context-md run 42 --role engineer  # Single agent
    """
    repo_root = ctx.obj["repo_root"]
    state = ctx.obj["state"]

    # Initialize framework
    model_client = create_model_client()  # From config
    factory = ContextMdAgentFactory(repo_root, model_client)

    if role:
        # Single agent mode
        agent = factory.create_agent(role, issue_number, ...)
        result = await agent.run(task=f"Work on issue #{issue_number}")
    else:
        # Full orchestration
        orchestrator = IssueOrchestrator(factory, state)
        result = await orchestrator.orchestrate(issue_number, ...)

    click.echo(result.summary)
```

**Risk**: Low -- new command, no existing commands modified
**Value**: Developer can run `context-md run 42` for live multi-agent execution

---

## 5. Comparison: Agent Framework vs Legacy Frameworks

### 5.1 Why Agent Framework Over AutoGen Alone

| Feature | Agent Framework | AutoGen |
|---------|----------------|---------|
| Orchestration | **Graph workflows** (conditional edges, checkpoints) | Swarm (linear handoffs only) |
| Memory | **Context Providers** (pluggable, lifecycle hooks) | No persistent memory |
| State | **Threads** (suspend/resume, custom stores) | save_state/load_state (manual) |
| Middleware | **Full pipeline** (pre/post processing) | None |
| Observability | **OpenTelemetry** built-in | Console only |
| Declarative agents | **YAML definitions** | Code only |
| Long-term support | **Strategic direction** for Microsoft | Being converged into Agent Framework |

### 5.2 Why Agent Framework Over Semantic Kernel Alone

| Feature | Agent Framework | Semantic Kernel |
|---------|----------------|-----------------|
| Multi-agent | **Graph workflows** with native multi-agent | Orchestration patterns (newer, less mature) |
| Context management | **Context Providers** (dedicated subsystem) | Plugin-based (bolted on) |
| Thread management | **Native threads** with suspend/resume | No equivalent |
| Middleware | **Dedicated pipeline** | Plugin filters (limited) |
| Python support | **First-class** (co-developed with C#) | C# primary, Python secondary |
| Complexity | **Focused on agents** | Broader SDK (kernel, plugins, connectors) |

### 5.3 Trade-Off Summary

| Approach | Pros | Cons |
|----------|------|------|
| **Agent Framework (Recommended)** | Unified platform, graph workflows, context providers, threads, middleware, future-proof | Preview status, API may change, smaller community (for now) |
| **AutoGen Swarm** | Stable, proven Swarm pattern, larger community | Being superseded, no middleware, no context providers |
| **Semantic Kernel** | Production-ready, enterprise features | Heavier, C#-centric, being superseded |
| **Status Quo (no framework)** | No dependencies, full control, offline | No function calling, static routing, no session continuity |

---

## 6. Dependency & Compatibility

### Agent Framework Dependencies

```toml
# pyproject.toml additions
[project.optional-dependencies]
agents = [
    "agent-framework>=0.1.0",       # Core framework (preview)
    "agent-framework[openai]",       # OpenAI chat client
    # Optional context providers:
    # "agent-framework[mem0]",       # Mem0 vector memory
    # "agent-framework[redis]",      # Redis thread store
]
```

**Compatibility**:
- Python 3.10+ (matches Context.md requirement)
- Async/await based (Context.md is currently sync -- requires gradual migration)
- Model-agnostic (OpenAI, Azure OpenAI, Anthropic via chat client adapters)
- Preview release -- API may change before GA

### Migration Considerations

| Consideration | Impact | Mitigation |
|---------------|--------|------------|
| **Async migration** | Context.md is currently sync | Gradual: start with `run` command only, expand later |
| **Preview stability** | API may change | Pin version, isolate framework code in `context_md/framework/` |
| **Offline operation** | Framework requires LLM API | Keep existing CLI commands as sync fallback |
| **Testing** | New async test patterns needed | Add `pytest-asyncio`, create integration test suite |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Agent Framework breaking changes (preview) | **High** | Medium | Pin version, isolate in `framework/` package |
| Async migration complexity | High | Medium | Gradual migration, keep sync CLI commands |
| LLM cost for orchestration routing | Low | Low | Use small model for routing decisions |
| Framework abandoned before GA | **Low** | High | Microsoft strategic investment; convergence of two major projects |
| Performance regression | Low | Medium | Benchmark before/after |
| Offline operation loss | Medium | Medium | Keep existing CLI as fallback without framework |
| AutoGen/SK deprecated before Agent Framework is stable | Medium | Medium | Both will be maintained during transition period |

---

## 8. Updated Recommendation Matrix

### Per-Feature Recommendation

| Context.md Feature | Recommendation | Target | Confidence |
|-|-|-|-|
| Agent orchestration | **ADOPT** | Agent Framework Graph Workflows | High |
| Tool integration | **ADOPT** | Agent Framework Tools + MCP | High |
| Session state | **ADOPT** | Agent Framework Threads (GitThreadStore) | High |
| Context injection | **ADOPT** | Agent Framework Context Providers | High |
| Validation/constraints | **ADOPT** | Agent Framework Middleware | Medium |
| Observability | **ADOPT** | Agent Framework OpenTelemetry | Medium |
| Git-native state | **KEEP** | Context.md | Very High |
| Memory/learning | **KEEP** | Context.md (expose via Context Provider) | Very High |
| Prompt engineering | **KEEP** | Context.md (expose via Context Provider) | Very High |
| Context generation | **KEEP** | Context.md (expose via Context Provider) | Very High |
| Skills library | **KEEP** | Context.md (optional Mem0 for similarity search) | Very High |
| Agent definitions | **KEEP** | Context.md (generate framework YAML) | High |
| GitHub integration | **KEEP** | Context.md | Very High |
| Dashboard | **KEEP** | Context.md (evaluate DevUI as complement) | Medium |
| CI/CD workflows | **KEEP** | GitHub Actions | High |
| Git hooks | **KEEP** | Context.md (complement with middleware) | High |

### Overall Strategy

**Adopt Microsoft Agent Framework** for:
- Graph-based multi-agent orchestration (replaces static label routing)
- Tool integration with function calling and MCP
- Session management via Threads with custom GitThreadStore
- Context injection via custom Context Provider (wrapping 4-layer system)
- Agent-level validation via Middleware pipeline
- Production observability via OpenTelemetry

**Keep Context.md** for:
- Git-native state (worktrees, branches, notes)
- Memory system (lessons, effectiveness tracking, learning loop)
- Prompt engineering pipeline (>95% success rate enabler)
- 4-layer context architecture (exposed through Context Provider)
- Skills library (27 domain knowledge documents)
- Agent definitions (richer than any framework; source of truth)
- GitHub integration (Projects V2, Actions, hooks)
- Dashboard (existing CLI + web)

**Skip standalone AutoGen and Semantic Kernel**:
- Both are being converged into the Agent Framework
- No reason to adopt legacy when the successor is available
- Reduces dependency management complexity

---

## 9. Implementation Priority

| Priority | Task | Dependencies |
|----------|------|-------------|
| 1 | Add `agent-framework` as optional dependency in pyproject.toml | None |
| 2 | Create `context_md/framework/` package structure | #1 |
| 3 | Implement ToolRegistry wrapping existing subprocess calls | #2 |
| 4 | Implement ContextMdProvider (4-layer context as Context Provider) | #2 |
| 5 | Implement ContextMdAgentFactory (agent creation with enhanced prompts) | #3, #4 |
| 6 | Implement GitThreadStore for session persistence | #2 |
| 7 | Implement graph workflow orchestrator | #5, #6 |
| 8 | Implement middleware (validation, file boundaries, security) | #5 |
| 9 | Add `context-md run <issue>` CLI command | #7 |
| 10 | Add OpenTelemetry integration | #7 |
| 11 | Integration testing with real LLM | #9 |
| 12 | Gradual async migration of existing commands | #9 |

### Quick Win (implement first):

```bash
# New CLI command
context-md run 42

# This would:
# 1. Generate 4-layer context using existing system
# 2. Create Agent Framework agents with enhanced prompts
# 3. Register tools from ToolRegistry
# 4. Inject context via ContextMdProvider
# 5. Run graph workflow with streaming
# 6. Persist session to GitThreadStore
# 7. Record outcomes to memory system
# 8. Emit OpenTelemetry traces
```

---

## 10. Conclusion

### What Changed from Previous Analysis

The discovery of Microsoft's **unified Agent Framework** significantly changes the adoption strategy:

| Aspect | Previous Recommendation | Updated Recommendation |
|--------|------------------------|----------------------|
| **Orchestration** | AutoGen Swarm | Agent Framework Graph Workflows |
| **Tools** | AutoGen Tools or SK Plugins | Agent Framework Tools |
| **State** | AutoGen save_state/load_state | Agent Framework Threads |
| **Memory** | Keep Context.md (no framework) | Keep Context.md + expose via Context Provider |
| **Validation** | Keep Context.md hooks | Keep hooks + add Agent Framework Middleware |
| **Observability** | None planned | Agent Framework OpenTelemetry |
| **Number of dependencies** | 2 (AutoGen + SK) | 1 (Agent Framework) |

### Why This Matters

The Agent Framework provides a **single, unified integration point** instead of requiring adoption of two separate frameworks. This means:

1. **One dependency** instead of two
2. **One API to learn** instead of two
3. **One upgrade path** instead of managing AutoGen + SK compatibility
4. **Future-proof** -- this is Microsoft's strategic direction
5. **Better architecture** -- graph workflows, context providers, and middleware are purpose-built for the patterns Context.md needs

### What Context.md Uniquely Provides

Even with the Agent Framework, Context.md's core value proposition remains unique:

- **Git-native state management** -- No framework treats Git as a first-class state backend
- **Structured learning with effectiveness tracking** -- The most advanced agent learning system available
- **Prompt engineering pipeline** -- Automatic enhancement achieving >95% success rates
- **4-layer context architecture** -- Methodical context assembly beyond what any framework provides
- **27 domain skill documents** -- Deep technical knowledge library
- **Rich agent definitions** -- Constraints, file boundaries, maturity levels, validation scripts

**The result is a system that combines the best of both worlds**: Context.md's deep domain expertise in AI agent context management with the Agent Framework's production-grade orchestration, tooling, and observability infrastructure.

---

## Appendix A: Legacy Framework Analysis (AutoGen + Semantic Kernel)

The detailed feature mapping for AutoGen and Semantic Kernel is preserved below for reference. These frameworks remain usable but are being converged into the Agent Framework.

### A.1 Semantic Kernel (SK)

**Key Components**:
- **Kernel** -- Central orchestrator managing plugins and AI services
- **Plugins** -- Encapsulate APIs as callable functions (native, OpenAPI, MCP)
- **Agents** -- ChatCompletionAgent, OpenAIAssistantAgent
- **Orchestration** -- Sequential, Concurrent, Handoff, GroupChat patterns
- **Process Framework** -- Event-driven workflow steps (experimental)

### A.2 AutoGen

**Architecture Layers**:
- **Studio** -- No-code web UI (built on AgentChat)
- **AgentChat** -- High-level API for multi-agent apps
- **Core** -- Event-driven, distributed, Actor-model framework
- **Extensions** -- MCP servers, Docker execution, distributed agents

**Key Patterns**:
- **Swarm** -- Decentralized handoff via HandoffMessage
- **SelectorGroupChat** -- LLM-based speaker selection
- **RoundRobinGroupChat** -- Sequential agent turns
- **save_state/load_state** -- JSON-serializable session persistence

### A.3 Legacy vs Agent Framework Comparison

| Capability | AutoGen | SK | Agent Framework |
|-----------|---------|----|----|
| Multi-agent orchestration | Swarm, GroupChat | Sequential, Handoff | **Graph Workflows** |
| Tool calling | Python functions | Plugins (@kernel_function) | **Python functions + MCP** |
| Memory | None (manual) | Vector stores (experimental) | **Context Providers** |
| Session persistence | save/load_state | None | **Threads (suspend/resume)** |
| Middleware | None | Plugin filters | **Full pipeline** |
| Observability | Console | Application Insights | **OpenTelemetry** |
| Declarative agents | No | No | **YAML-based** |
| Status | Stable, converging | Stable, converging | **Preview, strategic** |
