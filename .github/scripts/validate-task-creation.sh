#!/bin/bash
# Task Creation Validation Script
# Validates that tasks meet "standalone task principle" before creation
# Enforces: references field, documentation field, dependency explanations

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ISSUE_BODY_FILE="$1"

if [ -z "$ISSUE_BODY_FILE" ]; then
  echo -e "${RED}[X] Usage: $0 <issue-body-file>${NC}"
  exit 1
fi

if [ ! -f "$ISSUE_BODY_FILE" ]; then
  echo -e "${RED}[X] Issue body file not found: $ISSUE_BODY_FILE${NC}"
  exit 1
fi

echo "========================================="
echo "  Task Creation Validation"
echo "========================================="
echo ""

VALIDATION_PASSED=true

# Extract issue body
BODY=$(cat "$ISSUE_BODY_FILE")

# Check 1: Has description (non-empty)
echo -n "Checking description... "
if [ ${#BODY} -lt 50 ]; then
  echo -e "${RED}[FAIL]${NC} Description too short (min 50 chars)"
  VALIDATION_PASSED=false
else
  echo -e "${GREEN}[OK]${NC}"
fi

# Check 2: Has References section (for code tasks)
echo -n "Checking References section... "
if echo "$BODY" | grep -qi "## References"; then
  echo -e "${GREEN}[OK]${NC}"
  
  # Validate references have file paths
  if ! echo "$BODY" | grep -q "src/\|docs/\|tests/"; then
    echo -e "${YELLOW}[WARN]${NC}  Warning: References section exists but no file paths found"
  fi
else
  # References optional for docs/spike tasks
  if echo "$BODY" | grep -qiE "type:docs|type:spike"; then
    echo -e "${GREEN}[OK]${NC} (optional for docs/spike)"
  else
    echo -e "${RED}[FAIL]${NC} Missing References section (required for code tasks)"
    VALIDATION_PASSED=false
  fi
fi

# Check 3: Has Documentation section
echo -n "Checking Documentation section... "
if echo "$BODY" | grep -qi "## Documentation"; then
  echo -e "${GREEN}[OK]${NC}"
else
  echo -e "${YELLOW}[WARN]${NC}  Warning: Missing Documentation section (recommended)"
fi

# Check 4: Has Acceptance Criteria
echo -n "Checking Acceptance Criteria... "
if echo "$BODY" | grep -qi "Acceptance Criteria\|## AC\|## Criteria"; then
  echo -e "${GREEN}[OK]${NC}"
  
  # Count criteria
  CRITERIA_COUNT=$(echo "$BODY" | grep -c "^\s*[-*] \[[ x]\]" || echo "0")
  if [ "$CRITERIA_COUNT" -lt 2 ]; then
    echo -e "${YELLOW}[WARN]${NC}  Warning: Only $CRITERIA_COUNT acceptance criteria found (min 2 recommended)"
  fi
else
  echo -e "${RED}[FAIL]${NC} Missing Acceptance Criteria"
  VALIDATION_PASSED=false
fi

# Check 5: Dependencies have explanations
echo -n "Checking Dependencies... "
if echo "$BODY" | grep -qi "## Dependencies"; then
  # Check for structured dependency format
  if echo "$BODY" | grep -qiE "Provides:|Integration Point:|Verification:"; then
    echo -e "${GREEN}[OK]${NC}"
  else
    echo -e "${YELLOW}[WARN]${NC}  Warning: Dependencies exist but lack structured format"
    echo "     Expected: Provides, Integration Point, Verification fields"
  fi
else
  echo -e "${GREEN}[OK]${NC} (no dependencies)"
fi

# Check 6: Stranger Test - avoid implicit knowledge
echo -n "Running Stranger Test... "
IMPLICIT_PHRASES=(
  "like we discussed"
  "as mentioned"
  "as usual"
  "you know"
  "obviously"
  "just like before"
)

FOUND_IMPLICIT=false
for phrase in "${IMPLICIT_PHRASES[@]}"; do
  if echo "$BODY" | grep -qi "$phrase"; then
    echo -e "${RED}[FAIL]${NC}"
    echo -e "${YELLOW}[WARN]${NC}  Found implicit phrase: '$phrase'"
    echo "     Task assumes shared context - violates stranger test"
    FOUND_IMPLICIT=true
    VALIDATION_PASSED=false
    break
  fi
done

if [ "$FOUND_IMPLICIT" = false ]; then
  echo -e "${GREEN}[OK]${NC}"
fi

# Check 7: Has clear title format
echo ""
echo "========================================="
if [ "$VALIDATION_PASSED" = true ]; then
  echo -e "${GREEN}[OK] VALIDATION PASSED${NC}"
  echo "Task meets standalone task principle."
  echo "========================================="
  exit 0
else
  echo -e "${RED}[FAIL] VALIDATION FAILED${NC}"
  echo "Fix the issues above before creating task."
  echo ""
  echo "Standalone Task Principle:"
  echo "  • Complete context for independent execution"
  echo "  • References to code files"
  echo "  • Documentation links"
  echo "  • Dependency explanations (what/how/verify)"
  echo "  • No implicit knowledge"
  echo "========================================="
  exit 1
fi
