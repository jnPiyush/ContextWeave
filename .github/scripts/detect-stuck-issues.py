#!/usr/bin/env python3
"""
Automated Stuck Issue Detection

Detects issues that have been "In Progress" for too long without activity
and automatically escalates them with needs:help label.

Runs every 30 minutes via GitHub Actions (health-monitoring.yml).
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

from github import Github

# Stuck thresholds by issue type (hours)
STUCK_THRESHOLDS = {
    "type:bug": 12,
    "type:story": 24,
    "type:feature": 48,
    "type:epic": 72,
    "type:spike": 36,
    "type:docs": 18,
}
DEFAULT_THRESHOLD = 24


def get_stuck_threshold(labels: List[str]) -> int:
    """Get stuck threshold based on issue type label."""
    for label in labels:
        if label in STUCK_THRESHOLDS:
            return STUCK_THRESHOLDS[label]
    return DEFAULT_THRESHOLD


def detect_stuck_issues(repo_name: str, token: str) -> List[Dict]:
    """Detect stuck issues in repository."""
    g = Github(token)
    repo = g.get_repo(repo_name)
    
    stuck_issues = []
    now = datetime.now(timezone.utc)
    
    # Get all open issues with "In Progress" status (via Projects or labels)
    # For simplicity, look for issues with specific patterns
    open_issues = repo.get_issues(state='open')
    
    for issue in open_issues:
        # Skip pull requests
        if issue.pull_request:
            continue
        
        # Check if issue has activity
        labels = [label.name for label in issue.labels]
        threshold_hours = get_stuck_threshold(labels)
        
        # Get last activity time
        last_activity = issue.updated_at
        
        # Calculate hours since last activity
        hours_inactive = (now - last_activity.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        
        if hours_inactive > threshold_hours:
            # Check if already escalated
            has_needs_help = "needs:help" in labels
            
            if not has_needs_help:
                stuck_issues.append({
                    "issue": issue.number,
                    "title": issue.title,
                    "hours_inactive": int(hours_inactive),
                    "threshold": threshold_hours,
                    "assignee": issue.assignee.login if issue.assignee else "unassigned",
                    "labels": labels,
                })
    
    return stuck_issues


def escalate_issue(repo_name: str, token: str, issue_num: int, hours_inactive: int) -> None:
    """Escalate stuck issue by adding needs:help label and comment."""
    g = Github(token)
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(issue_num)
    
    # Add needs:help label
    issue.add_to_labels("needs:help")
    
    # Add comment
    comment = f"""🚨 **Stuck Issue Detected**

This issue has been inactive for **{hours_inactive} hours** without commits or updates.

**Automatic Escalation:**
- Added `needs:help` label
- Issue requires attention

**Next Steps:**
1. Review current blocker
2. Update issue with progress/blockers
3. Request help if needed
4. Consider breaking into smaller tasks

---
*Automated by Context.md Health Monitoring*
"""
    issue.create_comment(comment)
    
    print(f"✅ Escalated issue #{issue_num}")


def main() -> int:
    """Main entry point."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        return 1
    
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    if not repo_name:
        print("❌ GITHUB_REPOSITORY environment variable not set")
        return 1
    
    print(f"🔍 Detecting stuck issues in {repo_name}...")
    
    try:
        stuck = detect_stuck_issues(repo_name, token)
        
        if not stuck:
            print("✅ No stuck issues detected")
            return 0
        
        print(f"⚠️  Found {len(stuck)} stuck issue(s)")
        
        # Save report
        report_dir = Path(".agent-context")
        report_dir.mkdir(exist_ok=True)
        
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "stuck_count": len(stuck),
            "stuck_issues": stuck
        }
        
        report_file = report_dir / "stuck-report.json"
        report_file.write_text(json.dumps(report, indent=2))
        
        # Escalate each stuck issue
        for item in stuck:
            escalate_issue(repo_name, token, item["issue"], item["hours_inactive"])
        
        print(f"✅ Escalated {len(stuck)} stuck issue(s)")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
