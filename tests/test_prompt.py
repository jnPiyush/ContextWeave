"""
Tests for Prompt Engineering Module

Coverage target: 80%+
"""

import pytest

from context_weave.prompt import ROLE_TEMPLATES, EnhancedPrompt, PromptEngineer


class TestEnhancedPrompt:
    """Test EnhancedPrompt dataclass."""

    def test_create_basic_prompt(self):
        """Test creating a basic enhanced prompt."""
        prompt = EnhancedPrompt(
            role_primer="You are an engineer",
            task_statement="Implement feature X",
            context_summary="Working on auth module"
        )

        assert prompt.role_primer == "You are an engineer"
        assert prompt.task_statement == "Implement feature X"
        assert prompt.inputs == []
        assert prompt.outputs == []

    def test_create_full_prompt(self):
        """Test creating a fully specified prompt."""
        prompt = EnhancedPrompt(
            role_primer="You are an engineer",
            task_statement="Implement feature X",
            context_summary="Working on auth module",
            inputs=["Specification document", "API contracts"],
            outputs=["Production code", "Unit tests"],
            constraints=["Must use existing patterns", "No external dependencies"],
            success_criteria=["Tests pass", "Coverage ≥80%"],
            quality_checklist=["Code compiles", "No warnings"],
            approach_hints=["Start with tests", "Use TDD"],
            pitfalls_to_avoid=["Don't skip validation"],
            next_role="reviewer",
            handoff_requirements=["PR created", "Tests passing"]
        )

        assert len(prompt.inputs) == 2
        assert len(prompt.outputs) == 2
        assert len(prompt.constraints) == 2
        assert prompt.next_role == "reviewer"

    def test_to_markdown_minimal(self):
        """Test markdown generation with minimal data."""
        prompt = EnhancedPrompt(
            role_primer="You are a PM",
            task_statement="Define requirements",
            context_summary=""
        )

        markdown = prompt.to_markdown()

        assert "### Role" in markdown
        assert "You are a PM" in markdown
        assert "### Task" in markdown
        assert "Define requirements" in markdown

    def test_to_markdown_full(self):
        """Test markdown generation with all fields."""
        prompt = EnhancedPrompt(
            role_primer="You are an engineer",
            task_statement="Implement feature",
            context_summary="Bug fix context",
            inputs=["Spec doc"],
            outputs=["Code", "Tests"],
            constraints=["No breaking changes"],
            success_criteria=["Tests pass"],
            quality_checklist=["Lint clean"],
            approach_hints=["Start with tests"],
            pitfalls_to_avoid=["Don't skip tests"],
            next_role="reviewer",
            handoff_requirements=["PR ready"]
        )

        markdown = prompt.to_markdown()

        assert "### Inputs" in markdown
        assert "### Expected Outputs" in markdown
        assert "### Constraints" in markdown
        assert "### Success Criteria" in markdown
        assert "### Quality Checklist" in markdown
        assert "### Suggested Approach" in markdown
        assert "### Pitfalls to Avoid" in markdown
        assert "### Handoff to Reviewer" in markdown


class TestRoleTemplates:
    """Test role-specific templates."""

    def test_all_roles_have_templates(self):
        """Test that all expected roles have templates."""
        expected_roles = ["pm", "architect", "engineer", "reviewer", "ux"]

        for role in expected_roles:
            assert role in ROLE_TEMPLATES, f"Missing template for {role}"

    def test_template_structure(self):
        """Test that templates have required fields."""
        required_fields = [
            "role_primer",
            "default_outputs",
            "default_constraints",
            "quality_checklist",
            "approach_hints",
            "pitfalls"
        ]

        for role, template in ROLE_TEMPLATES.items():
            for field in required_fields:
                assert field in template, f"Missing {field} in {role} template"

    def test_pm_template_content(self):
        """Test PM template has appropriate content."""
        pm = ROLE_TEMPLATES["pm"]

        assert "Product Manager" in pm["role_primer"]
        assert any("PRD" in o for o in pm["default_outputs"])
        assert pm["next_role"] == "architect"

    def test_engineer_template_content(self):
        """Test engineer template has appropriate content."""
        eng = ROLE_TEMPLATES["engineer"]

        assert "Software Engineer" in eng["role_primer"]
        assert any("test" in o.lower() for o in eng["default_outputs"])
        assert eng["next_role"] == "reviewer"

    def test_reviewer_has_no_next_role(self):
        """Test reviewer is end of workflow."""
        reviewer = ROLE_TEMPLATES["reviewer"]

        assert reviewer["next_role"] is None


class TestPromptEngineer:
    """Test PromptEngineer class."""

    @pytest.fixture
    def engineer(self):
        """Create a PromptEngineer instance."""
        return PromptEngineer()

    def test_enhance_prompt_basic(self, engineer):
        """Test basic prompt enhancement."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Add login functionality",
            role="engineer",
            issue_number=100,
            issue_type="story",
            labels=["type:story"]
        )

        assert enhanced.role_primer is not None
        assert "100" in enhanced.task_statement
        assert "login" in enhanced.task_statement.lower()
        assert len(enhanced.outputs) > 0

    def test_enhance_prompt_for_pm(self, engineer):
        """Test prompt enhancement for PM role."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Define authentication system requirements",
            role="pm",
            issue_number=50,
            issue_type="epic",
            labels=["type:epic"]
        )

        assert "Product Manager" in enhanced.role_primer
        assert any("PRD" in o for o in enhanced.outputs)
        assert enhanced.next_role == "architect"

    def test_enhance_prompt_for_architect(self, engineer):
        """Test prompt enhancement for architect role."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Design the API architecture",
            role="architect",
            issue_number=75,
            issue_type="feature",
            labels=["type:feature", "api"]
        )

        assert "Architect" in enhanced.role_primer
        assert any("ADR" in o for o in enhanced.outputs)
        # Should have API-specific hints from labels
        assert any("REST" in h or "API" in h for h in enhanced.approach_hints)

    def test_enhance_prompt_for_bug(self, engineer):
        """Test prompt enhancement for bug fix."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Fix login page 500 error",
            role="engineer",
            issue_number=200,
            issue_type="bug",
            labels=["type:bug"]
        )

        # Bug-specific success criteria
        assert any("root cause" in c.lower() for c in enhanced.success_criteria)

    def test_enhance_prompt_with_context(self, engineer):
        """Test prompt enhancement with additional context."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Implement OAuth login",
            role="engineer",
            issue_number=150,
            issue_type="story",
            labels=["type:story", "security"],
            context={
                "dependencies": ["#100", "#120"],
                "spec_path": "docs/specs/SPEC-150.md"
            }
        )

        assert "spec" in enhanced.context_summary.lower() or "dependencies" in enhanced.context_summary.lower()
        # Security label should add security hints
        assert any("security" in h.lower() or "validate" in h.lower() for h in enhanced.approach_hints)

    def test_enhance_prompt_extracts_constraints(self, engineer):
        """Test that constraints are extracted from prompt."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Add feature X. Must not break existing API. Should not use external libraries.",
            role="engineer",
            issue_number=300,
            issue_type="story",
            labels=["type:story"]
        )

        # Should have extracted constraints
        assert len(enhanced.constraints) > len(ROLE_TEMPLATES["engineer"]["default_constraints"])

    def test_get_chain_of_thought_prompt(self, engineer):
        """Test chain-of-thought prompt generation."""
        cot = engineer.get_chain_of_thought_prompt(
            role="engineer",
            task="Implement user authentication"
        )

        assert "systematically" in cot.lower()
        assert "user authentication" in cot.lower()
        assert "1." in cot  # Numbered steps

    def test_cot_prompt_for_different_roles(self, engineer):
        """Test CoT prompts are different per role."""
        pm_cot = engineer.get_chain_of_thought_prompt("pm", "Define feature")
        eng_cot = engineer.get_chain_of_thought_prompt("engineer", "Build feature")

        assert "Problem" in pm_cot  # PM focuses on problem
        assert "Implement" in eng_cot or "Tests" in eng_cot  # Engineer focuses on implementation

    def test_validate_prompt_completeness_valid(self, engineer):
        """Test validation of complete prompt."""
        prompt = EnhancedPrompt(
            role_primer="You are an engineer",
            task_statement="Implement the authentication module with JWT support",
            context_summary="Security feature",
            inputs=["Spec document"],
            outputs=["Code", "Tests"],
            constraints=["Use existing patterns"],
            success_criteria=["Tests pass", "Security review approved"],
            quality_checklist=["Lint clean"],
            approach_hints=["TDD approach"],
            pitfalls_to_avoid=["Don't skip validation"]
        )

        validation = engineer.validate_prompt_completeness(prompt)

        assert validation["is_valid"] is True
        assert len(validation["issues"]) == 0
        assert validation["completeness_score"] > 0.8

    def test_validate_prompt_completeness_invalid(self, engineer):
        """Test validation catches missing elements."""
        prompt = EnhancedPrompt(
            role_primer="",  # Missing
            task_statement="Do something",  # Too short
            context_summary=""
        )

        validation = engineer.validate_prompt_completeness(prompt)

        assert validation["is_valid"] is False
        assert len(validation["issues"]) > 0
        assert validation["completeness_score"] < 0.5

    def test_validate_prompt_warnings(self, engineer):
        """Test validation generates warnings for optional but recommended elements."""
        prompt = EnhancedPrompt(
            role_primer="You are an engineer",
            task_statement="Implement feature X with all requirements met",
            context_summary="Working on auth",
            outputs=["Code"],
            success_criteria=["Works correctly"]
            # Missing: constraints, approach_hints, pitfalls
        )

        validation = engineer.validate_prompt_completeness(prompt)

        assert validation["is_valid"] is True  # Required elements present
        assert len(validation["warnings"]) > 0  # But has warnings

    def test_completeness_score_calculation(self, engineer):
        """Test completeness score is calculated correctly."""
        # Minimal prompt
        minimal = EnhancedPrompt(
            role_primer="Role",
            task_statement="Task",
            context_summary=""
        )

        # Full prompt
        full = EnhancedPrompt(
            role_primer="Role",
            task_statement="Task with enough detail to be useful",
            context_summary="Context",
            inputs=["Input"],
            outputs=["Output"],
            constraints=["Constraint"],
            success_criteria=["Criterion"],
            quality_checklist=["Check"],
            approach_hints=["Hint"],
            pitfalls_to_avoid=["Pitfall"]
        )

        minimal_validation = engineer.validate_prompt_completeness(minimal)
        full_validation = engineer.validate_prompt_completeness(full)

        assert full_validation["completeness_score"] > minimal_validation["completeness_score"]
        assert full_validation["completeness_score"] == 1.0


class TestLabelSpecificEnhancements:
    """Test label-specific prompt enhancements."""

    @pytest.fixture
    def engineer(self):
        return PromptEngineer()

    def test_security_label_adds_hints(self, engineer):
        """Test security label adds security-specific hints."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Add authentication",
            role="engineer",
            issue_number=100,
            issue_type="story",
            labels=["type:story", "security"]
        )

        # Should have security hints
        hints_text = " ".join(enhanced.approach_hints).lower()
        assert "owasp" in hints_text or "validate" in hints_text or "auth" in hints_text

    def test_api_label_adds_hints(self, engineer):
        """Test api label adds API-specific hints."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Create REST endpoint",
            role="engineer",
            issue_number=100,
            issue_type="story",
            labels=["type:story", "api"]
        )

        hints_text = " ".join(enhanced.approach_hints).lower()
        assert "rest" in hints_text or "endpoint" in hints_text or "api" in hints_text

    def test_database_label_adds_hints(self, engineer):
        """Test database label adds DB-specific hints."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Add user table",
            role="engineer",
            issue_number=100,
            issue_type="story",
            labels=["type:story", "database"]
        )

        hints_text = " ".join(enhanced.approach_hints).lower()
        assert "query" in hints_text or "index" in hints_text or "migration" in hints_text

    def test_multiple_labels_combine_hints(self, engineer):
        """Test multiple labels combine their hints."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Add secure API endpoint",
            role="engineer",
            issue_number=100,
            issue_type="story",
            labels=["type:story", "api", "security"]
        )

        # Should have hints from both labels
        base_hints_count = len(ROLE_TEMPLATES["engineer"]["approach_hints"])
        assert len(enhanced.approach_hints) > base_hints_count


class TestHandoffIntegration:
    """Test handoff workflow between roles."""

    @pytest.fixture
    def engineer(self):
        return PromptEngineer()

    def test_pm_to_architect_handoff(self, engineer):
        """Test PM prepares handoff for architect."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Define auth system",
            role="pm",
            issue_number=100,
            issue_type="epic",
            labels=["type:epic"]
        )

        assert enhanced.next_role == "architect"
        assert len(enhanced.handoff_requirements) > 0
        assert any("PRD" in r for r in enhanced.handoff_requirements)

    def test_architect_to_engineer_handoff(self, engineer):
        """Test architect prepares handoff for engineer."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Design API architecture",
            role="architect",
            issue_number=100,
            issue_type="feature",
            labels=["type:feature"]
        )

        assert enhanced.next_role == "engineer"
        assert len(enhanced.handoff_requirements) > 0
        assert any("spec" in r.lower() for r in enhanced.handoff_requirements)

    def test_engineer_to_reviewer_handoff(self, engineer):
        """Test engineer prepares handoff for reviewer."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Implement feature",
            role="engineer",
            issue_number=100,
            issue_type="story",
            labels=["type:story"]
        )

        assert enhanced.next_role == "reviewer"
        assert len(enhanced.handoff_requirements) > 0
        assert any("test" in r.lower() for r in enhanced.handoff_requirements)

    def test_reviewer_end_of_workflow(self, engineer):
        """Test reviewer is end of workflow."""
        enhanced = engineer.enhance_prompt(
            raw_prompt="Review PR",
            role="reviewer",
            issue_number=100,
            issue_type="story",
            labels=["type:story"]
        )

        assert enhanced.next_role is None
        assert len(enhanced.handoff_requirements) == 0
