#!/bin/bash
# Alignment Validation Script
# Validates alignment between PRD → Spec → Code
# Checks that acceptance criteria map to spec requirements and implementation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ISSUE_NUM="$1"

if [ -z "$ISSUE_NUM" ]; then
  echo -e "${RED}❌ Usage: $0 <issue-number>${NC}"
  exit 1
fi

echo "========================================="
echo "  Alignment Validation - Issue #${ISSUE_NUM}"
echo "========================================="
echo ""

VALIDATION_PASSED=true
WARNINGS=()

# Check if PRD exists
PRD_FILE="docs/prd/PRD-${ISSUE_NUM}.md"
SPEC_FILE="docs/specs/SPEC-${ISSUE_NUM}.md"
ADR_FILE="docs/adr/ADR-${ISSUE_NUM}.md"

echo -e "${BLUE}[1/4] Checking Documents Exist${NC}"
echo ""

if [ -f "$PRD_FILE" ]; then
  echo -e "${GREEN}✓${NC} PRD exists: $PRD_FILE"
  HAS_PRD=true
else
  echo -e "${YELLOW}⚠${NC}  PRD not found: $PRD_FILE"
  HAS_PRD=false
fi

if [ -f "$SPEC_FILE" ]; then
  echo -e "${GREEN}✓${NC} Spec exists: $SPEC_FILE"
  HAS_SPEC=true
else
  echo -e "${YELLOW}⚠${NC}  Spec not found: $SPEC_FILE"
  HAS_SPEC=false
fi

if [ -f "$ADR_FILE" ]; then
  echo -e "${GREEN}✓${NC} ADR exists: $ADR_FILE"
  HAS_ADR=true
else
  echo -e "${YELLOW}⚠${NC}  ADR not found (optional): $ADR_FILE"
  HAS_ADR=false
fi

echo ""

# If neither PRD nor Spec exists, can't validate alignment
if [ "$HAS_PRD" = false ] && [ "$HAS_SPEC" = false ]; then
  echo -e "${YELLOW}⚠${NC}  No PRD or Spec found - skipping alignment validation"
  exit 0
fi

# Extract acceptance criteria from PRD
echo -e "${BLUE}[2/4] Extracting Acceptance Criteria${NC}"
echo ""

if [ "$HAS_PRD" = true ]; then
  # Extract acceptance criteria (look for checklist items)
  AC_ITEMS=$(grep -E "^\s*-\s*\[[ x]\]" "$PRD_FILE" | sed 's/^\s*-\s*\[[ x]\]\s*//' || echo "")
  AC_COUNT=$(echo "$AC_ITEMS" | grep -v "^$" | wc -l)
  
  echo "Found $AC_COUNT acceptance criteria in PRD"
  
  if [ $AC_COUNT -eq 0 ]; then
    echo -e "${YELLOW}⚠${NC}  Warning: No acceptance criteria found in PRD"
    WARNINGS+=("No acceptance criteria in PRD")
  fi
else
  AC_COUNT=0
fi

echo ""

# Check Spec requirements match PRD criteria
echo -e "${BLUE}[3/4] Checking PRD → Spec Alignment${NC}"
echo ""

if [ "$HAS_PRD" = true ] && [ "$HAS_SPEC" = true ]; then
  # Extract requirement sections from spec
  SPEC_SECTIONS=$(grep -E "^##\s+" "$SPEC_FILE" | sed 's/^##\s*//' || echo "")
  
  # Check if spec has requirements section
  if grep -qi "requirements\|functional requirements" "$SPEC_FILE"; then
    echo -e "${GREEN}✓${NC} Spec has Requirements section"
  else
    echo -e "${YELLOW}⚠${NC}  Warning: Spec missing Requirements section"
    WARNINGS+=("Spec missing Requirements section")
  fi
  
  # Simple heuristic: check if key terms from PRD appear in Spec
  # Extract key terms from AC items (nouns/verbs)
  if [ $AC_COUNT -gt 0 ]; then
    ALIGNMENT_ISSUES=0
    
    while IFS= read -r ac_item; do
      # Extract key words (simple heuristic: words >4 chars)
      KEY_WORDS=$(echo "$ac_item" | tr ' ' '\n' | awk 'length($0)>4' | head -3)
      
      FOUND_IN_SPEC=false
      for word in $KEY_WORDS; do
        if grep -qi "$word" "$SPEC_FILE"; then
          FOUND_IN_SPEC=true
          break
        fi
      done
      
      if [ "$FOUND_IN_SPEC" = false ]; then
        ALIGNMENT_ISSUES=$((ALIGNMENT_ISSUES + 1))
        echo -e "${YELLOW}⚠${NC}  Potential gap: '$(echo $ac_item | cut -c1-60)...'"
      fi
    done <<< "$AC_ITEMS"
    
    if [ $ALIGNMENT_ISSUES -eq 0 ]; then
      echo -e "${GREEN}✓${NC} All AC items referenced in Spec"
    else
      echo -e "${YELLOW}⚠${NC}  $ALIGNMENT_ISSUES potential alignment gaps found"
      WARNINGS+=("$ALIGNMENT_ISSUES PRD → Spec alignment gaps")
    fi
  fi
elif [ "$HAS_PRD" = true ]; then
  echo -e "${YELLOW}⚠${NC}  Cannot validate: Spec not found"
fi

echo ""

# Check Spec → Code alignment (basic check for implementation)
echo -e "${BLUE}[4/4] Checking Spec → Code Alignment${NC}"
echo ""

if [ "$HAS_SPEC" = true ]; then
  # Check if code files referenced in spec exist
  CODE_REFS=$(grep -oE "src/[a-zA-Z0-9_/.-]+(\.py|\.cs|\.ts|\.js)" "$SPEC_FILE" | sort -u || echo "")
  
  if [ -n "$CODE_REFS" ]; then
    MISSING_FILES=0
    while IFS= read -r file; do
      if [ ! -f "$file" ]; then
        echo -e "${YELLOW}⚠${NC}  Referenced file not found: $file"
        MISSING_FILES=$((MISSING_FILES + 1))
      fi
    done <<< "$CODE_REFS"
    
    if [ $MISSING_FILES -eq 0 ]; then
      echo -e "${GREEN}✓${NC} All referenced code files exist"
    else
      echo -e "${YELLOW}⚠${NC}  $MISSING_FILES referenced files not found"
      WARNINGS+=("$MISSING_FILES code files missing")
    fi
  else
    echo -e "${YELLOW}⚠${NC}  No code file references found in Spec"
  fi
fi

echo ""
echo "========================================="

if [ ${#WARNINGS[@]} -eq 0 ]; then
  echo -e "${GREEN}✓ ALIGNMENT VALIDATION PASSED${NC}"
  echo "No critical alignment gaps detected."
  echo "========================================="
  exit 0
else
  echo -e "${YELLOW}⚠ ALIGNMENT WARNINGS${NC}"
  echo ""
  for warning in "${WARNINGS[@]}"; do
    echo "  • $warning"
  done
  echo ""
  echo "Review alignment between documents."
  echo "Non-critical warnings - handoff can proceed."
  echo "========================================="
  exit 0  # Warnings don't block handoff
fi
