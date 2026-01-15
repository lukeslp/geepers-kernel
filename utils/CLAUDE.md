# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module: utils

Common utilities for AI development including vision, embeddings, document parsing, async adapters, citation, progress tracking, and more.

### Overview

The utils module provides:
- **Vision** - Image analysis and processing
- **Embeddings** - Text embedding generation
- **Document Parsers** - PDF, DOCX, TXT parsing
- **Citations** - Academic citation formatting
- **Async Adapters** - Sync/async function conversion
- **Progress Tracking** - Progress bars and estimation
- **Time Utilities** - Timezone, formatting, scheduling
- **Text Processing** - Cleaning, tokenization, summarization
- **File Utilities** - File operations and management
- **Retry Logic** - Exponential backoff retry
- **Rate Limiting** - API rate limiting
- **Multi-Search** - Parallel searching across sources
- **Data Validation** - Schema validation
- **Execution** - Safe code execution
- **TTS** - Text-to-speech utilities
- **Crypto** - Encryption and hashing
- **Format Converter** - JSON/YAML/TOML/XML/CSV conversion

### Vision Utilities

Image analysis and processing:

```python
from utils.vision import (
    analyze_image_with_provider,
    encode_image_to_base64,
    resize_image,
    validate_image
)

# Analyze image with LLM vision
result = analyze_image_with_provider(
    image_path='/path/to/image.jpg',
    prompt='Describe this image in detail',
    provider='xai',  # or 'openai', 'anthropic', 'gemini'
    model='grok-vision-beta'
)
print(result.content)

# Encode image to base64
base64_str = encode_image_to_base64('/path/to/image.jpg')

# Resize image
resize_image(
    input_path='/path/to/large.jpg',
    output_path='/path/to/small.jpg',
    max_width=800,
    max_height=600
)

# Validate image
is_valid = validate_image('/path/to/image.jpg')
```

### Embeddings

Generate text embeddings:

```python
from utils.embeddings import (
    generate_embeddings,
    batch_generate_embeddings,
    cosine_similarity
)

# Single text embedding
embedding = generate_embeddings(
    text='This is a sample text',
    provider='openai',
    model='text-embedding-3-small'
)
# Returns: [0.123, -0.456, 0.789, ...]

# Batch embeddings
texts = ['Text 1', 'Text 2', 'Text 3']
embeddings = batch_generate_embeddings(
    texts=texts,
    provider='openai',
    batch_size=100
)

# Calculate similarity
similarity = cosine_similarity(embedding1, embedding2)
print(f"Similarity: {similarity:.4f}")
```

### Document Parsers

Parse various document formats:

```python
from utils.document_parsers import (
    parse_pdf,
    parse_docx,
    parse_text,
    extract_text_from_file
)

# Parse PDF
pdf_content = parse_pdf('/path/to/document.pdf')
print(pdf_content['text'])
print(pdf_content['metadata'])
print(pdf_content['page_count'])

# Parse DOCX
docx_content = parse_docx('/path/to/document.docx')

# Auto-detect and parse
content = extract_text_from_file('/path/to/document.pdf')  # Works with PDF, DOCX, TXT
```

### Citations

Format academic citations:

```python
from utils.citation import (
    format_citation,
    format_bibtex,
    format_apa,
    format_mla,
    parse_doi
)

# Format citation
paper = {
    'title': 'Paper Title',
    'authors': ['Author One', 'Author Two'],
    'year': 2024,
    'journal': 'Nature',
    'doi': '10.1000/xyz'
}

# APA format
apa = format_apa(paper)
# "Author One & Author Two. (2024). Paper Title. Nature. https://doi.org/10.1000/xyz"

# MLA format
mla = format_mla(paper)

# BibTeX format
bibtex = format_bibtex(paper)

# Parse DOI to get metadata
metadata = parse_doi('10.1000/xyz')
```

### Async Adapters

Convert between sync and async:

```python
from utils.async_adapter import (
    run_async_in_sync,
    run_sync_in_async,
    AsyncAdapter
)

# Run async function in sync context
async def async_function():
    await asyncio.sleep(1)
    return 'done'

result = run_async_in_sync(async_function())

# Run sync function in async context
def sync_function():
    time.sleep(1)
    return 'done'

result = await run_sync_in_async(sync_function)

# Adapter class
adapter = AsyncAdapter()
result = await adapter.run_in_executor(sync_function)
```

### Progress Tracking

Track and display progress:

```python
from utils.progress import (
    ProgressTracker,
    create_progress_bar,
    estimate_remaining_time
)

# Progress tracker
tracker = ProgressTracker(total=100)
for i in range(100):
    tracker.update(current=i+1)
    print(f"Progress: {tracker.percentage()}%")

# Progress bar
with create_progress_bar(total=100) as bar:
    for i in range(100):
        bar.update(1)

# Estimate remaining time
remaining = estimate_remaining_time(
    current=50,
    total=100,
    elapsed_seconds=60
)
print(f"~{remaining}s remaining")
```

### Time Utilities

Time formatting and timezone handling:

```python
from utils.time_utils import (
    format_timestamp,
    parse_timestamp,
    get_timezone_offset,
    schedule_task
)

# Format timestamp
formatted = format_timestamp(
    timestamp=1704067200,
    format='%Y-%m-%d %H:%M:%S',
    timezone='America/Los_Angeles'
)

# Parse timestamp
ts = parse_timestamp('2024-01-01 12:00:00')

# Get timezone offset
offset = get_timezone_offset('America/New_York')

# Schedule task
schedule_task(
    task=my_function,
    delay_seconds=60,
    repeat=True,
    interval=300
)
```

### Text Processing

Clean and process text:

```python
from utils.text_processing import (
    clean_text,
    tokenize,
    truncate_text,
    extract_keywords,
    summarize_text
)

# Clean text
cleaned = clean_text(
    text='   Some  messy\n\ntext  ',
    remove_extra_spaces=True,
    remove_newlines=True
)

# Tokenize
tokens = tokenize('This is a sentence.')
# ['This', 'is', 'a', 'sentence']

# Truncate
truncated = truncate_text('Long text...', max_length=100)

# Extract keywords
keywords = extract_keywords(text, top_n=10)

# Summarize (using LLM)
summary = summarize_text(
    text=long_article,
    max_length=200,
    provider='xai'
)
```

### File Utilities

File operations and management:

```python
from utils.file_utils import (
    ensure_directory,
    safe_file_write,
    get_file_hash,
    list_files_recursive
)

# Ensure directory exists
ensure_directory('/path/to/dir')

# Safe file write (atomic)
safe_file_write('/path/to/file.txt', 'content')

# Get file hash
hash_value = get_file_hash('/path/to/file.txt', algorithm='sha256')

# List files recursively
files = list_files_recursive('/path/to/dir', pattern='*.py')
```

### Retry Logic

Exponential backoff retry:

```python
from utils.retry_logic import (
    retry,
    retry_async,
    RetryConfig
)

# Decorator for sync functions
@retry(max_retries=3, base_delay=1.0, max_delay=10.0)
def unstable_function():
    # Might fail occasionally
    return api.fetch()

# Decorator for async functions
@retry_async(max_retries=5, base_delay=2.0)
async def unstable_async_function():
    return await api.fetch()

# Custom retry config
config = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2,
    jitter=True
)

@retry(config=config)
def my_function():
    pass
```

### Rate Limiting

API rate limiting:

```python
from utils.rate_limiter import RateLimiter

# Create rate limiter
limiter = RateLimiter(
    calls=100,      # 100 calls
    period=60       # per 60 seconds
)

# Use as context manager
with limiter:
    response = api.fetch()

# Or check manually
if limiter.can_proceed():
    response = api.fetch()
    limiter.record_call()
```

### Multi-Search

Search across multiple sources in parallel:

```python
from utils.multi_search import (
    parallel_search,
    SearchSource
)

# Define search sources
sources = [
    SearchSource(name='arxiv', search_fn=arxiv_search),
    SearchSource(name='github', search_fn=github_search),
    SearchSource(name='news', search_fn=news_search)
]

# Search all sources in parallel
results = parallel_search(
    query='machine learning',
    sources=sources,
    max_workers=3,
    timeout=30
)

for source_name, source_results in results.items():
    print(f"{source_name}: {len(source_results)} results")
```

### Data Validation

Schema validation:

```python
from utils.data_validation import (
    validate_schema,
    ValidationError
)

schema = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'age': {'type': 'integer', 'minimum': 0}
    },
    'required': ['name']
}

data = {'name': 'John', 'age': 30}

try:
    validate_schema(data, schema)
    print("Valid!")
except ValidationError as e:
    print(f"Invalid: {e}")
```

### Execution

Safe code execution:

```python
from utils.execution import (
    execute_safely,
    ExecutionResult
)

code = """
def add(a, b):
    return a + b

result = add(2, 3)
"""

result = execute_safely(
    code=code,
    timeout=5,
    allowed_imports=['math', 'json']
)

if result.success:
    print(result.output)
else:
    print(result.error)
```

### TTS Utilities

Text-to-speech helpers:

```python
from utils.tts import (
    text_to_speech,
    save_audio
)

# Generate speech
audio_data = text_to_speech(
    text='Hello, world!',
    provider='elevenlabs',
    voice='adam'
)

# Save to file
save_audio(audio_data, '/path/to/output.mp3')
```

### Crypto

Encryption and hashing:

```python
from utils.crypto import (
    hash_text,
    encrypt_text,
    decrypt_text
)

# Hash text
hashed = hash_text('password', algorithm='sha256')

# Encrypt
encrypted = encrypt_text('secret', key='encryption-key')

# Decrypt
decrypted = decrypt_text(encrypted, key='encryption-key')
```

### Format Converter

Convert between data formats:

```python
from utils.format_converter import (
    FormatConverter,
    json_to_yaml,
    json_to_xml,
    json_to_csv,
    yaml_to_json,
    csv_to_json
)

# Convert data between formats
data = {'name': 'Test', 'values': [1, 2, 3]}

# Using class method
result = FormatConverter.convert(data, target_format='yaml')
print(result.data)

result = FormatConverter.convert(data, target_format='xml')
print(result.data)

result = FormatConverter.convert(data, target_format='csv')
print(result.data)

# Convenience functions
yaml_str = json_to_yaml(data)
xml_str = json_to_xml(data)
csv_str = json_to_csv([{'a': 1}, {'a': 2}])

# Parse and convert
json_str = yaml_to_json('name: Test\nvalue: 42')
data = csv_to_json('a,b\n1,2\n3,4')

# Supported formats: json, yaml, toml, xml, csv
```

### Importing from Other Projects

```python
import sys
sys.path.insert(0, '/home/coolhand/shared')

from utils.vision import analyze_image_with_provider
from utils.embeddings import generate_embeddings
from utils.document_parsers import parse_pdf
from utils.citation import format_apa
from utils.retry_logic import retry_async
```

### Testing

```python
import pytest
from utils.text_processing import clean_text

def test_clean_text():
    result = clean_text('  messy   text  ')
    assert result == 'messy text'

@pytest.mark.asyncio
async def test_async_adapter():
    from utils.async_adapter import run_sync_in_async

    def sync_fn():
        return 'result'

    result = await run_sync_in_async(sync_fn)
    assert result == 'result'
```

### Files in This Module

- `vision.py` - Image analysis and processing
- `embeddings.py` - Text embedding generation
- `document_parsers.py` - PDF/DOCX/TXT parsing
- `citation.py` - Academic citation formatting
- `async_adapter.py` - Sync/async conversion
- `progress.py` - Progress tracking and bars
- `time_utils.py` - Time formatting and timezones
- `text_processing.py` - Text cleaning and processing
- `file_utils.py` - File operations
- `retry_logic.py` - Exponential backoff retry
- `rate_limiter.py` - API rate limiting
- `multi_search.py` - Parallel search
- `data_validation.py` - Schema validation
- `execution.py` - Safe code execution
- `tts.py` - Text-to-speech
- `crypto.py` - Encryption and hashing
- `format_converter.py` - Data format conversion (JSON/YAML/TOML/XML/CSV)

### Dependencies

Core: Standard library

Optional:
- `Pillow` - Image processing
- `PyPDF2` or `pdfplumber` - PDF parsing
- `python-docx` - DOCX parsing
- `openai`, `anthropic` - For embeddings and vision
- `cryptography` - Encryption

### Best Practices

- Use async adapters for I/O-heavy operations
- Enable retry logic for unreliable APIs
- Validate data before processing
- Use progress tracking for long operations
- Cache embeddings to save costs
- Handle file operations safely
- Apply rate limiting to external APIs
- Sanitize text input before processing
- Use proper exception handling
- Log utility operations for debugging

### Common Patterns

#### Image Analysis with Retry
```python
from utils.vision import analyze_image_with_provider
from utils.retry_logic import retry_async

@retry_async(max_retries=3)
async def analyze_with_retry(image_path, prompt):
    return analyze_image_with_provider(
        image_path=image_path,
        prompt=prompt,
        provider='xai'
    )
```

#### Batch Processing with Progress
```python
from utils.progress import ProgressTracker

tracker = ProgressTracker(total=len(items))
for i, item in enumerate(items):
    process(item)
    tracker.update(current=i+1)
    print(f"{tracker.percentage()}% complete")
```

#### Rate-Limited API Calls
```python
from utils.rate_limiter import RateLimiter

limiter = RateLimiter(calls=60, period=60)

for query in queries:
    with limiter:
        result = api.search(query)
```
