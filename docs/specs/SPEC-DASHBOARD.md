# Real-Time Dashboard Design Document

**Issue**: #4 - Real-Time Dashboard - WebSocket Agent Tracking  
**Date**: 2026-02-05  
**Status**: Design Phase

---

## 1. Overview

Implement a web-based real-time dashboard that provides immediate visibility into multi-agent workflows through WebSocket updates. This replaces the current polling-based CLI watch mode with a push-based web interface.

## 2. Current State Analysis

### Existing Infrastructure
- **State Management**: `context_md/state.py` - Tracks worktrees, GitHub sync
- **Status Collection**: `context_md/commands/status.py` - Gathers agent status
- **Watch Mode**: CLI polling every 5 seconds
- **Data Sources**: Git branches, notes, worktrees

### Current Limitations
- ❌ No real-time push updates
- ❌ CLI-only (no web UI)
- ❌ 5-second polling delay
- ❌ No historical visualization

## 3. Architecture Design

### 3.1 System Components

```
┌─────────────────────────────────────────────────────┐
│                  Browser Client                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  Dashboard UI (HTML/CSS/JS)                  │  │
│  │  - Agent Status Cards                        │  │
│  │  - Progress Bars                             │  │
│  │  - Activity Stream                           │  │
│  │  - WebSocket Client                          │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                        ↕ WebSocket
┌─────────────────────────────────────────────────────┐
│       WebSocket Server (Python asyncio)              │
│  ┌──────────────────────────────────────────────┐  │
│  │  - websockets library                        │  │
│  │  - Event emitter                             │  │
│  │  - State broadcaster                         │  │
│  │  - File watcher (.agent-context/state.json) │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│         Existing Context.md Infrastructure           │
│  - state.py (WorktreeInfo, GitHubConfig)           │
│  - status.py (_collect_status)                     │
│  - Git notes (metadata)                            │
│  - Git worktrees (isolation)                       │
└─────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

1. **State Changes** (Git operations, status updates)
2. **File Watch** → Detects `.agent-context/state.json` modifications
3. **WebSocket Server** → Collects status via `_collect_status()`
4. **Broadcast** → Pushes JSON payload to all connected clients
5. **UI Update** → Dashboard re-renders with new data

### 3.3 Message Protocol

#### Server → Client Messages

```json
{
  "type": "status_update",
  "timestamp": "2026-02-05T19:15:00Z",
  "data": {
    "mode": "local",
    "active_subagents": 2,
    "stuck_issues": 0,
    "worktrees": [
      {
        "issue": 3,
        "role": "engineer",
        "branch": "issue-3-export",
        "status": "spawned",
        "hours_inactive": 0.2,
        "is_stuck": false
      }
    ],
    "by_role": {"engineer": 2},
    "by_status": {"spawned": 2}
  }
}
```

#### Client → Server Messages

```json
{
  "type": "ping"
}
```

## 4. Implementation Plan

### Phase 1: Backend WebSocket Server

**File**: `context_md/dashboard.py`

```python
import asyncio
import json
import websockets
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DashboardServer:
    async def start(host="localhost", port=8765):
        # WebSocket handler
        # File watcher for state.json
        # Broadcast to connected clients
```

**Dependencies**:
- `websockets` - WebSocket server
- `watchdog` - File system monitoring

### Phase 2: Frontend Dashboard

**File**: `context_md/static/dashboard.html`

**Features**:
- Agent status cards with color coding
- Real-time activity stream
- Progress indicators
- Stuck issue alerts
- Connection status indicator

**Tech Stack**:
- Vanilla JavaScript (no framework)
- WebSocket API
- CSS Grid/Flexbox
- Chart.js for visualizations (optional)

### Phase 3: CLI Integration

**Command**: `context-md dashboard`

```bash
# Start dashboard server
context-md dashboard --port 8765

# Opens browser automatically to http://localhost:8765
```

## 5. Technical Specifications

### 5.1 WebSocket Server

**Protocol**: ws:// (can upgrade to wss:// for HTTPS)  
**Port**: 8765 (configurable)  
**Concurrency**: async/await with `asyncio`  
**Broadcasting**: Fan-out to all connected clients

### 5.2 Dashboard UI

**Browser Support**: Modern browsers (Chrome, Firefox, Safari, Edge)  
**Responsive**: Desktop and tablet optimized  
**Theme**: Dark mode default (matches CLI aesthetic)  
**Refresh Rate**: Real-time (event-driven)

### 5.3 Security

- ✅ Localhost only by default
- ✅ Optional authentication token
- ✅ CORS headers configured
- ✅ Input validation on server

## 6. User Experience

### 6.1 Starting Dashboard

```bash
$ context-md dashboard
[SUCCESS] Dashboard server started at http://localhost:8765
[SUCCESS] Opening browser...
```

### 6.2 Dashboard Layout

```
┌────────────────────────────────────────────────────┐
│  Context.md Real-Time Dashboard          [●LIVE]   │
├────────────────────────────────────────────────────┤
│  Mode: Local   |   Active: 2   |   Stuck: 0       │
├────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐                │
│  │ Issue #3     │  │ Issue #4     │                │
│  │ Engineer     │  │ PM           │                │
│  │ [●] Active   │  │ [●] Active   │                │
│  │ 0.2h ago     │  │ 1.5h ago     │                │
│  └──────────────┘  └──────────────┘                │
├────────────────────────────────────────────────────┤
│  Activity Stream                                   │
│  ⚫ 19:15:23 - Issue #3 updated status            │
│  ⚫ 19:14:10 - Issue #4 commit pushed             │
│  ⚫ 19:10:05 - New worktree created #3            │
└────────────────────────────────────────────────────┘
```

## 7. Testing Strategy

### Unit Tests
- `test_dashboard.py` - Server logic
- WebSocket connection handling
- State broadcasting
- File watch events

### Integration Tests
- End-to-end WebSocket communication
- Multi-client broadcast
- State synchronization

### Manual Tests
- Browser compatibility
- Reconnection handling
- Performance with many agents

## 8. Success Metrics

- ✅ Real-time updates (< 100ms latency)
- ✅ Support 10+ concurrent clients
- ✅ Zero config for local mode
- ✅ Works on Windows/Linux/Mac

## 9. Future Enhancements (Out of Scope)

- Historical charts and trends
- Agent performance analytics
- Mobile app
- Multi-repository dashboard
- Slack/Discord notifications

## 10. Implementation Checklist

- [ ] Install dependencies (websockets, watchdog)
- [ ] Create `context_md/dashboard.py` server
- [ ] Create `context_md/static/dashboard.html` UI
- [ ] Create `context_md/static/dashboard.css` styles
- [ ] Create `context_md/static/dashboard.js` client
- [ ] Add `dashboard` command to CLI
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Update documentation
- [ ] Test on all platforms

---

**Next Steps**: Begin Phase 1 - Backend WebSocket Server implementation
