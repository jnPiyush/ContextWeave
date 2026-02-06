# New Features Implementation Guide

This document describes the newly implemented features for Context.md: Git Hooks Infrastructure and GitHub Projects V2 Integration.

---

## 1. Git Hooks Infrastructure

### Overview

Git hooks provide automated validation and certificate generation at key points in the development workflow.

### Available Hooks

#### 1.1 Post-Merge Hook

**Purpose**: Generate completion certificates and track metrics after successful merges.

**Location**: `.github/hooks/post-merge`

**Triggers**: Automatically after `git merge` completes

**Actions**:
- Extracts issue number from merge commit message
- Generates completion certificate in `.agent-context/certificates/`
- Updates metrics in `.agent-context/metrics.json`
- Tracks: commit hash, author, files changed, merge date

**Certificate Format**:
```markdown
# Completion Certificate

**Issue**: #42
**Title**: Add user authentication
**Status**: ✅ Completed
**Merged**: 2026-02-06T09:30:00Z

## Merge Details
- Commit: `abc123...`
- Branch: `feature/auth`
- Author: John Doe <john@example.com>
- Files Changed: 15

## Verification
- ✅ Code review completed
- ✅ All tests passing
- ✅ Branch merged to main
```

#### 1.2 Pre-Commit Hook

**Purpose**: Run security checks and linting before allowing commits.

**Location**: `.github/hooks/pre-commit`

**Triggers**: Before every `git commit`

**Checks**:
1. **Secret Detection** - Scans for:
   - Passwords, API keys, tokens
   - GitHub PATs (`ghp_...`)
   - Private keys
   - Stripe keys (`sk_live_...`)

2. **File Size Check** - Warns about files >1MB

3. **Python Linting** - Runs `ruff` if available

4. **Commit Message Format** - Validates format: `type: description (#issue)`

**Example Output**:
```
========================================
  Context.md Pre-Commit Checks
========================================

[CHECK 1/4] Scanning for secrets...
[OK] No secrets detected

[CHECK 2/4] Checking file sizes...
[OK] All files within size limits

[CHECK 3/4] Linting Python files...
[OK] Python linting passed

[CHECK 4/4] Checking commit message format...
[OK] Commit message format valid

========================================
[OK] All pre-commit checks passed
========================================
```

#### 1.3 Pre-Push Hook

**Purpose**: Validate Definition of Done before pushing to remote.

**Location**: `.github/hooks/pre-push`

**Triggers**: Before `git push`

**Validations**:
- Extracts issue numbers from commits being pushed
- Runs `context-md validate <issue> --dod` for each issue
- Ensures:
  - Tests are included
  - Code changes present
  - Documentation updated

### Installation

#### Automatic Installation (Recommended)

```bash
cd your-repo
./.github/hooks/install-hooks.sh
```

**Output**:
```
========================================
  Context.md Git Hooks Installer
========================================

[OK] Installed post-merge
[OK] Installed pre-commit
[OK] Installed pre-push

✓ Installation complete

Installed hooks:
  • post-merge  - Generate completion certificates
  • pre-commit  - Security checks and linting
  • pre-push    - Definition of Done validation
```

#### Manual Installation

```bash
cd your-repo/.git/hooks
ln -s ../../.github/hooks/post-merge post-merge
ln -s ../../.github/hooks/pre-commit pre-commit
ln -s ../../.github/hooks/pre-push pre-push
chmod +x post-merge pre-commit pre-push
```

#### Uninstallation

```bash
./.github/hooks/install-hooks.sh --uninstall
```

### Bypassing Hooks

**Not recommended**, but useful in emergencies:

```bash
# Bypass pre-commit checks
git commit --no-verify

# Bypass pre-push validation
git push --no-verify
```

### Configuration

#### Disable Specific Checks

Edit `.github/hooks/pre-commit` to comment out checks:

```bash
# Skip secret detection
# [CHECK 1/4] Scanning for secrets...
```

#### Adjust File Size Limit

In `.github/hooks/pre-commit`, change:

```bash
MAX_SIZE_KB=1024  # 1MB limit (change to desired KB)
```

---

## 2. GitHub Projects V2 Integration

### Overview

Full GraphQL integration for updating issue status in GitHub Projects V2. This enables automated agent coordination through status transitions.

### Features Implemented

1. **GraphQL API Client** - Direct API access to Projects V2
2. **Field ID Resolution** - Automatic discovery of project field IDs
3. **Status Updates** - Update issue status programmatically
4. **CLI Command** - Easy status management from command line

### Usage

#### 2.1 Setup GitHub Projects V2

First, configure your project:

```bash
context-md sync setup --owner <owner> --repo <repo> --project <number>
```

**Example**:
```bash
context-md sync setup --owner jnPiyush --repo ContextMD --project 1
```

This will:
- Configure GitHub sync
- Store project number
- Verify GitHub CLI authentication

#### 2.2 Update Issue Status

```bash
context-md sync status-update <issue_number> "<status>"
```

**Available Status Values**:
- `Backlog` - Issue created, not started
- `In Progress` - Active work by current agent
- `In Review` - Code review phase
- `Ready` - Design/spec done, awaiting next phase
- `Done` - Completed and closed

**Examples**:
```bash
# Mark issue as ready for next phase
context-md sync status-update 42 "Ready"

# Start work on issue
context-md sync status-update 42 "In Progress"

# Send to code review
context-md sync status-update 42 "In Review"

# Mark as complete
context-md sync status-update 42 "Done"
```

**Output**:
```
Updating issue #42 status to 'Ready'...

[OK] Status updated successfully!
  Issue: #42
  Status: Ready
  Project: #1
```

### Agent Coordination Workflow

The Projects V2 integration enables the hub-and-spoke agent pattern documented in AGENTS.md:

```
1. PM Agent completes PRD
   → Updates status to "Ready"
   → UX/Architect picks up

2. Architect completes spec
   → Updates status to "Ready"
   → Engineer picks up

3. Engineer completes code
   → Updates status to "In Review"
   → Reviewer picks up

4. Reviewer approves
   → Updates status to "Done"
   → Closes issue
```

### Programmatic API

You can also use the Python API directly:

```python
from context_md.commands.sync import update_project_status

# Update status
update_project_status(
    token="ghp_...",
    owner="jnPiyush",
    repo="ContextMD",
    project_number=1,
    issue_number=42,
    status="Ready"
)
```

### GraphQL Functions

#### `get_project_field_ids()`

Retrieves field IDs for a project:

```python
from context_md.commands.sync import get_project_field_ids

fields = get_project_field_ids(
    token="ghp_...",
    owner="jnPiyush",
    repo="ContextMD",
    project_number=1
)

# fields = {
#     "Status": {
#         "id": "PVTF_lA...",
#         "options": {
#             "Backlog": "f75ad8...",
#             "In Progress": "47fc9e...",
#             "In Review": "98ecda...",
#             "Ready": "a8e6a1...",
#             "Done": "5e0ff3..."
#         }
#     }
# }
```

#### `_github_graphql()`

Execute raw GraphQL queries:

```python
from context_md.commands.sync import _github_graphql

query = """
query($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    projectsV2(first: 5) {
      nodes {
        number
        title
      }
    }
  }
}
"""

data = _github_graphql(
    token="ghp_...",
    query=query,
    variables={"owner": "jnPiyush", "repo": "ContextMD"}
)
```

### Error Handling

The integration handles common errors gracefully:

```bash
# Project not found
Error: Project #999 not found in owner/repo

# Issue not in project
Error: Issue #42 not found in project #1

# Invalid status
Error: Invalid status 'Pending'. Available: Backlog, In Progress, In Review, Ready, Done

# Authentication error
Error: Not authenticated with GitHub. Run: context-md auth login
```

### Authentication

Projects V2 integration requires authentication:

**Option 1: OAuth (Recommended)**
```bash
context-md auth login
```

**Option 2: GitHub CLI**
```bash
gh auth login
```

The integration will use OAuth token if available, falling back to gh CLI.

### Permissions Required

Your GitHub token needs:

- `repo` - Full repository access
- `project` - Project read/write access
- `read:org` - For organization repos (if applicable)

### Troubleshooting

#### "Project not found"

**Cause**: Project number incorrect or project not linked to repo.

**Solution**:
1. Go to your GitHub Projects
2. Find the project number (in URL: `projects/1`)
3. Ensure project is linked to the repository
4. Re-run setup: `context-md sync setup --project <number>`

#### "Status field not found"

**Cause**: Project doesn't have a "Status" field.

**Solution**:
1. Open your GitHub Project
2. Add a "Status" field (single select)
3. Create options: Backlog, In Progress, In Review, Ready, Done

#### "Issue not in project"

**Cause**: Issue hasn't been added to the project board.

**Solution**:
1. Open the project board
2. Click "+ Add item"
3. Search for and add the issue
4. Try status update again

---

## 3. Integration Testing

### Test Git Hooks

#### Test Post-Merge Hook

```bash
# Create a test branch with issue reference
git checkout -b test/issue-99
echo "test" > test.txt
git add test.txt
git commit -m "feat: test feature (#99)"

# Merge to trigger hook
git checkout master
git merge test/issue-99

# Check certificate generated
ls .agent-context/certificates/
# Should see: CERT-99-<hash>.md

# Check metrics updated
cat .agent-context/metrics.json
```

#### Test Pre-Commit Hook

```bash
# Test secret detection
echo 'password = "secret123"' > test.py
git add test.py
git commit -m "test"
# Should fail with secret detection error

# Clean up
git reset HEAD test.py
rm test.py
```

#### Test Pre-Push Hook

```bash
# Create commit without tests
git checkout -b test/no-tests
echo "code" > app.py
git add app.py
git commit -m "feat: new feature (#100)"

# Try to push (should warn about missing tests)
git push origin test/no-tests
```

### Test Projects V2 Integration

```bash
# Setup project
context-md sync setup --owner <owner> --repo <repo> --project 1

# Create test issue on GitHub
gh issue create --title "Test Projects V2" --label "type:story"
# Note the issue number (e.g., #50)

# Add issue to project (via GitHub UI or gh CLI)

# Test status update
context-md sync status-update 50 "In Progress"
# Check GitHub Projects UI - status should update

# Test all status transitions
context-md sync status-update 50 "Ready"
context-md sync status-update 50 "In Review"
context-md sync status-update 50 "Done"
```

---

## 4. CI/CD Integration

### GitHub Actions Integration

Add status updates to your workflows:

**.github/workflows/agent-workflow.yml**:
```yaml
name: Agent Workflow

on:
  workflow_dispatch:
    inputs:
      issue_number:
        required: true
        type: string

jobs:
  execute:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Update status to In Progress
        run: |
          context-md sync status-update ${{ inputs.issue_number }} "In Progress"

      - name: Run agent work
        run: |
          # ... agent execution ...

      - name: Update status to Ready
        if: success()
        run: |
          context-md sync status-update ${{ inputs.issue_number }} "Ready"

      - name: Update status to needs help
        if: failure()
        run: |
          gh issue edit ${{ inputs.issue_number }} --add-label "needs:help"
```

---

## 5. Migration Guide

### Existing Repositories

If you have an existing Context.md setup:

1. **Install Git Hooks**:
   ```bash
   ./.github/hooks/install-hooks.sh
   ```

2. **Configure Projects V2**:
   ```bash
   context-md sync setup --project <number>
   ```

3. **Update Workflows** (if using GitHub Actions):
   - Add `context-md sync status-update` commands
   - Remove manual label-based status tracking

4. **Test Integration**:
   ```bash
   # Test status update
   context-md sync status-update <test-issue> "Ready"
   ```

### From Label-Based Status to Projects V2

If you were using labels for status (not recommended):

**Before**:
```bash
gh issue edit 42 --add-label "status:in-progress"
```

**After**:
```bash
context-md sync status-update 42 "In Progress"
```

**Benefits**:
- Proper Projects V2 integration
- Better visualization on project board
- Automated agent coordination
- Audit trail in project history

---

## 6. FAQ

### Q: Can I use hooks with VS Code Git integration?

**A**: Yes! The hooks work with all Git interfaces (CLI, VS Code, GitKraken, etc.).

### Q: Do hooks work on Windows?

**A**: Yes, but requires Git Bash or WSL. The hooks are Bash scripts and need a Bash interpreter.

### Q: Can I customize hook behavior?

**A**: Yes! Edit the scripts in `.github/hooks/` to modify checks, thresholds, or add new validations.

### Q: What if my project uses different status names?

**A**: The `update_project_status()` function auto-detects available status options. It will show valid values in error messages.

### Q: Can I update multiple issues at once?

**A**: Not via CLI, but you can script it:
```bash
for issue in 42 43 44; do
  context-md sync status-update $issue "Ready"
done
```

### Q: Does this work with organization projects?

**A**: Yes! Make sure your token has `read:org` scope.

---

## 7. Rollback Instructions

If you need to revert these features:

### Remove Git Hooks

```bash
./.github/hooks/install-hooks.sh --uninstall
```

### Revert sync.py Changes

```bash
git log --oneline -- context_md/commands/sync.py
# Find commit before Projects V2 integration
git checkout <commit-hash> -- context_md/commands/sync.py
```

### Continue Using GitHub CLI

Projects V2 status can still be updated via GitHub CLI:

```bash
# Via gh CLI (requires project item ID)
gh project item-edit --id <item-id> --field-id <status-field-id> --single-select-option-id <option-id>
```

---

## 8. Next Steps

1. **Read AGENTS.md** for agent coordination workflows
2. **Setup Projects V2** in your GitHub repository
3. **Install hooks** for automated validation
4. **Test integration** with a sample issue
5. **Update workflows** to use new commands

---

**Questions?** Open an issue at https://github.com/jnPiyush/ContextMD/issues

**Documentation**: See README.md and AGENTS.md for more details.
