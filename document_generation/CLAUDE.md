# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module: document_generation

Comprehensive document generation capabilities for PDF, DOCX, and Markdown formats. Provides both individual generators and a unified manager for multi-format output.

### Overview

Generate professional documents from structured content:
- **PDF** - via ReportLab (optional dependency)
- **DOCX** - via python-docx (optional dependency)
- **Markdown** - built-in, always available

### Quick Start

```python
from document_generation import generate_multi_format_reports

content = [
    {
        "title": "Introduction",
        "content": "This report covers the key findings..."
    },
    {
        "title": "Analysis",
        "content": "## Key Findings\n- Finding 1\n- Finding 2"
    },
    {
        "title": "Conclusion",
        "content": "Based on the analysis..."
    }
]

result = generate_multi_format_reports(
    content_sections=content,
    title="Research Report",
    document_id="report_2024_01",
    formats=["pdf", "docx", "markdown"],
    output_dir="/output/reports"
)

print(f"Generated: {result['files']}")
# Output: {'pdf': '/output/reports/report_2024_01.pdf',
#          'docx': '/output/reports/report_2024_01.docx',
#          'markdown': '/output/reports/report_2024_01.md'}
```

### Individual Generators

#### PDFGenerator

```python
from document_generation import PDFGenerator

generator = PDFGenerator(output_dir="/output/pdf")

result = generator.generate_report_pdf(
    content_sections=content,
    title="My Report",
    subtitle="Q4 2024 Analysis",
    author="Luke Steuber",
    document_id="report_001",
    metadata={
        "department": "Research",
        "confidential": False
    }
)

print(result)
# Output: {
#   'success': True,
#   'file_path': '/output/pdf/report_001.pdf',
#   'format': 'pdf',
#   'file_size': 45678
# }
```

**PDF Features:**
- Custom styling and fonts
- Headers and footers
- Page numbers
- Table of contents
- Images and tables
- Hyperlinks

#### DOCXGenerator

```python
from document_generation import DOCXGenerator

generator = DOCXGenerator(output_dir="/output/docx")

result = generator.generate_report_docx(
    content_sections=content,
    title="My Report",
    subtitle="Quarterly Review",
    author="Luke Steuber",
    document_id="report_001",
    metadata={"version": "1.0"}
)
```

**DOCX Features:**
- Heading styles (Heading 1, 2, 3)
- Bullet and numbered lists
- Tables
- Images
- Bold, italic, underline
- Page breaks

#### MarkdownGenerator

```python
from document_generation import MarkdownGenerator

generator = MarkdownGenerator(output_dir="/output/markdown")

result = generator.generate_report_markdown(
    content_sections=content,
    title="My Report",
    subtitle="Analysis Report",
    author="Luke Steuber",
    document_id="report_001",
    include_toc=True,
    metadata={"date": "2024-01-01"}
)
```

**Markdown Features:**
- Full Markdown syntax
- Table of contents
- Code blocks
- Tables
- Images
- Links

### Document Manager

Unified interface for multi-format generation:

```python
from document_generation import DocumentGenerationManager

manager = DocumentGenerationManager(output_dir="/output/all")

# Generate all formats at once
result = manager.generate_all_formats(
    content_sections=content,
    title="Comprehensive Report",
    document_id="report_multi",
    author="Luke Steuber",
    formats=["pdf", "docx", "markdown"]  # Specify which formats
)

print(result)
# Output: {
#   'success': True,
#   'files': {
#       'pdf': '/output/all/report_multi.pdf',
#       'docx': '/output/all/report_multi.docx',
#       'markdown': '/output/all/report_multi.md'
#   },
#   'errors': []  # Any format-specific errors
# }
```

### Content Structure

Content sections should be dicts with:

```python
section = {
    "title": "Section Title",        # Required
    "content": "Section content...",  # Required (supports Markdown)
    "level": 1,                       # Optional: heading level (1-3)
    "metadata": {}                    # Optional: section-specific metadata
}
```

**Markdown in Content:**
```python
section = {
    "title": "Findings",
    "content": """
## Key Results

- **Result 1**: Important finding
- **Result 2**: Another discovery

### Details

This section provides [detailed analysis](https://example.com).

| Metric | Value |
|--------|-------|
| Speed  | 95%   |
| Accuracy | 98% |
"""
}
```

### Convenience Functions

```python
from document_generation import (
    generate_pdf_report,
    generate_docx_report,
    generate_markdown_report
)

# Quick PDF generation
pdf_result = generate_pdf_report(
    content_sections=content,
    title="Quick PDF",
    output_dir="/output"
)

# Quick DOCX generation
docx_result = generate_docx_report(
    content_sections=content,
    title="Quick DOCX",
    output_dir="/output"
)

# Quick Markdown generation
md_result = generate_markdown_report(
    content_sections=content,
    title="Quick Markdown",
    output_dir="/output"
)
```

### Checking Available Formats

```python
from document_generation import get_available_formats, check_dependencies

# Check what's available
formats = get_available_formats()
print(f"Available: {formats}")
# Output: ['markdown', 'pdf', 'docx']  (if all deps installed)

# Check dependencies
deps = check_dependencies()
for format_name, info in deps.items():
    if info['available']:
        print(f"{format_name}: ✓ Available")
    else:
        print(f"{format_name}: ✗ Missing - {info['install']}")
```

### Dependency Status

```python
from document_generation import print_dependency_status

print_dependency_status()
# Output:
# Document Generation Dependencies:
# --------------------------------------------------
# MARKDOWN   ✓ Available          (built-in)
# PDF        ✓ Available          (reportlab)
# DOCX       ✓ Available          (python-docx)
# --------------------------------------------------
# Available formats: markdown, pdf, docx
```

### Installation

```bash
# Core (Markdown only)
pip install dr-eamer-ai-shared

# With PDF support
pip install dr-eamer-ai-shared[pdf]
# Or: pip install reportlab

# With DOCX support
pip install dr-eamer-ai-shared[docx]
# Or: pip install python-docx

# All formats
pip install dr-eamer-ai-shared[all]
# Or: pip install reportlab python-docx
```

### Advanced Usage

#### Custom Styling (PDF)

```python
from document_generation import PDFGenerator

generator = PDFGenerator(output_dir="/output")

# Custom page size and margins
result = generator.generate_report_pdf(
    content_sections=content,
    title="Custom PDF",
    page_size="A4",           # or "LETTER"
    margin_left=72,           # Points (1 inch = 72 points)
    margin_right=72,
    margin_top=72,
    margin_bottom=72,
    font_name="Helvetica",
    font_size=12
)
```

#### Including Images

```python
section_with_image = {
    "title": "Visual Analysis",
    "content": """
Here's the chart:

![Chart](./charts/analysis.png)

And the graph:

![Graph](./graphs/trends.png)
"""
}
```

#### Table Generation

```python
section_with_table = {
    "title": "Results Table",
    "content": """
| Model | Accuracy | Speed |
|-------|----------|-------|
| GPT-4 | 95%      | 2.5s  |
| Grok  | 96%      | 1.8s  |
| Claude| 94%      | 2.1s  |
"""
}
```

### Integration with Orchestrators

```python
from orchestration import DreamCascadeOrchestrator, DreamCascadeConfig
from document_generation import generate_multi_format_reports

# Run orchestration
orchestrator = DreamCascadeOrchestrator(config, provider)
result = await orchestrator.execute_workflow("Research quantum computing")

# Generate reports from results
content = [
    {
        "title": "Executive Summary",
        "content": result.result.get('summary', '')
    },
    {
        "title": "Detailed Findings",
        "content": "\n\n".join([
            f"## Agent {i+1}\n{r.content}"
            for i, r in enumerate(result.agent_results)
        ])
    }
]

reports = generate_multi_format_reports(
    content_sections=content,
    title="Quantum Computing Research",
    document_id=f"research_{result.task_id}",
    formats=["pdf", "markdown"]
)
```

### Error Handling

```python
from document_generation import generate_multi_format_reports

try:
    result = generate_multi_format_reports(
        content_sections=content,
        title="My Report",
        formats=["pdf", "docx", "markdown"]
    )

    if result['success']:
        print(f"Generated: {list(result['files'].keys())}")

    if result['errors']:
        print(f"Errors: {result['errors']}")

except Exception as e:
    print(f"Generation failed: {e}")
```

### Testing

```python
import pytest
from document_generation import MarkdownGenerator

def test_markdown_generation():
    generator = MarkdownGenerator(output_dir="/tmp/test")

    content = [
        {"title": "Test", "content": "Test content"}
    ]

    result = generator.generate_report_markdown(
        content_sections=content,
        title="Test Report",
        document_id="test_001"
    )

    assert result['success'] is True
    assert 'file_path' in result
    assert result['format'] == 'markdown'
```

### Files in This Module

- `pdf_generator.py` - PDF generation via ReportLab
- `docx_generator.py` - DOCX generation via python-docx
- `markdown_generator.py` - Markdown generation (built-in)
- `manager.py` - Unified document generation manager
- `__init__.py` - Package exports and utilities

### Constants

```python
from document_generation import PDF_AVAILABLE, DOCX_AVAILABLE

if PDF_AVAILABLE:
    # Use PDF features
    pass

if DOCX_AVAILABLE:
    # Use DOCX features
    pass
```

### Best Practices

- Always check `get_available_formats()` before generating
- Use Markdown as fallback (always available)
- Validate content structure before generation
- Use meaningful document IDs for tracking
- Include metadata for document management
- Handle missing dependencies gracefully
- Test with sample content before production
- Use appropriate output directories
- Clean up old documents periodically

### Common Patterns

#### Report from Agent Results
```python
def create_report_from_agents(agent_results, title):
    content = []
    for i, result in enumerate(agent_results):
        content.append({
            "title": f"Agent {i+1}: {result.subtask_id}",
            "content": result.content
        })

    return generate_multi_format_reports(
        content_sections=content,
        title=title,
        formats=["pdf", "markdown"]
    )
```

#### Batch Document Generation
```python
def generate_batch_reports(reports_data):
    results = []
    for report in reports_data:
        result = generate_multi_format_reports(
            content_sections=report['content'],
            title=report['title'],
            document_id=report['id'],
            formats=["markdown"]
        )
        results.append(result)
    return results
```
