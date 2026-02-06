# Real-Time Dashboard User Guide

## Overview

The Context.md Real-Time Dashboard provides live monitoring of agent status through a web-based interface with WebSocket updates.

## Quick Start

```bash
# Start dashboard (opens browser automatically)
context-md dashboard

# Start on custom port
context-md dashboard --port 8080

# Start without opening browser
context-md dashboard --no-browser
```

## Features

### Real-Time Updates
- **Live Status**: Agent status updates pushed instantly via WebSocket
- **No Polling**: Event-driven updates when `.agent-context/state.json` changes
- **Auto-Reconnect**: Automatically reconnects if connection is lost

### Agent Cards
Each active agent displays:
- Issue number and role (Engineer, PM, Architect, etc.)
- Branch name
- Activity status (Active/Stuck)
- Commit count
- Time since last activity

### Activity Stream
- Real-time activity log
- Timestamps for all events
- Auto-scrolling to show latest events
- Maintains last 50 events

### Summary Bar
- Operating mode (Local/GitHub/Hybrid)
- Active agent count
- Stuck issue count (highlighted in red if > 0)
- Last update timestamp

## Usage

### Starting the Dashboard

```bash
$ context-md dashboard
[SUCCESS] Starting dashboard server...
  Host: localhost
  Port: 8765
  URL: http://localhost:8765

[SUCCESS] Opening browser...
[INFO] Press Ctrl+C to stop
```

The dashboard will open automatically in your default browser.

### Viewing Status

The dashboard updates automatically when:
- New agents are spawned
- Agents complete work
- State changes occur
- Commits are made

### Monitoring Multiple Agents

The dashboard supports multiple concurrent agents:
- Each agent gets its own card
- Color-coded status indicators
- Real-time activity tracking
- Stuck issue detection

## Configuration

### Port Configuration

```bash
# Use custom port
context-md dashboard --port 3000
```

### Host Configuration

```bash
# Listen on all interfaces (use with caution)
context-md dashboard --host 0.0.0.0
```

**Security Note**: Only use `0.0.0.0` on trusted networks. Default `localhost` restricts access to local machine.

## Architecture

### Components

1. **WebSocket Server** (`context_md/dashboard.py`)
   - Async server using `websockets` library
   - Serves static files via HTTP
   - Broadcasts state updates to connected clients

2. **File Watcher**
   - Monitors `.agent-context/` directory
   - Detects state changes using `watchdog`
   - Triggers broadcasts on modifications

3. **Frontend** (`context_md/static/`)
   - `dashboard.html` - UI structure
   - `dashboard.css` - Dark mode styling
   - `dashboard.js` - WebSocket client

### Communication Protocol

**Server → Client**:
```json
{
  "type": "status_update",
  "timestamp": "2026-02-05T19:30:00Z",
  "data": {
    "mode": "local",
    "active_subagents": 2,
    "stuck_issues": 0,
    "worktrees": [...]
  }
}
```

**Client → Server**:
```json
{
  "type": "request_update"
}
```

## Troubleshooting

### Dashboard Won't Start

**Error**: `Address already in use`
```bash
# Use different port
context-md dashboard --port 8766
```

### No Updates Showing

1. Check if Context.md is initialized:
   ```bash
   context-md status
   ```

2. Verify `.agent-context/` directory exists

3. Check browser console for WebSocket errors

### Connection Issues

If "Disconnected" status shown:
- Check if server is still running
- Dashboard auto-reconnects every 3 seconds
- Check firewall settings

### Browser Not Opening

```bash
# Manually open: http://localhost:8765
context-md dashboard --no-browser
```

## Keyboard Shortcuts

- **Ctrl+C** - Stop dashboard server
- **F5** / **Ctrl+R** - Refresh browser page

## Best Practices

1. **Leave Running**: Keep dashboard open while working with agents
2. **Multiple Windows**: Open in separate browser window/tab
3. **Port Conflicts**: Use custom port if 8765 is occupied
4. **Network Access**: Use `localhost` for security on shared machines

## Integration with Workflows

The dashboard automatically integrates with:
- `context-md subagent spawn` - Shows new agents instantly
- `context-md status` - Same data, different presentation
- Git operations - Detects commits and state changes

## Performance

- **Latency**: < 100ms from state change to dashboard update
- **Clients**: Supports 10+ concurrent browser connections
- **Resource**: Minimal CPU usage (event-driven)
- **Memory**: ~10MB for server + file watcher

## Comparison: Dashboard vs CLI Status

| Feature | Dashboard | CLI Status |
|---------|-----------|-------------|
| **Update Method** | Push (WebSocket) | Poll (5s intervals) |
| **Interface** | Web browser | Terminal |
| **Visuals** | Rich UI, cards, colors | Text-based |
| **Activity Log** | Yes (50 events) | No |
| **Multi-Agent** | Grid view | List view |
| **Resource Usage** | Moderate | Minimal |

**When to use Dashboard**: Active development, monitoring multiple agents
**When to use CLI**: Quick checks, scripting, SSH sessions

## Security Considerations

- **Default**: Listens on `localhost` only
- **Authentication**: None (local access assumed)
- **Encryption**: No TLS (use `localhost`)
- **Firewall**: No inbound rules needed for localhost

For remote access, consider:
- SSH tunnel: `ssh -L 8765:localhost:8765 user@host`
- Reverse proxy with authentication
- VPN for network access

## Examples

### Monitor Build Process

```bash
# Terminal 1: Start dashboard
context-md dashboard

# Terminal 2: Spawn agent
context-md subagent spawn 123 engineer

# Dashboard shows: Issue #123 Engineer card appears
```

### Multi-Agent Workflow

```bash
# Start dashboard
context-md dashboard

# Spawn multiple agents
context-md subagent spawn 100 pm
context-md subagent spawn 101 engineer
context-md subagent spawn 102 reviewer

# Dashboard shows: 3 agent cards with real-time updates
```

## Related Commands

- `context-md status` - CLI status view
- `context-md status --watch` - CLI watch mode (polling)
- `context-md subagent list` - List active agents
- `context-md subagent status <issue>` - Individual agent status

## Support

For issues or questions:
- GitHub Issues: https://github.com/jnPiyush/ContextMD/issues
- Check logs: `~/.context-md/logs/context-md.log`
