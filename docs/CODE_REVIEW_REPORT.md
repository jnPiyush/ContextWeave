# Comprehensive Code Review Report

**Date:** January 30, 2026  
**Reviewer:** AI Code Review Agent  
**Project:** ContextWeave CLI  
**Coverage:** 54% (Target: 80%)

---

## Executive Summary

ContextWeave is a well-architected CLI tool for managing AI agent runtime context using Git-native state management. The codebase demonstrates solid design patterns but has several areas requiring attention for production readiness.

### Quality Scorecard

| Category | Score | Status |
|----------|-------|--------|
| Architecture & Design | 8/10 | ✅ Good |
| Code Quality | 7/10 | 🟡 Needs Work |
| Security | 7/10 | 🟡 Needs Work |
| Error Handling | 6/10 | 🟡 Needs Improvement |
| Test Coverage | 5/10 | ❌ Below Target |
| Documentation | 8/10 | ✅ Good |
| Performance | 7/10 | ✅ Acceptable |

---

## 1. Critical Issues (Must Fix)

### 1.1 Security Vulnerabilities

#### 1.1.1 Token Exposure Risk in Debug Mode
**File:** [context_weave/commands/auth.py](../context_weave/commands/auth.py#L343-L355)
**Severity:** HIGH

```python
@auth_cmd.command("token")
@click.option("--show", is_flag=True, help="Show the actual token (use with caution)")
def token_cmd(ctx: click.Context, show: bool) -> None:
    """Display token information (for debugging)."""
    if show:
        token = state.github_token
        if len(token) > 16:
            masked = token[:8] + "..." + token[-8:]  # Still exposes 16 chars!
```

**Issue:** The token command exposes 16 characters of the token when `--show` is used. With `gho_` prefix tokens, this reveals most of the token.

**Recommendation:**
```python
if show:
    token = state.github_token
    masked = token[:4] + "*" * (len(token) - 8) + token[-4:]  # Only 8 chars visible
    click.secho("⚠️ SENSITIVE: Do not share this output", fg="yellow")
```

#### 1.1.2 Missing Input Sanitization on Issue Titles
**File:** [context_weave/commands/issue.py](../context_weave/commands/issue.py#L52-L93)
**Severity:** MEDIUM

Issue titles are stored directly without sanitization, potentially allowing:
- XSS injection if rendered in web UI
- Command injection via branch names derived from titles

**Recommendation:** Add input validation:
```python
def sanitize_title(title: str) -> str:
    """Sanitize issue title for safe storage and branch naming."""
    import re
    # Remove control characters
    title = re.sub(r'[\x00-\x1f\x7f]', '', title)
    # Limit length
    return title[:200].strip()
```

#### 1.1.3 OAuth Client ID Hardcoded
**File:** [context_weave/commands/auth.py](../context_weave/commands/auth.py#L31-L35)
**Severity:** MEDIUM

```python
GITHUB_CLIENT_ID = os.getenv(
    "CONTEXT_WEAVE_GITHUB_CLIENT_ID",
    "Ov23liUwXgKjNxHiXmpt"  # Default public client for OSS
)
```

**Issue:** While documented as intentional for OSS, this could be abused. Consider:
- Rate limiting per installation
- User-agent validation
- Documenting risks in README

---

### 1.2 Error Handling Deficiencies

#### 1.2.1 Broad Exception Catching
**Files:** Multiple locations (162 total lint errors reported)

```python
# Bad pattern found in state.py:204
except Exception as e:
    logger.warning(f"Failed to retrieve token from keyring: {e}")
```

**Recommendation:** Catch specific exceptions:
```python
from keyring.errors import KeyringError, PasswordNotFoundError

try:
    token = keyring.get_password("context-weave", "github_token")
except PasswordNotFoundError:
    return None
except KeyringError as e:
    logger.warning("Keyring access failed: %s", e)
    return os.getenv("GITHUB_TOKEN")
```

#### 1.2.2 subprocess.run Without check=True
**Files:** Multiple commands (subagent.py, validate.py, test files)

```python
# Unsafe pattern - exit code ignored
subprocess.run(["git", "worktree", "prune"], cwd=repo_root, capture_output=True)
```

**Recommendation:** Always specify `check` parameter explicitly:
```python
subprocess.run(
    ["git", "worktree", "prune"],
    cwd=repo_root,
    capture_output=True,
    check=False  # Explicit: we want to ignore failures here
)
```

#### 1.2.3 Missing Timeout on Network Operations
**File:** [context_weave/commands/sync.py](../context_weave/commands/sync.py#L440-L460)
**Severity:** MEDIUM

Some `urlopen` calls have timeout, but the timeout value (30s) may be too long for interactive CLI.

**Recommendation:** Make timeout configurable via config:
```python
NETWORK_TIMEOUT = config.get("network.timeout", 15)  # Default 15s
```

---

### 1.3 Missing Test Coverage

#### Current Coverage: 54% (Target: 80%)

| Module | Current | Target | Gap |
|--------|---------|--------|-----|
| auth.py | 58% | 80% | 22% |
| sync.py | 42% | 80% | 38% |
| validate.py | 73% | 80% | 7% |
| issue.py | 19% | 80% | **61%** |
| config.py | 32% | 80% | **48%** |
| subagent.py | 51% | 80% | 29% |
| context.py | 50% | 80% | 30% |
| init.py | 65% | 80% | 15% |

**Critical Gaps:**
1. **issue.py (19%)** - Most user-facing commands untested
2. **config.py (32%)** - Configuration edge cases untested
3. **sync.py (42%)** - GitHub API interactions need more mocking

---

## 2. Design Issues

### 2.1 Missing Retry Logic for Network Operations

**File:** [context_weave/commands/auth.py](../context_weave/commands/auth.py), [sync.py](../context_weave/commands/sync.py)

Network operations lack proper retry logic with exponential backoff.

**Recommendation:** Add retry decorator:
```python
from functools import wraps
import time

def retry_with_backoff(max_retries=3, base_delay=1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (HTTPError, URLError) as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
        return wrapper
    return decorator
```

### 2.2 No Graceful Degradation

When GitHub sync fails, the CLI doesn't offer offline alternatives.

**Recommendation:** Add offline mode detection:
```python
def check_connectivity() -> bool:
    """Check if GitHub API is reachable."""
    try:
        urlopen("https://api.github.com", timeout=5)
        return True
    except URLError:
        return False

# In sync commands:
if not check_connectivity():
    click.secho("⚠️ GitHub unavailable. Working in offline mode.", fg="yellow")
    _show_local_issues(state, verbose)
    return
```

### 2.3 Missing Rate Limit Handling

**File:** [context_weave/commands/sync.py](../context_weave/commands/sync.py)

GitHub API rate limits (60/hour unauthenticated, 5000/hour authenticated) are not tracked.

**Recommendation:** Add rate limit awareness:
```python
def _github_api_get(token: str, endpoint: str) -> Any:
    # ... existing code ...
    with urlopen(request, timeout=30) as response:
        # Check rate limit headers
        remaining = response.headers.get("X-RateLimit-Remaining", "?")
        reset_time = response.headers.get("X-RateLimit-Reset", "?")
        if int(remaining) < 10:
            logger.warning(
                "GitHub API rate limit low: %s remaining, resets at %s",
                remaining, reset_time
            )
        return json.loads(response.read().decode())
```

### 2.4 Configuration Validation Missing

**File:** [context_weave/config.py](../context_weave/config.py)

No schema validation for configuration files. Malformed config silently uses defaults.

**Recommendation:** Add JSON Schema validation:
```python
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "mode": {"enum": ["local", "github", "hybrid"]},
        "worktree_base": {"type": "string"},
        # ... more properties
    }
}

def _validate_config(data: Dict) -> List[str]:
    """Validate config against schema, return list of errors."""
    errors = []
    # Validate mode
    if data.get("mode") not in ("local", "github", "hybrid"):
        errors.append(f"Invalid mode: {data.get('mode')}")
    return errors
```

---

## 3. Code Quality Issues

### 3.1 Logging Format Strings

**Multiple Files:** Using f-strings instead of lazy formatting.

```python
# Bad
logger.warning(f"Failed to retrieve token: {e}")

# Good (lazy evaluation)
logger.warning("Failed to retrieve token: %s", e)
```

**Files Affected:** state.py, subagent.py, validate.py

### 3.2 Unused Parameters

Several functions have unused parameters that should be removed or prefixed with `_`:

```python
# cli.py:111
def validate_issue_number(ctx, param, value):  # ctx and param unused

# validate.py:238
def _run_dod_check(repo_root, issue, role, check_id, state):  # role unused

# status.py:63, 130
def _collect_status(repo_root, state, config):  # repo_root unused
def _display_status(data, config):  # config unused
```

### 3.3 Missing Type Hints

Several functions lack complete type annotations:

```python
# auth.py - Missing return type hints on some helpers
def _check_gh_cli_auth():  # Should be -> Optional[str]
```

### 3.4 Code Duplication

**Issue:** GitHub API helper functions are duplicated between auth.py and sync.py.

**Recommendation:** Create shared module `context_weave/github_api.py`:
```python
# context_weave/github_api.py
"""Shared GitHub API utilities."""

def api_get(token: str, endpoint: str, timeout: int = 30) -> Any: ...
def api_post(token: str, endpoint: str, data: Dict) -> Any: ...
def get_current_user(token: str) -> Optional[Dict]: ...
```

---

## 4. Missing Features

### 4.1 No Logging Configuration

Users cannot configure log levels or output locations via CLI.

**Recommendation:** Add `--log-level` option:
```python
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]))
```

### 4.2 No Progress Indicators for Long Operations

Sync operations with many issues show no progress.

**Recommendation:** Add progress bar:
```python
from click import progressbar

with click.progressbar(issues, label="Syncing issues") as bar:
    for issue in bar:
        # process issue
```

### 4.3 Missing Configuration Commands

No way to view full configuration or reset to defaults.

**Recommendation:** Add commands:
```bash
context-weave config show          # Show all config
context-weave config reset         # Reset to defaults
context-weave config validate      # Validate config file
```

### 4.4 No Dry-Run Support on Destructive Operations

`subagent complete --force` can delete uncommitted work without preview.

**Recommendation:** Always show what will be deleted before `--force`.

---

## 5. Robustness Improvements

### 5.1 State File Corruption Recovery

If `state.json` is corrupted, the CLI fails completely.

**Recommendation:** Add backup and recovery:
```python
def _load(self) -> None:
    if self.state_file.exists():
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # Backup corrupted file
            backup = self.state_file.with_suffix('.json.bak')
            shutil.copy(self.state_file, backup)
            logger.warning("Corrupted state file backed up to %s", backup)
            self._data = self._default_state()
```

### 5.2 Git Repository Detection

`find_repo_root()` doesn't handle bare repositories or worktrees.

**Recommendation:** Use `git rev-parse`:
```python
def find_repo_root() -> Optional[Path]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        return None
```

### 5.3 Concurrent Access

Multiple CLI processes can corrupt state.json.

**Recommendation:** Add file locking:
```python
import fcntl  # Unix
# or
import msvcrt  # Windows

def save(self) -> None:
    with open(self.state_file, "w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(self._data, f, indent=2)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

---

## 6. Test Quality Issues

### 6.1 Tests Don't Verify Side Effects

Many tests check return values but not side effects (files created, Git state changed).

**Example Fix:**
```python
def test_issue_create_writes_to_state(self, tmp_path, runner):
    # ... create issue ...
    
    # Verify state was actually written
    state_file = tmp_path / ".context-weave" / "state.json"
    assert state_file.exists()
    
    with open(state_file) as f:
        data = json.load(f)
    assert "1" in data["local_issues"]
```

### 6.2 Missing Integration Tests

No tests verify end-to-end workflows:
- Create issue → Spawn SubAgent → Generate context → Complete

**Recommendation:** Add integration test file:
```python
# tests/test_integration.py
class TestFullWorkflow:
    def test_issue_to_completion_workflow(self, temp_git_repo, runner):
        # 1. Init
        # 2. Create issue
        # 3. Spawn SubAgent
        # 4. Generate context
        # 5. Complete SubAgent
        # 6. Verify final state
```

### 6.3 Test Fixtures Need Cleanup

`temp_git_repo` fixture uses `shutil.rmtree(ignore_errors=True)` which can leave orphan files.

---

## 7. Documentation Gaps

### 7.1 Missing API Documentation

Public functions in modules lack docstrings or have incomplete ones:
- `State.get_issue_branches()` - No return type documented
- `Config.get_skills_for_labels()` - No param descriptions

### 7.2 Missing Error Messages Guide

Users need documentation on what error messages mean and how to resolve them.

### 7.3 Missing Architecture Decision Records

No ADRs for key design decisions:
- Why Git notes for metadata?
- Why worktrees for isolation?
- Why keyring for token storage?

---

## 8. Action Items (Priority Order)

### P0 - Critical (Fix Immediately)
1. [ ] Fix token exposure in `--show` flag
2. [ ] Add input sanitization for issue titles
3. [ ] Fix broad exception catching (use specific exceptions)

### P1 - High (Fix This Sprint)
4. [ ] Add explicit `check` parameter to all subprocess.run calls
5. [ ] Fix lazy logging format strings
6. [ ] Remove/prefix unused function parameters
7. [ ] Add tests for issue.py (61% gap)
8. [ ] Add tests for config.py (48% gap)

### P2 - Medium (Fix Next Sprint)
9. [ ] Extract shared GitHub API code to separate module
10. [ ] Add retry logic for network operations
11. [ ] Add rate limit awareness
12. [ ] Add progress indicators for long operations
13. [ ] Add state file corruption recovery

### P3 - Low (Backlog)
14. [ ] Add file locking for concurrent access
15. [ ] Add offline mode detection
16. [ ] Add configuration validation
17. [ ] Write integration tests
18. [ ] Document architecture decisions

---

## 9. Positive Observations

### Well-Designed Aspects

1. **Git-Native State** - Using Git branches/notes for state is elegant and auditable
2. **Worktree Isolation** - True file system isolation prevents cross-contamination
3. **Security-First Token Storage** - Using system keyring over state files
4. **Click Framework** - Consistent CLI structure with good help text
5. **Skill Routing** - Configurable skill loading based on labels is flexible
6. **Hook Integration** - Git hooks for automation are well-designed

### Code Quality Highlights

- Consistent code style
- Good module separation (commands, state, config)
- Dataclasses used appropriately
- Type hints on most public functions
- Comprehensive CLI help text

---

## Appendix: Files Reviewed

| File | Lines | Complexity | Issues |
|------|-------|------------|--------|
| cli.py | 161 | Low | 7 |
| state.py | 356 | Medium | 5 |
| config.py | 167 | Low | 0 |
| auth.py | 525 | High | 3 |
| sync.py | 480 | High | 0 |
| validate.py | 378 | Medium | 7 |
| issue.py | 313 | Low | 2 |
| subagent.py | 426 | High | 6 |
| context.py | 412 | Medium | 1 |
| init.py | 355 | Medium | 3 |

**Total Production Code:** ~3,573 lines  
**Total Test Code:** ~1,300 lines  
**Test-to-Code Ratio:** 0.36 (Target: 0.8+)

---

*This review was conducted following the guidelines in [Skills.md](../Skills.md) and [.github/skills/development/code-review-and-audit/SKILL.md](../.github/skills/development/code-review-and-audit/SKILL.md).*
