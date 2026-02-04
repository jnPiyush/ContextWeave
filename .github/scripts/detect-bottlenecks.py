#!/usr/bin/env python3
"""
Bottleneck Detection Script

Analyzes issue flow through workflow stages (Backlog → In Progress → In Review → Done)
to detect bottlenecks, queue buildup, and resource constraints.

Runs weekly to generate bottleneck report.
"""

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from github import Github
except ImportError:
    print("[ERROR] PyGithub not installed. Run: pip install PyGithub")
    sys.exit(1)


# Workflow stages and their GitHub representations
WORKFLOW_STAGES = {
    "backlog": ["Backlog"],
    "in_progress": ["In Progress"],
    "in_review": ["In Review"],
    "ready": ["Ready"],
    "done": ["Done"]
}

# Bottleneck thresholds
MAX_QUEUE_SIZE = 5  # Issues waiting in a stage
MAX_AVG_WAIT_DAYS = 3  # Average days in stage


def get_issue_status(issue) -> str:
    """Determine issue status from labels or projects."""
    labels = [label.name.lower() for label in issue.labels]
    
    # Check for status in labels
    if "in progress" in ' '.join(labels):
        return "in_progress"
    elif "in review" in ' '.join(labels):
        return "in_review"
    elif "ready" in ' '.join(labels):
        return "ready"
    elif "done" in ' '.join(labels):
        return "done"
    else:
        return "backlog"


def calculate_wait_time(issue, status: str) -> float:
    """Calculate days in current status."""
    # Simplified: use updated_at as proxy for status change time
    now = datetime.now(timezone.utc)
    last_update = issue.updated_at.replace(tzinfo=timezone.utc)
    
    delta = now - last_update
    return delta.total_seconds() / (24 * 3600)  # Convert to days


def detect_bottlenecks(repo_name: str, token: str) -> Dict:
    """Detect workflow bottlenecks."""
    g = Github(token)
    repo = g.get_repo(repo_name)
    
    # Get all open issues
    open_issues = list(repo.get_issues(state='open'))
    
    # Analyze by stage
    stage_analysis = defaultdict(lambda: {
        "queue_size": 0,
        "issues": [],
        "wait_times": [],
        "avg_wait_days": 0.0
    })
    
    for issue in open_issues:
        if issue.pull_request:
            continue
        
        status = get_issue_status(issue)
        wait_days = calculate_wait_time(issue, status)
        
        stage_analysis[status]["queue_size"] += 1
        stage_analysis[status]["issues"].append({
            "number": issue.number,
            "title": issue.title,
            "wait_days": round(wait_days, 1),
            "assignee": issue.assignee.login if issue.assignee else "unassigned"
        })
        stage_analysis[status]["wait_times"].append(wait_days)
    
    # Calculate averages
    for status, data in stage_analysis.items():
        if data["wait_times"]:
            data["avg_wait_days"] = sum(data["wait_times"]) / len(data["wait_times"])
    
    # Detect bottlenecks
    bottlenecks = []
    
    for status, data in stage_analysis.items():
        is_bottleneck = False
        reasons = []
        
        # Check queue size
        if data["queue_size"] > MAX_QUEUE_SIZE:
            is_bottleneck = True
            reasons.append(f"Queue size ({data['queue_size']}) exceeds threshold ({MAX_QUEUE_SIZE})")
        
        # Check average wait time
        if data["avg_wait_days"] > MAX_AVG_WAIT_DAYS:
            is_bottleneck = True
            reasons.append(f"Avg wait time ({data['avg_wait_days']:.1f} days) exceeds threshold ({MAX_AVG_WAIT_DAYS} days)")
        
        if is_bottleneck:
            bottlenecks.append({
                "stage": status,
                "queue_size": data["queue_size"],
                "avg_wait_days": round(data["avg_wait_days"], 1),
                "reasons": reasons,
                "recommendation": get_recommendation(status, data)
            })
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_open_issues": len(open_issues),
        "stage_analysis": {k: {
            "queue_size": v["queue_size"],
            "avg_wait_days": round(v["avg_wait_days"], 1),
            "top_issues": sorted(v["issues"], key=lambda x: x["wait_days"], reverse=True)[:5]
        } for k, v in stage_analysis.items()},
        "bottlenecks_detected": len(bottlenecks),
        "bottlenecks": bottlenecks
    }


def get_recommendation(stage: str, data: Dict) -> str:
    """Get recommendation for bottleneck."""
    recommendations = {
        "in_progress": "Consider adding engineering capacity or breaking work into smaller tasks",
        "in_review": "Add reviewer capacity or streamline review process",
        "backlog": "Prioritize and assign issues to move forward",
        "ready": "Ensure prerequisites are met and assign to appropriate role"
    }
    return recommendations.get(stage, "Review workflow and resource allocation")


def generate_report(analysis: Dict) -> str:
    """Generate human-readable bottleneck report."""
    lines = [
        "=" * 60,
        "  WORKFLOW BOTTLENECK ANALYSIS",
        "=" * 60,
        "",
        f"Generated: {analysis['timestamp']}",
        f"Total Open Issues: {analysis['total_open_issues']}",
        "",
    ]
    
    if analysis["bottlenecks_detected"] == 0:
        lines.extend([
            "✅ NO BOTTLENECKS DETECTED",
            "",
            "Workflow is flowing smoothly.",
            "All stages are within acceptable thresholds.",
        ])
    else:
        lines.extend([
            f"⚠️  {analysis['bottlenecks_detected']} BOTTLENECK(S) DETECTED",
            "",
        ])
        
        for bn in analysis["bottlenecks"]:
            lines.extend([
                f"Stage: {bn['stage'].upper()}",
                f"  Queue: {bn['queue_size']} issues",
                f"  Avg Wait: {bn['avg_wait_days']} days",
                f"  Reasons:",
            ])
            for reason in bn["reasons"]:
                lines.append(f"    • {reason}")
            lines.extend([
                f"  Recommendation:",
                f"    → {bn['recommendation']}",
                "",
            ])
    
    lines.extend([
        "Stage Summary:",
        "",
    ])
    
    for stage, data in analysis["stage_analysis"].items():
        if data["queue_size"] > 0:
            lines.append(f"  {stage.upper()}: {data['queue_size']} issues (avg {data['avg_wait_days']} days wait)")
    
    lines.extend([
        "",
        "=" * 60,
    ])
    
    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("[ERROR] GITHUB_TOKEN environment variable not set")
        return 1
    
    repo_name = os.environ.get("GITHUB_REPOSITORY", "jnPiyush/ContextMD")
    
    print(f"[INFO] Detecting workflow bottlenecks in {repo_name}...")
    
    try:
        analysis = detect_bottlenecks(repo_name, token)
        
        # Save analysis
        report_dir = Path(".agent-context")
        report_dir.mkdir(exist_ok=True)
        
        report_file = report_dir / f"bottleneck-{datetime.now().strftime('%Y-%m-%d')}.json"
        report_file.write_text(json.dumps(analysis, indent=2))
        
        # Generate and display report
        report_text = generate_report(analysis)
        print(report_text)
        
        # Save text report
        text_file = report_dir / f"bottleneck-{datetime.now().strftime('%Y-%m-%d')}.txt"
        text_file.write_text(report_text, encoding='utf-8')
        
        print(f"\n[SUCCESS] Bottleneck analysis complete")
        print(f"   JSON: {report_file}")
        print(f"   Report: {text_file}")
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
