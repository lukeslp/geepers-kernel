# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Module: data_fetching

Structured API clients for 17 external data sources. Provides consistent interfaces for retrieving data from academic, government, news, and web APIs.

### Available Clients

- **ArxivClient** - Academic papers from arXiv.org
- **SemanticScholarClient** - Research papers with citations
- **PubMedClient** - Biomedical/medical literature from NCBI
- **ArchiveClient** - Internet Archive / Wayback Machine
- **CensusClient** - US Census Bureau data
- **FECClient** - Federal Election Commission campaign finance
- **JudiciaryClient** - Court records and judicial data
- **GitHubClient** - Repository and user data
- **NASAClient** - NASA imagery and space data
- **NewsClient** - News articles from various sources
- **WikipediaClient** - Wikipedia article content
- **WeatherClient** - Weather data and forecasts
- **OpenLibraryClient** - Book metadata and availability
- **YouTubeClient** - Video metadata and transcripts
- **FinanceClient** - Stock and financial data
- **MALClient** - MyAnimeList anime/manga data
- **WolframAlphaClient** - Computational knowledge queries
- **MultiArchiveClient** - Multi-provider archive access (Wayback, Archive.is, Memento, 12ft)

### Factory Pattern

```python
from data_fetching import ClientFactory

# Create client by name
client = ClientFactory.create_client('arxiv')
results = client.search(query='quantum computing')

# List available clients
available = ClientFactory.list_clients()
# Returns: ['arxiv', 'census', 'github', 'nasa', ...]
```

### Usage Examples

#### ArxivClient - Academic Papers

```python
from data_fetching import ArxivClient, search_arxiv, get_paper_by_id

# Method 1: Direct client
client = ArxivClient()
papers = client.search(
    query='machine learning',
    max_results=10,
    sort_by='relevance',
    sort_order='descending'
)

for paper in papers:
    print(f"{paper.title} - {paper.authors}")
    print(f"Published: {paper.published}")
    print(f"PDF: {paper.pdf_url}")

# Method 2: Convenience functions
papers = search_arxiv('quantum computing', max_results=5)
paper = get_paper_by_id('2103.12345')
```

#### SemanticScholarClient - Research Papers

```python
from data_fetching import SemanticScholarClient, search_papers, get_paper_by_doi

client = SemanticScholarClient()
papers = client.search(
    query='neural networks',
    limit=10,
    fields=['title', 'authors', 'year', 'citations']
)

# Get by DOI
paper = get_paper_by_doi('10.1000/xyz123')
print(f"Citations: {paper.citation_count}")
```

#### PubMedClient - Medical Literature

```python
from data_fetching import PubMedClient, search_pubmed, get_article_by_pmid

client = PubMedClient()

# Basic search
articles = client.search(
    query='COVID-19 treatment',
    max_results=10,
    sort_by='relevance'
)

for article in articles:
    print(f"{article.title} - {article.journal}")
    print(f"Authors: {', '.join(article.authors)}")
    print(f"PMID: {article.pmid}")
    print(f"URL: {article.url}")

# Search by MeSH term
diabetes_articles = client.search_by_mesh('Diabetes Mellitus', max_results=10)

# Search clinical trials only
trials = client.search_clinical_trials('hypertension', max_results=10)

# Search review articles only
reviews = client.search_reviews('cancer immunotherapy', max_results=10)

# Search by author
author_articles = client.search_by_author('Fauci AS', max_results=10)

# Get article by PMID
article = client.get_by_id('12345678')

# Convenience functions (return dicts)
results = search_pubmed('heart disease', max_results=5)
article_dict = get_article_by_pmid('12345678')
```

#### ArchiveClient - Wayback Machine

```python
from data_fetching import ArchiveClient, archive_url, get_latest_archive

client = ArchiveClient()

# Save URL to archive
snapshot = client.save_page('https://example.com')
print(f"Archived at: {snapshot.archive_url}")

# Get snapshots
snapshots = client.get_snapshots(
    url='https://example.com',
    from_date='2020-01-01',
    to_date='2024-01-01'
)

# Convenience functions
archive_url('https://example.com')
latest = get_latest_archive('https://example.com')
```

#### CensusClient - US Census Data

```python
from data_fetching import CensusClient

client = CensusClient(api_key='your-key')

# Get population data
data = client.get_population(
    year=2020,
    geography='state',
    state='CA'
)

# Economic data
econ = client.get_economic_data(
    dataset='acs/acs5',
    year=2020,
    variables=['B01001_001E'],  # Total population
    geography='county:*',
    state='CA'
)
```

#### GitHubClient - Repository Data

```python
from data_fetching import GitHubClient

client = GitHubClient(token='github-token')

# Search repositories
repos = client.search_repositories(
    query='machine learning',
    language='python',
    sort='stars'
)

# Get repo details
repo = client.get_repository('owner/repo')
print(f"Stars: {repo['stargazers_count']}")

# Get user info
user = client.get_user('username')
```

#### WikipediaClient - Article Content

```python
from data_fetching import WikipediaClient

client = WikipediaClient()

# Search articles
results = client.search('quantum computing')

# Get article content
article = client.get_article('Quantum_computing')
print(article['content'])
print(article['summary'])

# Get article in different language
article_es = client.get_article('Computación_cuántica', lang='es')
```

#### NewsClient - News Articles

```python
from data_fetching import NewsClient

client = NewsClient(api_key='news-api-key')

# Top headlines
headlines = client.get_top_headlines(
    category='technology',
    country='us'
)

# Search articles
articles = client.search(
    query='artificial intelligence',
    from_date='2024-01-01',
    language='en',
    sort_by='relevance'
)

for article in articles:
    print(f"{article['title']} - {article['source']}")
```

#### WeatherClient - Weather Data

```python
from data_fetching import WeatherClient

client = WeatherClient(api_key='weather-key')

# Current weather
weather = client.get_current_weather(
    city='San Francisco',
    country='US'
)

# Forecast
forecast = client.get_forecast(
    lat=37.7749,
    lon=-122.4194,
    days=7
)
```

#### NASAClient - Space Imagery

```python
from data_fetching import NASAClient

client = NASAClient(api_key='nasa-key')

# Astronomy Picture of the Day
apod = client.get_apod(date='2024-01-01')
print(apod['explanation'])
print(apod['url'])

# Mars rover photos
photos = client.get_mars_photos(
    rover='curiosity',
    sol=1000,
    camera='FHAZ'
)

# Near Earth Objects
neos = client.get_near_earth_objects(
    start_date='2024-01-01',
    end_date='2024-01-07'
)
```

#### YouTubeClient - Video Data

```python
from data_fetching import YouTubeClient

client = YouTubeClient(api_key='youtube-key')

# Search videos
videos = client.search(
    query='python tutorial',
    max_results=10,
    order='relevance'
)

# Get video details
video = client.get_video('video_id')
print(video['title'])
print(video['statistics']['viewCount'])

# Get comments
comments = client.get_comments('video_id')
```

#### OpenLibraryClient - Book Data

```python
from data_fetching import OpenLibraryClient

client = OpenLibraryClient()

# Search books
books = client.search(
    query='science fiction',
    limit=10
)

# Get book by ISBN
book = client.get_book_by_isbn('9780451524935')
print(book['title'])
print(book['authors'])
```

#### WolframAlphaClient - Computational Knowledge

```python
from data_fetching import WolframAlphaClient, wolfram_query, wolfram_calculate

client = WolframAlphaClient(api_key='wolfram-key')

# Simple query
result = client.query('What is the population of France?')
print(result.result)

# Mathematical calculation
calc = client.calculate('integrate x^2 from 0 to 1')
print(calc.result)

# Unit conversion
converted = client.convert('100', 'miles', 'kilometers')

# Full query with all pods
full = client.query_full('derivative of sin(x)')
for pod in full.pods:
    print(f"{pod['title']}: {pod['subpods'][0]['plaintext']}")

# Convenience functions
answer = wolfram_query('capital of Japan')
result = wolfram_calculate('2^10')
```

#### MultiArchiveClient - Multi-Provider Archives

```python
from data_fetching import MultiArchiveClient, get_archive

client = MultiArchiveClient()

# Get from specific provider
result = client.get_archive('https://example.com', provider='wayback')
result = client.get_archive('https://example.com', provider='archiveis')
result = client.get_archive('https://example.com', provider='memento')
result = client.get_archive('https://example.com', provider='12ft')

if result.success:
    print(f"Archived URL: {result.archive_url}")

# Try all providers
all_results = client.get_all_archives('https://example.com')
for provider, result in all_results.items():
    if result.success:
        print(f"{provider}: {result.archive_url}")

# Convenience function
archived_url = get_archive('https://example.com', provider='wayback')
```

### Common Interface Pattern

Most clients follow this pattern:

```python
class SomeClient:
    def __init__(self, api_key: str = None):
        """Initialize with optional API key"""

    def search(self, query: str, **kwargs) -> List[dict]:
        """Search for items"""

    def get_by_id(self, id: str) -> dict:
        """Get single item by ID"""
```

### API Key Management

API keys loaded from `/home/coolhand/API_KEYS.md`:

```python
from config import ConfigManager

config = ConfigManager()
api_key = config.get_api_key('nasa')

client = NASAClient(api_key=api_key)
```

Or set directly:

```python
client = NASAClient(api_key='explicit-key')
```

### Error Handling

```python
from data_fetching import ArxivClient

try:
    client = ArxivClient()
    papers = client.search('query')
except requests.exceptions.RequestException as e:
    logger.error(f"API request failed: {e}")
except ValueError as e:
    logger.error(f"Invalid parameters: {e}")
```

### Importing from Other Projects

```python
import sys
sys.path.insert(0, '/home/coolhand/shared')

from data_fetching import ClientFactory, ArxivClient, GitHubClient

arxiv = ClientFactory.create_client('arxiv')
papers = arxiv.search('topic')
```

### Data Models

```python
from data_fetching import ArxivPaper, ArchivedSnapshot, SemanticScholarPaper

# ArxivPaper
paper = ArxivPaper(
    id='2103.12345',
    title='Paper Title',
    authors=['Author 1', 'Author 2'],
    abstract='...',
    published='2021-03-15',
    pdf_url='https://arxiv.org/pdf/...'
)

# ArchivedSnapshot
snapshot = ArchivedSnapshot(
    timestamp='20210101120000',
    url='https://example.com',
    archive_url='https://web.archive.org/...'
)
```

### Testing

```python
import pytest
from data_fetching import ArxivClient

def test_arxiv_search():
    client = ArxivClient()
    results = client.search('test', max_results=1)
    assert len(results) <= 1
    assert all(hasattr(r, 'title') for r in results)

@pytest.fixture
def mock_client():
    """Mock client for testing"""
    from unittest.mock import Mock
    client = Mock()
    client.search.return_value = [{'title': 'Test'}]
    return client
```

### Adding New Clients

1. Create `newclient_client.py`:
```python
class NewClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = 'https://api.example.com'

    def search(self, query: str, **kwargs):
        """Search implementation"""
        response = requests.get(f"{self.base_url}/search", params={'q': query})
        return response.json()
```

2. Add to `factory.py`:
```python
CLIENT_REGISTRY = {
    'newclient': NewClient,
    # ... existing clients
}
```

3. Export in `__init__.py`:
```python
from .newclient_client import NewClient
__all__ = [..., 'NewClient']
```

### Dependencies

Core: `requests`

Per-client optional:
- ArxivClient: `arxiv` package
- Census: Census API key
- GitHub: GitHub token
- News: News API key
- Weather: Weather API key
- NASA: NASA API key

### Files in This Module

- `arxiv_client.py` - arXiv academic papers
- `semantic_scholar.py` - Research paper citations
- `pubmed_client.py` - PubMed biomedical literature
- `archive_client.py` - Internet Archive
- `census_client.py` - US Census data
- `fec_client.py` - Campaign finance
- `judiciary_client.py` - Court records
- `github_client.py` - GitHub repositories
- `nasa_client.py` - NASA data
- `news_client.py` - News articles
- `wikipedia_client.py` - Wikipedia
- `weather_client.py` - Weather data
- `openlibrary_client.py` - Books
- `youtube_client.py` - YouTube videos
- `finance_client.py` - Financial data
- `mal_client.py` - Anime/manga data
- `wolfram_client.py` - Wolfram Alpha computational queries
- `factory.py` - Client factory
- `example_usage.py` - Usage examples

### Best Practices

- Always handle API rate limits
- Cache results when appropriate
- Use connection pooling for multiple requests
- Validate input parameters before API calls
- Log API errors with full context
- Store API keys securely (never in code)
- Use pagination for large result sets
- Implement timeouts for all requests

### Rate Limiting

```python
from utils.rate_limiter import RateLimiter

limiter = RateLimiter(calls=100, period=60)  # 100 calls per minute

with limiter:
    results = client.search(query)
```
