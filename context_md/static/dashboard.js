// Context.md Real-Time Dashboard Client

class DashboardClient {
    constructor() {
        this.ws = null;
        this.reconnectInterval = 3000;
        this.reconnectTimer = null;
        this.maxActivityItems = 50;
        
        this.init();
    }
    
    init() {
        this.connectWebSocket();
        this.setupHeartbeat();
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        console.log(`[Dashboard] Connecting to ${wsUrl}...`);
        this.updateConnectionStatus('connecting');
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('[Dashboard] Connected');
                this.updateConnectionStatus('connected');
                this.addActivity('Connected to dashboard server');
                clearTimeout(this.reconnectTimer);
                
                // Request initial update
                this.send({ type: 'request_update' });
            };
            
            this.ws.onmessage = (event) => {
                this.handleMessage(event.data);
            };
            
            this.ws.onerror = (error) => {
                console.error('[Dashboard] WebSocket error:', error);
                this.updateConnectionStatus('disconnected');
            };
            
            this.ws.onclose = () => {
                console.log('[Dashboard] Disconnected');
                this.updateConnectionStatus('disconnected');
                this.addActivity('Disconnected from server');
                this.scheduleReconnect();
            };
        } catch (error) {
            console.error('[Dashboard] Failed to create WebSocket:', error);
            this.updateConnectionStatus('disconnected');
            this.scheduleReconnect();
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectTimer) return;
        
        console.log(`[Dashboard] Reconnecting in ${this.reconnectInterval}ms...`);
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connectWebSocket();
        }, this.reconnectInterval);
    }
    
    setupHeartbeat() {
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.send({ type: 'ping' });
            }
        }, 30000); // Ping every 30 seconds
    }
    
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }
    
    handleMessage(data) {
        try {
            const message = JSON.parse(data);
            
            switch (message.type) {
                case 'status_update':
                    this.updateDashboard(message.data);
                    this.updateLastUpdateTime(message.timestamp);
                    break;
                case 'pong':
                    console.log('[Dashboard] Pong received');
                    break;
                default:
                    console.warn('[Dashboard] Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('[Dashboard] Failed to parse message:', error);
        }
    }
    
    updateConnectionStatus(status) {
        const indicator = document.getElementById('connection-status');
        const statusText = indicator.querySelector('.status-text');
        
        indicator.className = `status-indicator ${status}`;
        
        switch (status) {
            case 'connected':
                statusText.textContent = 'Live';
                break;
            case 'connecting':
                statusText.textContent = 'Connecting...';
                break;
            case 'disconnected':
                statusText.textContent = 'Disconnected';
                break;
        }
    }
    
    updateDashboard(data) {
        // Update summary bar
        document.getElementById('mode').textContent = data.mode || '-';
        document.getElementById('active-agents').textContent = data.active_subagents || 0;
        
        const stuckEl = document.getElementById('stuck-issues');
        stuckEl.textContent = data.stuck_issues || 0;
        stuckEl.className = 'summary-value' + (data.stuck_issues > 0 ? ' error' : '');
        
        // Update agents grid
        this.updateAgentsGrid(data.worktrees || []);
        
        // Add activity for changes
        if (data.worktrees && data.worktrees.length > 0) {
            this.addActivity(`Status update: ${data.active_subagents} active agent(s)`);
        }
    }
    
    updateAgentsGrid(worktrees) {
        const container = document.getElementById('agents-container');
        
        if (!worktrees || worktrees.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No active agents</p>
                    <small>Agents will appear here when spawned</small>
                </div>
            `;
            return;
        }
        
        container.innerHTML = worktrees.map(wt => this.createAgentCard(wt)).join('');
    }
    
    createAgentCard(worktree) {
        const statusClass = worktree.is_stuck ? 'stuck' : 'active';
        const statusText = worktree.is_stuck ? 'Stuck' : 'Active';
        
        return `
            <div class="agent-card">
                <div class="agent-card-header">
                    <div class="agent-issue">Issue #${worktree.issue}</div>
                    <span class="agent-status-badge ${statusClass}">${statusText}</span>
                </div>
                <div class="agent-role">${this.capitalizeRole(worktree.role)}</div>
                <div class="agent-branch">${this.escapeHtml(worktree.branch)}</div>
                <div class="agent-meta">
                    <span>📝 ${worktree.commits || 0} commits</span>
                    <span>⏱️ ${this.formatTimeSince(worktree.hours_inactive)}h</span>
                </div>
            </div>
        `;
    }
    
    capitalizeRole(role) {
        return role.charAt(0).toUpperCase() + role.slice(1);
    }
    
    formatTimeSince(hours) {
        return typeof hours === 'number' ? hours.toFixed(1) : '0.0';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    addActivity(message) {
        const stream = document.getElementById('activity-stream');
        const now = new Date();
        const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
        
        const item = document.createElement('div');
        item.className = 'activity-item';
        item.innerHTML = `
            <span class="activity-time">${timeStr}</span>
            <span class="activity-message">${this.escapeHtml(message)}</span>
        `;
        
        // Prepend to show newest first
        if (stream.firstChild && stream.firstChild.classList.contains('activity-item')) {
            stream.insertBefore(item, stream.firstChild);
        } else {
            stream.innerHTML = '';
            stream.appendChild(item);
        }
        
        // Limit activity items
        while (stream.children.length > this.maxActivityItems) {
            stream.removeChild(stream.lastChild);
        }
    }
    
    updateLastUpdateTime(timestamp) {
        const el = document.getElementById('last-update');
        if (timestamp) {
            const date = new Date(timestamp);
            el.textContent = date.toLocaleTimeString();
        }
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Dashboard] Initializing...');
    new DashboardClient();
});
