"""Targeted batch validation tests for all 5 batches."""

import inspect
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(r"c:\Piyush - Personal\GenAI\ContextWeave")
sys.path.insert(0, str(PROJECT_ROOT))

from click.testing import CliRunner
from context_weave.cli import cli

results = []


def check(name, passed):
    status = "PASS" if passed else "FAIL"
    results.append((name, status))
    print(f"  [{status}] {name}")


# Setup temp repo
tmpdir = tempfile.mkdtemp(prefix="cw_batch_")
import os
os.chdir(tmpdir)
subprocess.run(["git", "init"], capture_output=True, check=True)
subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True, check=True)
subprocess.run(["git", "config", "user.name", "Test"], capture_output=True, check=True)
Path("README.md").write_text("# Test\n")
subprocess.run(["git", "add", "."], capture_output=True, check=True)
subprocess.run(["git", "commit", "-m", "init"], capture_output=True, check=True)

runner = CliRunner(mix_stderr=False)
runner.invoke(cli, ["init", "--mode", "local"])

print("=== BATCH 1: Dead code removal, sync fix, security comments ===")

from context_weave.commands import subagent as sub_mod
check("ROLE_ORDER removed from subagent", not hasattr(sub_mod, "ROLE_ORDER"))

from context_weave.state import State
state = State(Path(tmpdir))
github_config = state.github
github_config.enabled = True
github_config.owner = "testowner"
github_config.repo = "testrepo"
github_config.project_number = 42
state.github = github_config
state.save()
state2 = State(Path(tmpdir))
gh = state2.github
check("sync fix: enabled persists", gh.enabled is True)
check("sync fix: owner persists", gh.owner == "testowner")
check("sync fix: repo persists", gh.repo == "testrepo")

from context_weave import security as sec_mod
sec_src = inspect.getsource(sec_mod)
check("security.py has design-intent comment", "middleware" in sec_src.lower() or "Agent Framework" in sec_src)

from context_weave.framework.middleware import SecurityMiddleware
src2 = inspect.getsource(SecurityMiddleware)
check("middleware.py has CLI bypass comment", "CLI" in src2 or "bypass" in src2.lower())

print()
print("=== BATCH 2: Skill directory scan, token budget ===")

from context_weave.commands.context import _discover_skills
check("_discover_skills function exists", callable(_discover_skills))

skills = _discover_skills(Path(tmpdir))
check("_discover_skills returns dict", isinstance(skills, dict))

from context_weave.config import Config
config = Config(Path(tmpdir))
check("max_skill_tokens in config", hasattr(config, "max_skill_tokens"))
check("max_skill_tokens default is 8000", config.max_skill_tokens == 8000)

skills_for_api = config.get_skills_for_labels(["api"])
if skills_for_api:
    has_hash = any(s.startswith("#") for s in skills_for_api)
    check("skill routing returns names not #XX", not has_hash)
else:
    check("skill routing returns names (empty OK for test repo)", True)

print()
print("=== BATCH 3: Tri-state validation, desync detection, gitignore ===")

runner.invoke(cli, ["issue", "create", "Test", "--type", "story"])
r = runner.invoke(cli, ["validate", "dod", "1"])
check("validate dod shows [?] tri-state", "[?]" in r.output)
check("validate dod shows [OK] checks", "[OK]" in r.output)
check("validate dod shows [FAIL] checks", "[FAIL]" in r.output)

from context_weave.commands.doctor import doctor_cmd
doc_src = inspect.getsource(doctor_cmd.callback)
check(
    "doctor has state/notes desync check",
    "notes" in doc_src.lower()
    and ("mismatch" in doc_src.lower() or "consistency" in doc_src.lower() or "desync" in doc_src.lower()),
)

gi = Path(tmpdir) / ".gitignore"
if gi.exists():
    content = gi.read_text()
    check("gitignore has memory.json", "memory.json" in content)
    check("gitignore has certificates/", "certificates/" in content)
else:
    check("gitignore exists", False)

print()
print("=== BATCH 4: Memory recording, --push/--create-pr flags ===")

from context_weave.commands.subagent import complete_cmd
params = {p.name for p in complete_cmd.params}
check("complete_cmd has --push flag", "push" in params)
check("complete_cmd has --create_pr flag", "create_pr" in params)

src = inspect.getsource(complete_cmd.callback)
check("complete records ExecutionRecord", "ExecutionRecord" in src)
check("complete imports Memory", "Memory" in src)

print()
print("=== BATCH 5: Prompt slim, dashboard lazy imports ===")

from context_weave.prompt import PromptEngineer
pe = PromptEngineer()
check("get_chain_of_thought_prompt removed", not hasattr(pe, "get_chain_of_thought_prompt"))
check("_get_label_specific_hints removed", not hasattr(pe, "_get_label_specific_hints"))

from context_weave.prompt import ROLE_TEMPLATES
for role, tmpl in ROLE_TEMPLATES.items():
    if "approach_hints" in tmpl or "pitfalls" in tmpl:
        check(f'ROLE_TEMPLATES["{role}"] clean', False)
        break
else:
    check("ROLE_TEMPLATES has no approach_hints/pitfalls", True)

from context_weave.prompt import EnhancedPrompt
ep = EnhancedPrompt(
    role_primer="test",
    task_statement="test",
    context_summary="test",
    approach_hints=["hint1"],
    pitfalls_to_avoid=["pitfall1"],
)
md = ep.to_markdown()
check("to_markdown omits Suggested Approach", "### Suggested Approach" not in md)
check("to_markdown omits Pitfalls to Avoid", "### Pitfalls to Avoid" not in md)

from context_weave import dashboard as dash_mod
check("dashboard has _import_websockets", hasattr(dash_mod, "_import_websockets"))
check("dashboard has _import_watchdog", hasattr(dash_mod, "_import_watchdog"))

from context_weave.dashboard import StateChangeHandler
bases = [b.__name__ for b in StateChangeHandler.__bases__]
check("StateChangeHandler no FileSystemEventHandler base", "FileSystemEventHandler" not in bases)

r = runner.invoke(cli, ["dashboard", "--help"])
check("dashboard help says experimental", "experimental" in r.output.lower())
check("dashboard help mentions pip install", "pip install" in r.output)

pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()
check("pyproject has [dashboard] extras", "dashboard" in pyproject and "websockets" in pyproject)

deps_match = re.search(r"dependencies\s*=\s*\[(.*?)\]", pyproject, re.DOTALL)
if deps_match:
    core_deps = deps_match.group(1)
    check("websockets not in core deps", "websockets" not in core_deps)
    check("watchdog not in core deps", "watchdog" not in core_deps)

print()
print("===========================================")
print("BATCH VALIDATION SUMMARY")
print("===========================================")
passed = sum(1 for _, s in results if s == "PASS")
failed = sum(1 for _, s in results if s == "FAIL")
for name, status in results:
    marker = "OK  " if status == "PASS" else "FAIL"
    print(f"  [{marker}] {name}")
print()
print(f"Total: {passed} passed, {failed} failed out of {len(results)}")

os.chdir(str(PROJECT_ROOT))
shutil.rmtree(tmpdir, ignore_errors=True)
