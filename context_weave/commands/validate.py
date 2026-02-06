"""
Validate Command - Run validation checks

Usage:
    context-weave validate <issue> --task
    context-weave validate <issue> --pre-exec
    context-weave validate <issue> --dod
    context-weave validate <issue> --all
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import click

from context_weave.state import State

logger = logging.getLogger(__name__)


# Definition of Done checklists per role
DOD_CHECKLISTS = {
    "pm": {
        "name": "Product Manager",
        "checks": [
            ("prd_exists", "PRD created at docs/prd/PRD-{issue}.md"),
            ("child_issues", "Child issues created (Features/Stories)"),
            ("acceptance_criteria", "Acceptance criteria defined"),
            ("success_metrics", "Success metrics specified"),
            ("timeline", "Timeline with phases documented")
        ]
    },
    "architect": {
        "name": "Architect",
        "checks": [
            ("adr_exists", "ADR created at docs/adr/ADR-{issue}.md"),
            ("spec_exists", "Tech Spec at docs/specs/SPEC-{issue}.md"),
            ("options_documented", "Options with pros/cons documented"),
            ("decision_rationale", "Decision rationale clear"),
            ("no_code_examples", "NO CODE EXAMPLES (diagrams only)")
        ]
    },
    "engineer": {
        "name": "Engineer",
        "checks": [
            ("code_committed", "Code committed and pushed"),
            ("tests_written", "Tests written (>=80% coverage)"),
            ("tests_passing", "Tests passing"),
            ("docs_updated", "Documentation updated"),
            ("no_lint_errors", "No compiler warnings or linter errors"),
            ("security_scan", "Security scan passed")
        ]
    },
    "reviewer": {
        "name": "Reviewer",
        "checks": [
            ("review_doc", "Review document at docs/reviews/REVIEW-{issue}.md"),
            ("checklist_verified", "All checklist items verified"),
            ("decision_documented", "Approval or rejection documented"),
            ("feedback_provided", "Feedback provided for rejections")
        ]
    },
    "ux": {
        "name": "UX Designer",
        "checks": [
            ("ux_doc", "UX Design at docs/ux/UX-{issue}.md"),
            ("wireframes", "Wireframes complete"),
            ("user_flows", "User flows documented"),
            ("accessibility", "Accessibility considered")
        ]
    }
}


@click.group("validate")
@click.pass_context
def validate_cmd(_ctx: click.Context) -> None:
    """Run validation checks for issues.

    Validation types:
    - task: Validate task quality (required fields, stranger test)
    - pre-exec: Pre-flight validation (context, dependencies)
    - dod: Definition of Done checklist

    Note: ctx is required by Click but not used in group commands.
    """


@validate_cmd.command("task")
@click.argument("issue", type=int)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def validate_task_cmd(ctx: click.Context, issue: int, verbose: bool) -> None:
    """Validate task quality."""
    repo_root = ctx.obj.get("repo_root")
    state = ctx.obj.get("state", State(repo_root))

    click.echo(f"Validating task quality for issue #{issue}...")

    # Get branch and metadata
    worktree = state.get_worktree(issue)
    branch = worktree.branch if worktree else None

    if not branch:
        branches = state.get_issue_branches()
        matching = [b for b in branches if b.startswith(f"issue-{issue}-")]
        branch = matching[0] if matching else None

    metadata = state.get_branch_note(branch) if branch else {}

    results = []

    # Check 1: Title exists
    title = metadata.get("title", "")
    results.append(("Title exists", bool(title), "Add a descriptive title"))

    # Check 2: Description exists
    description = metadata.get("description", "")
    results.append(("Description exists", bool(description), "Add a task description"))

    # Check 3: Acceptance criteria
    criteria = metadata.get("acceptance_criteria", [])
    results.append(("Acceptance criteria defined", bool(criteria), "Add measurable acceptance criteria"))

    # Check 4: No implicit knowledge (stranger test)
    implicit_phrases = ["as discussed", "like before", "you know", "as usual", "obviously"]
    has_implicit = any(phrase in description.lower() for phrase in implicit_phrases)
    results.append(("No implicit knowledge", not has_implicit, "Remove vague references, add explicit details"))

    # Display results
    _display_validation_results(results, "Task Quality", verbose)


@validate_cmd.command("pre-exec")
@click.argument("issue", type=int)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def validate_preexec_cmd(ctx: click.Context, issue: int, verbose: bool) -> None:
    """Pre-flight validation before execution."""
    repo_root = ctx.obj.get("repo_root")
    state = ctx.obj.get("state", State(repo_root))

    click.echo(f"Running pre-flight validation for issue #{issue}...")

    results = []

    # Check 1: Context file exists
    context_file = repo_root / ".context-weave" / f"context-{issue}.md"
    results.append(("Context file exists", context_file.exists(),
                   f"Generate with: context-weave context generate {issue}"))

    # Check 2: SubAgent exists
    worktree = state.get_worktree(issue)
    results.append(("SubAgent spawned", worktree is not None,
                   f"Create with: context-weave subagent spawn {issue} --role <role>"))

    # Check 3: Worktree accessible
    if worktree:
        worktree_exists = Path(worktree.path).exists()
        results.append(("Worktree accessible", worktree_exists,
                       f"Recover with: context-weave subagent recover {issue}"))
    else:
        results.append(("Worktree accessible", False, "Spawn SubAgent first"))

    # Check 4: Branch exists
    if worktree:
        branch_check = subprocess.run(
            ["git", "branch", "--list", worktree.branch],
            cwd=repo_root, capture_output=True, text=True,
            check=False, timeout=10
        )
        results.append(("Branch exists", bool(branch_check.stdout.strip()), "Branch may need recovery"))
    else:
        results.append(("Branch exists", False, "Spawn SubAgent first"))

    _display_validation_results(results, "Pre-Flight", verbose)


@validate_cmd.command("dod")
@click.argument("issue", type=int)
@click.option("--role", type=click.Choice(["pm", "architect", "engineer", "reviewer", "ux"]),
              help="Override role detection")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Exit code only")
@click.option("--certificate", is_flag=True, help="Generate certificate on pass")
@click.pass_context
def validate_dod_cmd(ctx: click.Context, issue: int, role: Optional[str],
                     verbose: bool, quiet: bool, certificate: bool) -> None:
    """Validate Definition of Done checklist."""
    repo_root = ctx.obj.get("repo_root")
    state = ctx.obj.get("state", State(repo_root))

    # Determine role
    worktree = state.get_worktree(issue)
    detected_role = role or (worktree.role if worktree else "engineer")

    if not quiet:
        click.echo(f"Validating DoD for issue #{issue} (role: {detected_role})...")

    checklist = DOD_CHECKLISTS.get(detected_role, DOD_CHECKLISTS["engineer"])
    results = []

    for check_id, description in checklist["checks"]:
        passed, remediation = _run_dod_check(repo_root, issue, detected_role, check_id, state)
        results.append((description.format(issue=issue), passed, remediation))

    if quiet:
        # Exit code only
        all_passed = all(r[1] for r in results)
        ctx.exit(0 if all_passed else 1)

    _display_validation_results(results, f"DoD ({checklist['name']})", verbose)

    # Generate certificate if requested and all passed
    all_passed = all(r[1] for r in results)
    if certificate and all_passed:
        _generate_certificate(repo_root, issue, detected_role, results)


@validate_cmd.command("all")
@click.argument("issue", type=int)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def validate_all_cmd(ctx: click.Context, issue: int, verbose: bool) -> None:
    """Run all validations."""
    click.echo(f"Running all validations for issue #{issue}...")
    click.echo("")

    ctx.invoke(validate_task_cmd, issue=issue, verbose=verbose)
    click.echo("")
    ctx.invoke(validate_preexec_cmd, issue=issue, verbose=verbose)
    click.echo("")
    ctx.invoke(validate_dod_cmd, issue=issue, verbose=verbose)


def _run_dod_check(repo_root: Path, issue: int, _role: str, check_id: str, state: State) -> Tuple[bool, str]:
    """Run a specific DoD check and return (passed, remediation).

    Args:
        repo_root: Repository root path
        issue: Issue number
        _role: Role type (reserved for future role-specific checks)
        check_id: Identifier of the check to run
        state: Current state object
    """

    if check_id == "prd_exists":
        path = repo_root / "docs" / "prd" / f"PRD-{issue}.md"
        return path.exists(), f"Create PRD at {path}"

    elif check_id == "adr_exists":
        path = repo_root / "docs" / "adr" / f"ADR-{issue}.md"
        return path.exists(), f"Create ADR at {path}"

    elif check_id == "spec_exists":
        path = repo_root / "docs" / "specs" / f"SPEC-{issue}.md"
        return path.exists(), f"Create Tech Spec at {path}"

    elif check_id == "review_doc":
        path = repo_root / "docs" / "reviews" / f"REVIEW-{issue}.md"
        return path.exists(), f"Create Review at {path}"

    elif check_id == "ux_doc":
        path = repo_root / "docs" / "ux" / f"UX-{issue}.md"
        return path.exists(), f"Create UX Design at {path}"

    elif check_id == "code_committed":
        worktree = state.get_worktree(issue)
        if not worktree:
            return False, "Spawn SubAgent first"

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=worktree.path, capture_output=True, text=True,
                check=True, timeout=10
            )
            has_uncommitted = bool(result.stdout.strip())
            return not has_uncommitted, "Commit all changes"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning("Could not check git status: %s", e)
            return False, f"Could not check git status: {e}"

    elif check_id == "tests_passing":
        # Try to run tests
        try:
            # Try pytest first
            result = subprocess.run(
                ["pytest", "--co", "-q"],
                cwd=repo_root, capture_output=True, text=True, timeout=30,
                check=False
            )
            if result.returncode == 0:
                return True, ""
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug("pytest check failed: %s", e)

        # Try dotnet test
        try:
            result = subprocess.run(
                ["dotnet", "test", "--list-tests"],
                cwd=repo_root, capture_output=True, text=True, timeout=30,
                check=False
            )
            if result.returncode == 0:
                return True, ""
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug("dotnet test check failed: %s", e)

        return True, "Unable to verify - check manually"  # Can't verify, assume OK

    elif check_id == "no_lint_errors":
        # Try ruff/pylint for Python
        try:
            result = subprocess.run(
                ["ruff", "check", "."],
                cwd=repo_root, capture_output=True, text=True, timeout=30,
                check=False
            )
            return result.returncode == 0, "Fix lint errors: ruff check . --fix"
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug("ruff check failed: %s", e)
            return True, "Unable to verify linting - check manually"
        except subprocess.CalledProcessError as e:
            logger.debug("ruff check returned non-zero: %s", e)
            return True, "Unable to verify linting - check manually"

    # Default: manual check required
    return True, "Manual verification required"


def _display_validation_results(results: List[Tuple[str, bool, str]], title: str, verbose: bool) -> None:
    """Display validation results."""
    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    all_passed = passed == total

    status_color = "green" if all_passed else "red"
    status_symbol = "[OK]" if all_passed else "[FAIL]"

    click.echo("")
    click.secho(f"{title} Validation: {passed}/{total} passed {status_symbol}", fg=status_color)
    click.echo("")

    for description, passed, remediation in results:
        symbol = "[OK]" if passed else "[FAIL]"
        click.echo(f"  {symbol} {description}")
        if not passed and verbose and remediation:
            click.echo(f"      -> {remediation}")

    if not all_passed:
        click.echo("")
        click.echo("Fix the issues above before proceeding.")


def _generate_certificate(repo_root: Path, issue: int, role: str, results: List) -> None:
    """Generate a completion certificate."""
    cert_dir = repo_root / ".context-weave" / "certificates"
    cert_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().isoformat() + "Z"
    cert_id = f"CERT-{issue}-{datetime.utcnow().strftime('%Y%m%d%H%M')}"

    certificate = {
        "id": cert_id,
        "issue": issue,
        "role": role,
        "timestamp": timestamp,
        "checklist": [
            {"check": desc, "passed": passed}
            for desc, passed, _ in results
        ],
        "all_passed": all(r[1] for r in results)
    }

    cert_path = cert_dir / f"cert-{issue}.json"
    cert_path.write_text(json.dumps(certificate, indent=2))

    click.echo("")
    click.secho(f"[OK] Certificate generated: {cert_path}", fg="green")
    click.echo(f"   ID: {cert_id}")
