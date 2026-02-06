# Document Export Feature

## Overview

The export feature allows you to convert Context.md markdown deliverables (PRD, ADR, Specs, Reviews, UX designs) into professional DOCX and PDF formats for stakeholder distribution.

## Installation

### Install Export Dependencies

```bash
# Core dependencies (required)
pip install python-docx markdown-it-py markdown

# Optional: For DOCX to PDF conversion
# Windows (requires Microsoft Word)
pip install docx2pdf

# Linux/macOS (requires LibreOffice)
sudo apt-get install libreoffice  # Ubuntu/Debian
brew install --cask libreoffice    # macOS

# Optional: For MD to PDF (cross-platform)
# Install pandoc: https://pandoc.org/installing.html
```

## Usage

### Export Single Document

```bash
# Export to DOCX
context-md export document docs/prd/PRD-123.md --format docx

# Export to PDF
context-md export document docs/adr/ADR-456.md --format pdf

# Export to both formats
context-md export document docs/specs/SPEC-789.md --format both

# Custom output directory
context-md export document docs/prd/PRD-123.md --format docx --output ./deliverables/
```

### Export All Issue Deliverables

```bash
# Export all documents for an issue
context-md export issue 123 --format both

# Custom output directory
context-md export issue 123 --format pdf --output ./exports/issue-123/
```

This will find and export:
- `docs/prd/PRD-123*.md`
- `docs/adr/ADR-123*.md`
- `docs/specs/SPEC-123*.md`
- `docs/ux/UX-123*.md`
- `docs/reviews/REVIEW-123*.md`

## Output

Exported documents are saved with the same base name:

```
deliverables/
├── PRD-123-User-Authentication.docx
├── PRD-123-User-Authentication.pdf
├── ADR-123-JWT-Implementation.docx
├── ADR-123-JWT-Implementation.pdf
├── SPEC-123-Auth-Service.docx
└── SPEC-123-Auth-Service.pdf
```

## Features

### DOCX Export
- ✅ Preserves markdown structure (headings, lists, tables, code blocks)
- ✅ Professional formatting (fonts, colors, spacing)
- ✅ Table of contents generation
- ✅ Code block syntax highlighting
- ✅ Customizable templates (future)

### PDF Export
- ✅ Professional styling with CSS
- ✅ Page numbering and headers/footers
- ✅ Syntax highlighting for code blocks
- ✅ Hyperlink preservation
- ✅ Cross-platform support

## Architecture

```
Export Command
    ├── markdown-it-py      # Parse markdown structure
    ├── python-docx         # Generate DOCX files directly
    └── pandoc              # Generate PDF from markdown (optional)
```

## Conversion Methods

### Markdown → DOCX
1. Parse markdown using `markdown-it-py`
2. Generate Word document using `python-docx` directly
3. Apply formatting (fonts, styles, colors, tables)
4. Save `.docx` file

### Markdown → PDF
1. Convert markdown to PDF using `pandoc` (requires separate installation)
2. Pandoc handles styling and formatting
3. Save `.pdf` file

**Note**: Recommended to export as DOCX and convert to PDF using platform tools.

### DOCX → PDF (Windows)
- Uses `docx2pdf` (requires Microsoft Word)

### DOCX → PDF (Linux/macOS)
- Uses LibreOffice headless mode (`soffice`)

## Examples

### Export PRD for Stakeholder Review
```bash
context-md export document docs/prd/PRD-123-User-Auth.md --format pdf --output ./stakeholder-review/
```

### Export All Deliverables for Client Handoff
```bash
context-md export issue 456 --format both --output ./client-delivery/release-1.0/
```

### Batch Export All PRDs
```bash
for file in docs/prd/*.md; do
    context-md export document "$file" --format docx --output ./prd-library/
done
```

## Troubleshooting

### "PDF conversion requires pandoc"
```bash
# Install pandoc for MD→PDF conversion
# Visit: https://pandoc.org/installing.html

# Ubuntu/Debian
sudo apt-get install pandoc

# macOS
brew install pandoc

# Windows
winget install --id JohnMacFarlane.Pandoc
```

### "PDF conversion requires LibreOffice"
```bash
# Ubuntu/Debian
sudo apt-get install libreoffice

# macOS
brew install --cask libreoffice

# Arch Linux
sudo pacman -S libreoffice-fresh
```

### "docx2pdf requires Microsoft Word"
On Windows, `docx2pdf` requires Microsoft Word to be installed. If you don't have Word, use LibreOffice instead:
1. Install LibreOffice
2. The export command will automatically fall back to LibreOffice

## Configuration

Future enhancements will support:
- Custom DOCX templates (`.github/templates/export/`)
- Company branding (logos, colors, fonts)
- Variable substitution (`${issue_number}`, `${date}`, `${author}`)
- Export presets (client, internal, archival)

## Related Issues

- [Issue #3: Document Export Feature](https://github.com/jnPiyush/ContextMD/issues/3)

## Testing

```bash
# Run export tests
pytest tests/test_export.py -v

# Test with real documents
context-md export document docs/prd/PRD-CONTEXT-MD.md --format both --output ./test-exports/
```
