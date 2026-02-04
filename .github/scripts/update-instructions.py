#!/usr/bin/env python3
"""
Instruction Update Generator

Reads learning analysis and generates Pull Request with instruction updates
for Skills.md, AGENTS.md, and agent files based on failure patterns.

Requires human approval before merge.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def load_instruction_updates() -> List[Dict]:
    """Load instruction updates from learning analysis."""
    updates_file = Path(".agent-context/instruction-updates.json")
    
    if not updates_file.exists():
        print("[INFO] No instruction updates found")
        return []
    
    return json.loads(updates_file.read_text())


def generate_update_content(update: Dict) -> str:
    """Generate the actual content to add to file."""
    file = update["file"]
    section = update["section"]
    recommendation = update["recommendation"]
    action = update["action"]
    
    # Generate markdown content based on file type
    if "engineer.agent.md" in file:
        return f"""
### Common Mistakes - Updated {datetime.now().strftime('%Y-%m-%d')}

**Pattern Detected**: {recommendation}

**Action**: {action}

> [WARNING] This section was auto-generated based on failure pattern analysis.
> Review and adjust as needed.
"""
    elif "story.yml" in file:
        return f"""
# Learning Loop Update - {datetime.now().strftime('%Y-%m-%d')}
# Pattern: {recommendation}
# Action: {action}
"""
    else:
        return f"""
## Learning Loop Update - {datetime.now().strftime('%Y-%m-%d')}

**Pattern**: {recommendation}

**Recommendation**: {action}
"""


def create_update_branch(updates: List[Dict]) -> str:
    """Create git branch for updates."""
    import subprocess
    
    branch_name = f"learning-updates-{datetime.now().strftime('%Y-%m')}"
    
    try:
        # Create and checkout new branch
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            check=True,
            capture_output=True
        )
        
        print(f"[SUCCESS] Created branch: {branch_name}")
        return branch_name
        
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to create branch: {e}")
        sys.exit(1)


def apply_updates(updates: List[Dict]) -> List[str]:
    """Apply updates to files."""
    modified_files = []
    
    for update in updates:
        file_path = Path(update["file"])
        
        if not file_path.exists():
            print(f"[WARNING] File not found: {file_path}")
            continue
        
        # Read current content
        content = file_path.read_text()
        
        # Generate update content
        update_content = generate_update_content(update)
        
        # Append to end of file
        updated_content = content + "\n" + update_content + "\n"
        
        # Write back
        file_path.write_text(updated_content)
        
        modified_files.append(str(file_path))
        print(f"[SUCCESS] Updated: {file_path}")
    
    return modified_files


def commit_and_push(branch: str, modified_files: List[str]) -> None:
    """Commit and push changes."""
    import subprocess
    
    try:
        # Add modified files
        subprocess.run(
            ["git", "add"] + modified_files,
            check=True
        )
        
        # Commit
        commit_msg = f"chore: learning loop instruction updates ({datetime.now().strftime('%Y-%m')})"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            check=True,
            capture_output=True
        )
        
        # Push
        subprocess.run(
            ["git", "push", "-u", "origin", branch],
            check=True,
            capture_output=True
        )
        
        print(f"[SUCCESS] Pushed changes to {branch}")
        
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to commit/push: {e}")
        sys.exit(1)


def create_pull_request(branch: str, updates: List[Dict]) -> None:
    """Create pull request for updates."""
    try:
        from github import Github
    except ImportError:
        print("[WARNING] PyGithub not installed - skipping PR creation")
        print("   Install with: pip install PyGithub")
        return
    
    token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    
    if not token or not repo_name:
        print("[WARNING] GITHUB_TOKEN or GITHUB_REPOSITORY not set")
        return
    
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # Create PR body
        body = f"""## Learning Loop Instruction Updates

**Period**: {datetime.now().strftime('%B %Y')}

### Updates Applied

"""
        for update in updates:
            body += f"- **{update['file']}** ({update['section']}): {update['recommendation']}\n"
        
        body += """
### Review Required

These updates were automatically generated based on failure pattern analysis.

**Action Required:**
1. Review each change
2. Adjust wording/formatting as needed
3. Approve and merge when satisfied

---
*Automated by Context.md Learning Loop*
"""
        
        pr = repo.create_pull(
            title=f"chore: learning loop updates ({datetime.now().strftime('%Y-%m')})",
            body=body,
            head=branch,
            base="master"
        )
        
        # Add label
        pr.add_to_labels("learning-loop")
        
        print(f"[SUCCESS] Created PR: {pr.html_url}")
        
    except Exception as e:
        print(f"[WARNING] Failed to create PR: {e}")
        print(f"   Manually create PR from branch: {branch}")


def main() -> int:
    """Main entry point."""
    print("[INFO] Generating instruction updates...")
    
    updates = load_instruction_updates()
    
    if not updates:
        print("[SUCCESS] No updates needed")
        return 0
    
    print(f"Found {len(updates)} recommended updates")
    
    # Create branch
    branch = create_update_branch(updates)
    
    # Apply updates
    modified_files = apply_updates(updates)
    
    if not modified_files:
        print("[WARNING] No files were modified")
        return 1
    
    # Commit and push
    commit_and_push(branch, modified_files)
    
    # Create PR
    create_pull_request(branch, updates)
    
    print("[SUCCESS] Instruction update PR created")
    print("   Review and merge when ready")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
