# GitHub Project Setup Guide

> **Status Tracking**: This project uses GitHub Projects V2 **Status** field exclusively. No orchestration labels needed.

---

## 📋 Initial Setup

### 1. Create GitHub Project V2

```bash
# Via GitHub CLI
gh project create --owner <OWNER> --title "AgentX Development"

# Or via web: https://github.com/users/<YOUR_USERNAME>/projects
```

### 2. Add Status Field

In your project settings, create a **Status** field with these standard values:

| Status Value | Description |
|--------------|-------------|
| **📝 Backlog** | Issue created, waiting to be claimed |
| **🚀 In Progress** | Active work by Engineer |
| **👀 In Review** | Code review phase |
| **🏗️ Ready** | Design/spec complete, awaiting next phase |
| **✅ Done** | Completed and closed |

**Configuration:**
- Field Type: **Single Select**
- Field Name: **Status** (exact name recommended)
- Default: **📝 Backlog**

### 3. Link Repository

1. Go to Project Settings → Manage Access
2. Add repository: `<OWNER>/<REPO>`
3. Issues automatically sync to project board

---

## 🔄 How Status Tracking Works

### Status Field (Primary and Only)

> ⚠️ **Status Tracking**: Use GitHub Projects V2 **Status** field, NOT labels.

**Status transitions:**
| Phase | Status Transition | Meaning |
|-------|-------------------|---------|
| PM completes PRD | → `Ready` | Ready for design/architecture |
| UX completes designs | → `Ready` | Ready for architecture |
| Architect completes spec | → `Ready` | Ready for implementation |
| Engineer starts work | → `In Progress` | Active development |
| Engineer completes code | → `In Review` | Ready for code review |
| Reviewer approves | → `Done` + Close | Work complete |

**Labels are for type only:**
- `type:epic`, `type:feature`, `type:story`, `type:bug`, `type:spike`, `type:docs`
- `needs:ux` - Indicates UI/UX work required
- `needs:changes` - Reviewer requested changes

---

## 🤖 Agent Workflow

### For Agents Using MCP Server

**Check issue status:**
```json
{ "tool": "issue_read", "args": { "issue_number": 60 } }
// Check Status field in Projects board (not labels)
```

**Agent workflow:**
1. Check issue Status in Projects board
2. Comment when starting: "🔧 Engineer starting implementation..."
3. Complete work
4. Update Status in Projects board (manual or via GraphQL)
5. Comment when done: "✅ Implementation complete, ready for review"

### For Users in Project Board

**Drag & drop between columns:**
- Move issue from "In Progress" → "In Review"
- Status updates immediately
- Next agent can pick up work

---

## 🎯 Querying by Status

### GitHub CLI

```bash
# Find issues by type
gh issue list --label "type:story"

# Find issues needing UX work
gh issue list --label "needs:ux"

# Find all Epic child issues
gh issue list --search "parent:#<EPIC_ID>"
```

### MCP Server

```json
// List all open stories
{ "tool": "list_issues", "args": { 
  "owner": "<OWNER>",
  "repo": "AgentX",
  "labels": ["type:story"],
  "state": "open"
} }
```

### GitHub API

```bash
curl -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/<OWNER>/<REPO>/issues?labels=type:story"
```

---

## 🔧 Customization

### Modify Status Values

Edit your GitHub Project Status field to add custom values like:
- **🚧 Blocked** - Work paused due to dependencies
- **🔄 Rework** - Changes requested by reviewer

Status is managed in Projects UI, not via code.

---

## 📊 Project Views

### Recommended Board View

**Columns:**
1. 📝 Backlog (`Status = Backlog`)
2. 🏗️ Ready (`Status = Ready`) - Design/spec complete
3. 🚀 In Progress (`Status = In Progress`)
4. 👀 In Review (`Status = In Review`)
5. ✅ Done (`Status = Done`)

**Filters:**
- Group by: `Status`
- Sort by: `Priority` (descending), then `Updated` (newest)

### Table View

**Columns to show:**
- Issue
- Status
- Labels (for type:* tracking)
- Priority
- Assignees
- Updated

---

## 🚨 Troubleshooting

### Status not visible in project

**Check:**
1. Issue is added to project (drag from repo to project)
2. Status field exists in project settings
3. View columns are configured to show Status field

**Manual add:**
```bash
gh project item-add <PROJECT_ID> --owner <OWNER> --url <ISSUE_URL>
```

### Agent coordination not working

**Check Status field in Projects board:**
1. Go to Projects board
2. Verify issue Status is correct
3. Engineer should start when Status = `Ready`

### Status field missing

Create Status field in Project Settings:
1. Go to project → Settings → Fields
2. Add new field → Single Select → Name: "Status"
3. Add options: Backlog, Ready, In Progress, In Review, Done

---

## 📚 References

- [GitHub Projects v2 Docs](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [GitHub GraphQL API](https://docs.github.com/en/graphql)
- [AGENTS.md](../AGENTS.md) - Workflow documentation

---

**Last Updated**: January 27, 2026
