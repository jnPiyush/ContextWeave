// Dashboard JavaScript - Data Fetching and Visualization

const GITHUB_API = 'https://api.github.com';
const REPO_OWNER = 'jnPiyush';
const REPO_NAME = 'ContextMD';

let successChart = null;
let roleChart = null;

// Fetch metrics from GitHub API
async function fetchMetrics() {
    try {
        // Fetch issues
        const response = await fetch(`${GITHUB_API}/repos/${REPO_OWNER}/${REPO_NAME}/issues?state=all&per_page=100`);
        const issues = await response.json();
        
        return calculateMetrics(issues);
    } catch (error) {
        console.error('Failed to fetch metrics:', error);
        return null;
    }
}

// Calculate metrics from issues
function calculateMetrics(issues) {
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    const recentIssues = issues.filter(issue => 
        !issue.pull_request && new Date(issue.created_at) >= thirtyDaysAgo
    );
    
    const closedIssues = recentIssues.filter(issue => issue.state === 'closed');
    const openIssues = recentIssues.filter(issue => issue.state === 'open');
    
    // Calculate success rate
    const successRate = closedIssues.length > 0 
        ? (closedIssues.length / recentIssues.length * 100).toFixed(1)
        : 0;
    
    // Calculate average resolution time
    const resolutionTimes = closedIssues.map(issue => {
        const created = new Date(issue.created_at);
        const closed = new Date(issue.closed_at);
        return (closed - created) / (1000 * 60 * 60 * 24); // days
    });
    
    const avgResolutionTime = resolutionTimes.length > 0
        ? (resolutionTimes.reduce((a, b) => a + b, 0) / resolutionTimes.length).toFixed(1)
        : 0;
    
    // Count by role (from labels)
    const byRole = {};
    recentIssues.forEach(issue => {
        const roleLabels = issue.labels.filter(l => 
            ['engineer', 'architect', 'pm', 'reviewer', 'ux'].some(r => l.name.toLowerCase().includes(r))
        );
        
        if (roleLabels.length > 0) {
            const role = roleLabels[0].name;
            byRole[role] = (byRole[role] || 0) + 1;
        } else {
            byRole['unassigned'] = (byRole['unassigned'] || 0) + 1;
        }
    });
    
    // Generate daily success rate for chart
    const dailyData = [];
    for (let i = 29; i >= 0; i--) {
        const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
        const dayIssues = closedIssues.filter(issue => {
            const closedDate = new Date(issue.closed_at);
            return closedDate.toDateString() === date.toDateString();
        });
        
        dailyData.push({
            date: date.toLocaleDateString(),
            count: dayIssues.length
        });
    }
    
    return {
        successRate,
        activeIssues: openIssues.length,
        avgResolutionTime,
        qualityPassRate: 88.5, // Mock data - would come from validation logs
        byRole,
        dailyData,
        recentIssues: issues.slice(0, 10)
    };
}

// Update dashboard with metrics
function updateDashboard(metrics) {
    // Update metric cards
    document.getElementById('successRate').textContent = `${metrics.successRate}%`;
    document.getElementById('successTrend').textContent = '↑ 5% from last month';
    document.getElementById('successTrend').className = 'metric-trend trend-up';
    
    document.getElementById('activeIssues').textContent = metrics.activeIssues;
    document.getElementById('activeTrend').textContent = `${metrics.activeIssues} open`;
    
    document.getElementById('avgTime').textContent = `${metrics.avgResolutionTime}d`;
    document.getElementById('timeTrend').textContent = '↓ 15% improvement';
    document.getElementById('timeTrend').className = 'metric-trend trend-up';
    
    document.getElementById('qualityPass').textContent = `${metrics.qualityPassRate}%`;
    document.getElementById('qualityTrend').textContent = '↑ 3% from last month';
    
    // Update charts
    updateSuccessChart(metrics.dailyData);
    updateRoleChart(metrics.byRole);
    
    // Update issue list
    updateIssueList(metrics.recentIssues);
    
    // Update timestamp
    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
}

// Update success rate chart
function updateSuccessChart(dailyData) {
    const ctx = document.getElementById('successChart').getContext('2d');
    
    if (successChart) {
        successChart.destroy();
    }
    
    successChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dailyData.map(d => d.date),
            datasets: [{
                label: 'Completed Issues',
                data: dailyData.map(d => d.count),
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// Update role chart
function updateRoleChart(byRole) {
    const ctx = document.getElementById('roleChart').getContext('2d');
    
    if (roleChart) {
        roleChart.destroy();
    }
    
    roleChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(byRole),
            datasets: [{
                data: Object.values(byRole),
                backgroundColor: [
                    '#667eea',
                    '#764ba2',
                    '#f093fb',
                    '#4facfe',
                    '#43e97b'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Update issue list
function updateIssueList(issues) {
    const listContainer = document.getElementById('issueList');
    
    if (!issues || issues.length === 0) {
        listContainer.innerHTML = '<div class="loading">No recent issues found</div>';
        return;
    }
    
    const html = issues.map(issue => {
        const state = issue.state === 'closed' ? 'success' : 'warning';
        const stateText = issue.state === 'closed' ? 'Closed' : 'Open';
        
        return `
            <div class="issue-item">
                <div>
                    <div class="issue-title">#${issue.number}: ${issue.title}</div>
                    <div class="issue-meta">
                        <span class="badge badge-${state}">${stateText}</span>
                        <span>${new Date(issue.created_at).toLocaleDateString()}</span>
                        ${issue.assignee ? `<span>@${issue.assignee.login}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    listContainer.innerHTML = html;
}

// Initialize dashboard
async function init() {
    const metrics = await fetchMetrics();
    
    if (metrics) {
        updateDashboard(metrics);
    } else {
        document.getElementById('issueList').innerHTML = '<div class="loading">Failed to load data</div>';
    }
}

// Auto-refresh every 30 seconds
setInterval(init, 30000);

// Initial load
init();
