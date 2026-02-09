"""
Prompt Engineering Module for ContextWeave

Implements prompt engineering best practices to structure and enhance
user prompts before handing over to role-based agents.

This module acts as a "Prompt Helper" that:
1. Analyzes raw user prompts/issues
2. Structures them using proven patterns
3. Adds role-specific framing
4. Enhances clarity and specificity
5. Includes success criteria
6. Formats for optimal agent performance

Best Practices Applied:
- Role Priming: Clear role definition at the start
- Task Decomposition: Break complex tasks into steps
- Output Specification: Define expected deliverables
- Constraint Definition: Clarify boundaries and limits
- Context Anchoring: Ground in relevant knowledge
- Chain-of-Thought: Encourage reasoning steps
- Success Criteria: Define measurable outcomes
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EnhancedPrompt:
    """A structured, enhanced prompt ready for agent consumption."""

    # Core elements
    role_primer: str  # Sets the agent's persona/role
    task_statement: str  # Clear statement of what to do
    context_summary: str  # Relevant background info

    # Structured requirements
    inputs: List[str] = field(default_factory=list)  # What's provided
    outputs: List[str] = field(default_factory=list)  # Expected deliverables
    constraints: List[str] = field(default_factory=list)  # Boundaries/limits

    # Success definition
    success_criteria: List[str] = field(default_factory=list)  # How to measure success
    quality_checklist: List[str] = field(default_factory=list)  # Quality gates

    # Guidance
    approach_hints: List[str] = field(default_factory=list)  # Suggested approach
    pitfalls_to_avoid: List[str] = field(default_factory=list)  # Common mistakes

    # Handoff preparation
    next_role: Optional[str] = None  # Who receives output
    handoff_requirements: List[str] = field(default_factory=list)  # What next role needs

    def to_markdown(self) -> str:
        """Convert to structured markdown format."""
        sections = []

        # Role Primer
        sections.append(f"### Role\n\n{self.role_primer}")

        # Task Statement
        sections.append(f"### Task\n\n{self.task_statement}")

        # Context
        if self.context_summary:
            sections.append(f"### Context\n\n{self.context_summary}")

        # Inputs
        if self.inputs:
            inputs_text = "\n".join(f"- {i}" for i in self.inputs)
            sections.append(f"### Inputs (What You Have)\n\n{inputs_text}")

        # Outputs
        if self.outputs:
            outputs_text = "\n".join(f"- {o}" for o in self.outputs)
            sections.append(f"### Expected Outputs\n\n{outputs_text}")

        # Constraints
        if self.constraints:
            constraints_text = "\n".join(f"- [!] {c}" for c in self.constraints)
            sections.append(f"### Constraints\n\n{constraints_text}")

        # Success Criteria
        if self.success_criteria:
            criteria_text = "\n".join(f"- [x] {c}" for c in self.success_criteria)
            sections.append(f"### Success Criteria\n\n{criteria_text}")

        # Quality Checklist
        if self.quality_checklist:
            checklist_text = "\n".join(f"- [ ] {c}" for c in self.quality_checklist)
            sections.append(f"### Quality Checklist\n\n{checklist_text}")

        # Handoff
        if self.next_role and self.handoff_requirements:
            handoff_text = "\n".join(f"- {r}" for r in self.handoff_requirements)
            sections.append(f"### Handoff to {self.next_role.title()}\n\n{handoff_text}")

        return "\n\n---\n\n".join(sections)


# Role-specific prompt templates
ROLE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "pm": {
        "role_primer": (
            "You are a **Product Manager Agent** responsible for defining clear, "
            "actionable product requirements. Your outputs enable engineering teams "
            "to build exactly what users need without ambiguity."
        ),
        "default_outputs": [
            "Product Requirements Document (PRD) at `docs/prd/PRD-{issue}.md`",
            "Child Feature/Story issues with complete context",
            "Success metrics and acceptance criteria",
            "Risk assessment and mitigation strategies"
        ],
        "default_constraints": [
            "All requirements must pass the 'stranger test' - executable by someone unfamiliar with the project",
            "No implementation details - focus on WHAT, not HOW",
            "Include measurable success criteria",
            "Reference existing documentation and related issues"
        ],
        "quality_checklist": [
            "Problem statement is clear and specific",
            "User goals are defined with measurable outcomes",
            "Scope is bounded (in-scope and out-of-scope defined)",
            "Dependencies are identified with links",
            "Acceptance criteria are testable",
            "Child issues are standalone (no assumed context)"
        ],
        "next_role": "architect",
        "handoff_requirements": [
            "PRD document with complete context",
            "Clear success metrics",
            "Prioritized feature list",
            "Technical constraints identified (if any)"
        ]
    },

    "architect": {
        "role_primer": (
            "You are a **Solution Architect Agent** responsible for designing robust, "
            "scalable technical solutions. Your designs enable engineers to implement "
            "features correctly the first time without architectural surprises."
        ),
        "default_outputs": [
            "Architecture Decision Record (ADR) at `docs/adr/ADR-{issue}.md`",
            "Technical Specification at `docs/specs/SPEC-{issue}.md`",
            "Component diagrams and data flow (Mermaid/ASCII)",
            "API contracts (if applicable)"
        ],
        "default_constraints": [
            "NO CODE EXAMPLES - use diagrams and descriptions only",
            "Follow existing architectural patterns in the codebase",
            "Consider security, performance, and scalability",
            "Document trade-offs and alternatives considered"
        ],
        "quality_checklist": [
            "Solution addresses all requirements from PRD",
            "Trade-offs are documented with rationale",
            "Security implications considered",
            "Performance impact assessed",
            "Integration points clearly defined",
            "Rollback strategy documented"
        ],
        "next_role": "engineer",
        "handoff_requirements": [
            "Complete technical specification",
            "Clear component boundaries",
            "Data models and API contracts",
            "Test strategy outline"
        ]
    },

    "engineer": {
        "role_primer": (
            "You are a **Software Engineer Agent** responsible for implementing "
            "production-quality code. Your code must be secure, tested, documented, "
            "and maintainable by other engineers."
        ),
        "default_outputs": [
            "Production code implementing the specification",
            "Unit tests with >=80% coverage",
            "Integration tests for critical paths",
            "Updated documentation (inline + README)"
        ],
        "default_constraints": [
            "Follow the technical specification exactly",
            "Minimum 80% test coverage for new code",
            "No hardcoded secrets or credentials",
            "All inputs must be validated",
            "SQL queries must use parameterization"
        ],
        "quality_checklist": [
            "Code compiles without warnings",
            "All tests pass",
            "Coverage >=80% for new code",
            "Security checklist completed",
            "Documentation is updated",
            "Code review guidelines followed"
        ],
        "next_role": "reviewer",
        "handoff_requirements": [
            "All tests passing",
            "Coverage report generated",
            "Code committed with issue reference",
            "PR created (if applicable)"
        ]
    },

    "reviewer": {
        "role_primer": (
            "You are a **Code Reviewer Agent** responsible for ensuring code quality, "
            "security, and maintainability. Your reviews catch issues before they "
            "reach production and help engineers improve."
        ),
        "default_outputs": [
            "Review document at `docs/reviews/REVIEW-{issue}.md`",
            "Approval decision (APPROVE/REQUEST_CHANGES/COMMENT)",
            "Specific, actionable feedback",
            "Security and performance observations"
        ],
        "default_constraints": [
            "Review against the specification, not personal preference",
            "Provide specific line references for issues",
            "Distinguish blocking issues from suggestions",
            "Be constructive - explain the WHY"
        ],
        "quality_checklist": [
            "Code matches specification requirements",
            "Tests are comprehensive and meaningful",
            "Security best practices followed",
            "Error handling is appropriate",
            "Code is readable and maintainable",
            "Documentation is accurate"
        ],
        "next_role": None,  # End of workflow
        "handoff_requirements": []
    },

    "ux": {
        "role_primer": (
            "You are a **UX Designer Agent** responsible for creating user-centered "
            "designs that are intuitive, accessible, and delightful. Your designs "
            "enable engineers to build the right user experience."
        ),
        "default_outputs": [
            "UX Design document at `docs/ux/UX-{issue}.md`",
            "Wireframes or mockups",
            "User flow diagrams",
            "Accessibility considerations"
        ],
        "default_constraints": [
            "Follow accessibility guidelines (WCAG 2.1 AA)",
            "Consider mobile and desktop experiences",
            "Design for error states and edge cases",
            "Use existing design system components"
        ],
        "quality_checklist": [
            "User goals are clearly supported",
            "Flow is intuitive and discoverable",
            "Error states are handled gracefully",
            "Accessibility requirements met",
            "Consistent with design system",
            "Edge cases considered"
        ],
        "next_role": "architect",
        "handoff_requirements": [
            "Complete wireframes/mockups",
            "User flow documentation",
            "Interaction specifications",
            "Accessibility requirements"
        ]
    }
}


class PromptEngineer:
    """
    Enhances and structures user prompts using prompt engineering best practices.

    This acts as a "helper" that preprocesses prompts before handing them
    to role-based agents, improving clarity and completeness.
    """

    def __init__(self) -> None:
        self.templates: Dict[str, Dict[str, Any]] = ROLE_TEMPLATES

    def enhance_prompt(
        self,
        raw_prompt: str,
        role: str,
        issue_number: int,
        issue_type: str,
        labels: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> EnhancedPrompt:
        """
        Enhance a raw prompt for a specific role.

        Args:
            raw_prompt: Original user prompt/issue description
            role: Target agent role (pm, architect, engineer, etc.)
            issue_number: Issue being worked on
            issue_type: Type of issue (epic, feature, story, bug)
            labels: Issue labels for context
            context: Additional context (dependencies, previous work, etc.)

        Returns:
            EnhancedPrompt: Structured, enhanced prompt
        """
        context = context or {}
        template = self.templates.get(role, self.templates["engineer"])

        # Build role primer
        role_primer = template["role_primer"]

        # Analyze and enhance the task statement
        task_statement = self._enhance_task_statement(raw_prompt, issue_type, issue_number)

        # Build context summary
        context_summary = self._build_context_summary(context, labels, issue_type)

        # Determine inputs based on workflow position
        inputs = self._determine_inputs(role, context)

        # Get outputs with issue number substitution
        outputs = [o.format(issue=issue_number) for o in template["default_outputs"]]

        # Get constraints
        constraints = template["default_constraints"].copy()
        constraints.extend(self._extract_constraints_from_prompt(raw_prompt))

        # Build success criteria from acceptance criteria and template
        success_criteria = self._build_success_criteria(raw_prompt, issue_type)

        # Quality checklist
        quality_checklist = template["quality_checklist"].copy()

        # Handoff info
        next_role = template.get("next_role")
        handoff_requirements = template.get("handoff_requirements", [])

        return EnhancedPrompt(
            role_primer=role_primer,
            task_statement=task_statement,
            context_summary=context_summary,
            inputs=inputs,
            outputs=outputs,
            constraints=constraints,
            success_criteria=success_criteria,
            quality_checklist=quality_checklist,
            approach_hints=[],
            pitfalls_to_avoid=[],
            next_role=next_role,
            handoff_requirements=handoff_requirements
        )

    def _enhance_task_statement(self, raw_prompt: str, issue_type: str, issue_number: int) -> str:
        """Enhance the raw prompt into a clear task statement."""
        # Clean up the prompt
        cleaned = raw_prompt.strip()

        # Add issue type context
        type_context = {
            "epic": "Define the complete scope and break down into deliverable features for",
            "feature": "Design and specify the implementation approach for",
            "story": "Implement the following user story:",
            "bug": "Investigate and fix the following issue:",
            "spike": "Research and document findings for",
            "docs": "Create or update documentation for"
        }

        prefix = type_context.get(issue_type, "Complete the following task:")

        # Structure the task
        task = f"{prefix}\n\n**Issue #{issue_number}**: {cleaned}"

        # Add clarity prompt
        task += "\n\n*Before starting, ensure you understand the full scope and have all required context.*"

        return task

    def _build_context_summary(
        self,
        context: Dict[str, Any],
        labels: List[str],
        issue_type: str
    ) -> str:
        """Build a context summary from available information."""
        parts = []

        # Issue type context
        parts.append(f"**Issue Type**: {issue_type}")

        # Labels
        if labels:
            parts.append(f"**Labels**: {', '.join(f'`{lbl}`' for lbl in labels)}")

        # Dependencies
        if context.get("dependencies"):
            deps = context["dependencies"]
            parts.append(f"**Dependencies**: {deps}")

        # Previous work
        if context.get("previous_session"):
            parts.append(f"**Previous Session**: {context['previous_session']}")

        # Related PRD/Spec
        if context.get("prd_path"):
            parts.append(f"**PRD**: [{context['prd_path']}]({context['prd_path']})")
        if context.get("spec_path"):
            parts.append(f"**Spec**: [{context['spec_path']}]({context['spec_path']})")

        return "\n".join(parts) if parts else "_No additional context available._"

    def _determine_inputs(self, role: str, context: Dict[str, Any]) -> List[str]:
        """Determine what inputs are available based on role and workflow position."""
        inputs = []

        if role == "pm":
            inputs.append("User request or problem statement")
            inputs.append("Existing documentation and related issues")
        elif role == "architect":
            inputs.append("Product Requirements Document (PRD)")
            if context.get("prd_path"):
                inputs.append(f"PRD at: {context['prd_path']}")
        elif role == "engineer":
            inputs.append("Technical Specification")
            if context.get("spec_path"):
                inputs.append(f"Spec at: {context['spec_path']}")
            inputs.append("Existing codebase patterns")
        elif role == "reviewer":
            inputs.append("Code changes to review")
            inputs.append("Technical Specification for validation")
            inputs.append("Test coverage report")
        elif role == "ux":
            inputs.append("Product Requirements Document (PRD)")
            inputs.append("User personas and goals")

        return inputs

    def _extract_constraints_from_prompt(self, raw_prompt: str) -> List[str]:
        """Extract any constraints mentioned in the raw prompt."""
        constraints = []

        # Look for constraint patterns
        constraint_patterns = [
            r"must\s+(.+?)(?:\.|$)",
            r"should\s+not\s+(.+?)(?:\.|$)",
            r"cannot\s+(.+?)(?:\.|$)",
            r"restricted\s+to\s+(.+?)(?:\.|$)",
            r"limited\s+to\s+(.+?)(?:\.|$)"
        ]

        prompt_lower = raw_prompt.lower()
        for pattern in constraint_patterns:
            matches = re.findall(pattern, prompt_lower, re.IGNORECASE)
            for match in matches[:2]:  # Limit to 2 per pattern
                constraints.append(match.strip().capitalize())

        return constraints

    def _build_success_criteria(
        self,
        raw_prompt: str,
        issue_type: str
    ) -> List[str]:
        """Build success criteria from prompt and issue type."""
        criteria = []

        # Type-specific criteria
        type_criteria = {
            "epic": [
                "All child features/stories are created and linked",
                "PRD document is complete and approved",
                "Success metrics are defined and measurable"
            ],
            "feature": [
                "Technical specification is complete",
                "All acceptance criteria from PRD are addressed",
                "Integration points are clearly defined"
            ],
            "story": [
                "All acceptance criteria are met",
                "Tests pass with >=80% coverage",
                "Code review is approved"
            ],
            "bug": [
                "Root cause is identified and documented",
                "Fix addresses the root cause",
                "Regression tests prevent recurrence"
            ],
            "spike": [
                "Research question is answered",
                "Findings are documented",
                "Recommendations are actionable"
            ]
        }

        criteria.extend(type_criteria.get(issue_type, type_criteria["story"]))

        # Extract acceptance criteria from prompt
        if "acceptance criteria" in raw_prompt.lower() or "- [ ]" in raw_prompt:
            criteria.append("All acceptance criteria from issue are satisfied")

        return criteria

    def validate_prompt_completeness(self, prompt: EnhancedPrompt) -> Dict[str, Any]:
        """
        Validate that an enhanced prompt has all required elements.

        Returns a validation report with missing or weak elements.
        """
        issues = []
        warnings = []

        # Required elements
        if not prompt.task_statement or len(prompt.task_statement) < 20:
            issues.append("Task statement is missing or too brief")

        if not prompt.outputs:
            issues.append("No expected outputs defined")

        if not prompt.success_criteria:
            issues.append("No success criteria defined")

        # Warnings for optional but recommended elements
        if not prompt.constraints:
            warnings.append("No constraints defined - consider adding boundaries")

        if prompt.next_role and not prompt.handoff_requirements:
            warnings.append(f"Handoff to {prompt.next_role} defined but no requirements specified")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "completeness_score": self._calculate_completeness_score(prompt)
        }

    def _calculate_completeness_score(self, prompt: EnhancedPrompt) -> float:
        """Calculate a completeness score from 0.0 to 1.0."""
        score = 0.0
        total_weight = 0.0

        # Weighted elements
        elements = [
            (bool(prompt.role_primer), 1.0),
            (bool(prompt.task_statement), 2.0),
            (bool(prompt.context_summary), 1.0),
            (len(prompt.inputs) > 0, 1.0),
            (len(prompt.outputs) > 0, 2.0),
            (len(prompt.constraints) > 0, 1.0),
            (len(prompt.success_criteria) > 0, 2.0),
            (len(prompt.quality_checklist) > 0, 1.0),
        ]

        for has_element, weight in elements:
            total_weight += weight
            if has_element:
                score += weight

        return score / total_weight if total_weight > 0 else 0.0
