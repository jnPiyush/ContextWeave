#!/usr/bin/env python3
"""
Learning Loop - Pattern Analysis

Analyzes completed issues to identify success/failure patterns
and generate actionable insights for instruction improvements.

Runs monthly to analyze last 30 days of closed issues.
"""

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    from github import Github
except ImportError:
    print("❌ PyGithub not installed. Run: pip install PyGithub")
    sys.exit(1)


def analyze_closed_issues(repo_name: str, token: str, days: int = 30) -> Dict:
    """Analyze closed issues from last N days."""
    g = Github(token)
    repo = g.get_repo(repo_name)
    
    since = datetime.now(timezone.utc) - timedelta(days=days)
    closed_issues = repo.get_issues(state='closed', since=since)
    
    analysis = {
        "period": f"{days} days",
        "start_date": since.isoformat(),
        "end_date": datetime.now(timezone.utc).isoformat(),
        "total_issues": 0,
        "by_type": defaultdict(int),
        "by_role": defaultdict(lambda: {"total": 0, "success": 0, "failure": 0}),
        "success_count": 0,
        "failure_count": 0,
        "common_failures": [],
        "avg_resolution_time_hours": 0.0,
        "revision_cycles": [],
    }
    
    resolution_times = []
    failure_types = Counter()
    
    for issue in closed_issues:
        if issue.pull_request:
            continue
        
        analysis["total_issues"] += 1
        
        # Extract issue type from labels
        labels = [label.name for label in issue.labels]
        issue_type = next((l for l in labels if l.startswith("type:")), "type:unknown")
        analysis["by_type"][issue_type] += 1
        
        # Detect role from labels or assignee
        role = "unknown"
        for label in labels:
            if "engineer" in label.lower():
                role = "engineer"
            elif "architect" in label.lower():
                role = "architect"
            elif label.lower() in ["pm", "product-manager"]:
                role = "pm"
            elif "reviewer" in label.lower():
                role = "reviewer"
        
        # Determine success/failure based on labels
        is_success = "state_reason:completed" in labels or issue.state_reason == "completed"
        is_failure = "needs:changes" in labels or "needs:fixes" in labels
        
        if is_success:
            analysis["success_count"] += 1
            analysis["by_role"][role]["success"] += 1
        elif is_failure:
            analysis["failure_count"] += 1
            analysis["by_role"][role]["failure"] += 1
        
        analysis["by_role"][role]["total"] += 1
        
        # Calculate resolution time
        if issue.created_at and issue.closed_at:
            delta = issue.closed_at - issue.created_at
            resolution_times.append(delta.total_seconds() / 3600)
        
        # Detect failure types from comments
        for comment in issue.get_comments():
            body = comment.body.lower()
            if "missing test" in body or "no tests" in body:
                failure_types["missing_tests"] += 1
            elif "incomplete" in body or "missing context" in body:
                failure_types["incomplete_context"] += 1
            elif "lint" in body or "format" in body:
                failure_types["code_quality"] += 1
            elif "security" in body or "vulnerability" in body:
                failure_types["security_issue"] += 1
    
    # Calculate averages
    if resolution_times:
        analysis["avg_resolution_time_hours"] = sum(resolution_times) / len(resolution_times)
    
    # Top failure types
    analysis["common_failures"] = [
        {"type": ftype, "count": count, "fix": get_fix_recommendation(ftype)}
        for ftype, count in failure_types.most_common(5)
    ]
    
    # Calculate success rate
    total = analysis["success_count"] + analysis["failure_count"]
    analysis["success_rate"] = (analysis["success_count"] / total * 100) if total > 0 else 0
    
    return analysis


def get_fix_recommendation(failure_type: str) -> str:
    """Get fix recommendation for failure type."""
    fixes = {
        "missing_tests": "Strengthen DoD enforcement, add test coverage checks",
        "incomplete_context": "Improve task creation validation, enforce references field",
        "code_quality": "Enable pre-commit hooks, stricter linting",
        "security_issue": "Add security scan to CI/CD, training on OWASP",
    }
    return fixes.get(failure_type, "Review and address root cause")


def generate_instruction_updates(analysis: Dict) -> List[Dict]:
    """Generate instruction update recommendations."""
    updates = []
    
    # Check if success rate is low
    if analysis["success_rate"] < 85:
        updates.append({
            "file": ".github/agents/engineer.agent.md",
            "section": "Quality Standards",
            "recommendation": f"Success rate is {analysis['success_rate']:.1f}% - strengthen quality requirements",
            "action": "Add emphasis on test coverage and DoD compliance"
        })
    
    # Check common failure patterns
    for failure in analysis["common_failures"]:
        if failure["count"] >= 3:
            if failure["type"] == "missing_tests":
                updates.append({
                    "file": ".github/agents/engineer.agent.md",
                    "section": "Testing Requirements",
                    "recommendation": f"Missing tests occurred {failure['count']} times",
                    "action": "Add: 'CRITICAL: Tests MUST be written BEFORE marking code complete'"
                })
            elif failure["type"] == "incomplete_context":
                updates.append({
                    "file": ".github/templates/story.yml",
                    "section": "Task Template",
                    "recommendation": f"Incomplete context occurred {failure['count']} times",
                    "action": "Make References and Documentation fields mandatory"
                })
    
    return updates


def main() -> int:
    """Main entry point."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        return 1
    
    repo_name = os.environ.get("GITHUB_REPOSITORY", "jnPiyush/ContextMD")
    
    print(f"📊 Analyzing closed issues in {repo_name}...")
    
    try:
        analysis = analyze_closed_issues(repo_name, token, days=30)
        
        # Save analysis report
        report_dir = Path(".agent-context")
        report_dir.mkdir(exist_ok=True)
        
        report_file = report_dir / f"learning-{datetime.now().strftime('%Y-%m')}.json"
        report_file.write_text(json.dumps(analysis, indent=2, default=str))
        
        print(f"✅ Analysis complete: {report_file}")
        print(f"   Total issues: {analysis['total_issues']}")
        print(f"   Success rate: {analysis['success_rate']:.1f}%")
        
        # Generate instruction updates
        updates = generate_instruction_updates(analysis)
        
        if updates:
            updates_file = report_dir / "instruction-updates.json"
            updates_file.write_text(json.dumps(updates, indent=2))
            print(f"✅ Generated {len(updates)} instruction update recommendations")
            print(f"   See: {updates_file}")
        else:
            print("✅ No instruction updates needed - system performing well")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
