"""
Data Fetching MCP Server

Exposes shared.data_fetching capabilities through MCP protocol.

Tools provided:
- dream_of_census_acs: Fetch American Community Survey data
- dream_of_census_saipe: Fetch poverty estimates
- dream_of_census_variables: Search Census variable catalog
- dream_of_arxiv: Search arXiv papers
- dream_of_semantic_scholar: Search research papers
- dream_of_semantic_scholar_paper: Get paper details
- dream_of_wayback: Search Wayback Machine
- dream_of_wayback_snapshots: List available snapshots

Resources provided:
- census://variables/{table}: Census variable catalog
- arxiv://category/{category}: arXiv category info
- archive://snapshot/{url}/{timestamp}: Wayback snapshot metadata
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import from shared library
import sys
sys.path.insert(0, '/home/coolhand/shared')
from data_fetching import CensusClient, ArxivClient, SemanticScholarClient, ArchiveClient
from config import ConfigManager

logger = logging.getLogger(__name__)


class DataServer:
    """
    MCP server for data fetching capabilities.

    Exposes Census, arXiv, Semantic Scholar, and Archive.org through MCP protocol.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize data fetching MCP server.

        Args:
            config_manager: ConfigManager instance (creates new one if None)
        """
        self.config = config_manager or ConfigManager(app_name='mcp_data')

        # Initialize clients (lazy loading)
        self._census_client = None
        self._arxiv_client = None
        self._semantic_scholar_client = None
        self._archive_client = None

    def get_census_client(self) -> CensusClient:
        """Get or create Census client."""
        if self._census_client is None:
            api_key = self.config.get('CENSUS_API_KEY')
            self._census_client = CensusClient(
                api_key=api_key,
                use_cache=True
            )
        return self._census_client

    def get_arxiv_client(self) -> ArxivClient:
        """Get or create arXiv client."""
        if self._arxiv_client is None:
            self._arxiv_client = ArxivClient()
        return self._arxiv_client

    def get_semantic_scholar_client(self) -> SemanticScholarClient:
        """Get or create Semantic Scholar client."""
        if self._semantic_scholar_client is None:
            self._semantic_scholar_client = SemanticScholarClient()
        return self._semantic_scholar_client

    def get_archive_client(self) -> ArchiveClient:
        """Get or create Archive.org client."""
        if self._archive_client is None:
            self._archive_client = ArchiveClient()
        return self._archive_client

    # -------------------------------------------------------------------------
    # MCP Tools - Census Bureau
    # -------------------------------------------------------------------------

    def tool_dream_of_census_acs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_census_acs

        Fetch American Community Survey (ACS) demographic data.

        Arguments:
            year (int): Census year (e.g., 2022)
            variables (dict): Variable mapping {code: name}
            geography (str, optional): Geographic level (default: county:*)
            state (str, optional): State FIPS code filter

        Returns:
            {success: bool, records: List[Dict], metadata: Dict}
        """
        try:
            year = arguments.get('year')
            variables = arguments.get('variables')

            if not year or not variables:
                return {
                    "success": False,
                    "error": "Missing required arguments: year and variables"
                }

            client = self.get_census_client()

            df = client.fetch_acs(
                year=year,
                variables=variables,
                geography=arguments.get('geography', 'county:*'),
                state=arguments.get('state')
            )

            # Convert DataFrame to records
            records = df.to_dict('records')

            return {
                "success": True,
                "records": records,
                "metadata": {
                    "year": year,
                    "record_count": len(records),
                    "source": "Census ACS 5-year estimates",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.exception(f"Error in dream_of_census_acs: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_dream_of_census_saipe(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_census_saipe

        Fetch Small Area Income and Poverty Estimates (SAIPE).

        Arguments:
            year (int): Census year
            geography (str, optional): county, state, or us (default: county)
            state (str, optional): State FIPS code filter

        Returns:
            {success: bool, records: List[Dict], metadata: Dict}
        """
        try:
            year = arguments.get('year')
            if not year:
                return {
                    "success": False,
                    "error": "Missing required argument: year"
                }

            client = self.get_census_client()

            df = client.fetch_saipe(
                year=year,
                geography=arguments.get('geography', 'county'),
                state=arguments.get('state')
            )

            records = df.to_dict('records')

            return {
                "success": True,
                "records": records,
                "metadata": {
                    "year": year,
                    "record_count": len(records),
                    "source": "Census SAIPE",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.exception(f"Error in dream_of_census_saipe: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_dream_of_census_variables(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_census_variables

        Search Census variable catalog.

        Arguments:
            search_term (str, optional): Keyword to search
            table (str, optional): Specific table (e.g., "B17001")

        Returns:
            {success: bool, variables: List[Dict]}
        """
        try:
            # This would require implementing variable catalog search in CensusClient
            # For now, return placeholder
            return {
                "success": True,
                "variables": [],
                "message": "Variable catalog search not yet implemented"
            }

        except Exception as e:
            logger.exception(f"Error in dream_of_census_variables: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - arXiv
    # -------------------------------------------------------------------------

    def tool_dream_of_arxiv(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_arxiv

        Search arXiv for academic papers.

        Arguments:
            query (str): Search query
            max_results (int, optional): Max papers to return (default: 5)
            sort_by (str, optional): relevance or date (default: relevance)
            category (str, optional): arXiv category filter

        Returns:
            {success: bool, papers: List[Dict], metadata: Dict}
        """
        try:
            query = arguments.get('query')
            if not query:
                return {
                    "success": False,
                    "error": "Missing required argument: query"
                }

            client = self.get_arxiv_client()

            # Add category filter if provided
            search_query = query
            category = arguments.get('category')
            if category:
                search_query = f"cat:{category} AND {query}"

            papers = client.search(
                query=search_query,
                max_results=arguments.get('max_results', 5),
                sort_by=arguments.get('sort_by', 'relevance')
            )

            # Convert to dicts
            paper_dicts = [p.to_dict() for p in papers]

            return {
                "success": True,
                "papers": paper_dicts,
                "metadata": {
                    "query": query,
                    "result_count": len(paper_dicts),
                    "source": "arXiv",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.exception(f"Error in dream_of_arxiv: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - Semantic Scholar
    # -------------------------------------------------------------------------

    def tool_dream_of_semantic_scholar(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_semantic_scholar

        Search Semantic Scholar for research papers.

        Arguments:
            query (str): Search query
            limit (int, optional): Max papers to return (default: 10)
            fields (list, optional): Fields to return

        Returns:
            {success: bool, papers: List[Dict], metadata: Dict}
        """
        try:
            query = arguments.get('query')
            if not query:
                return {
                    "success": False,
                    "error": "Missing required argument: query"
                }

            client = self.get_semantic_scholar_client()

            papers = client.search_papers(
                query=query,
                limit=arguments.get('limit', 10),
                fields=arguments.get('fields')
            )

            # Convert to dicts
            paper_dicts = [p.to_dict() for p in papers]

            return {
                "success": True,
                "papers": paper_dicts,
                "metadata": {
                    "query": query,
                    "result_count": len(paper_dicts),
                    "source": "Semantic Scholar",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.exception(f"Error in dream_of_semantic_scholar: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_dream_of_semantic_scholar_paper(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_semantic_scholar_paper

        Get detailed information about a specific paper.

        Arguments:
            paper_id (str): Semantic Scholar paper ID
            fields (list, optional): Fields to return

        Returns:
            {success: bool, paper: Dict}
        """
        try:
            paper_id = arguments.get('paper_id')
            if not paper_id:
                return {
                    "success": False,
                    "error": "Missing required argument: paper_id"
                }

            client = self.get_semantic_scholar_client()

            paper = client.get_paper_details(
                paper_id=paper_id,
                fields=arguments.get('fields')
            )

            if paper:
                return {
                    "success": True,
                    "paper": paper.to_dict()
                }
            else:
                return {
                    "success": False,
                    "error": f"Paper not found: {paper_id}"
                }

        except Exception as e:
            logger.exception(f"Error in dream_of_semantic_scholar_paper: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - Internet Archive / Wayback Machine
    # -------------------------------------------------------------------------

    def tool_dream_of_wayback(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_wayback

        Get the most recent archived snapshot of a URL.

        Arguments:
            url (str): URL to search for
            timestamp (str, optional): Specific timestamp (YYYYMMDDhhmmss)

        Returns:
            {success: bool, snapshot: Dict}
        """
        try:
            url = arguments.get('url')
            if not url:
                return {
                    "success": False,
                    "error": "Missing required argument: url"
                }

            client = self.get_archive_client()

            snapshot = client.get_latest_snapshot(url)

            if snapshot:
                return {
                    "success": True,
                    "snapshot": {
                        "url": snapshot.url,
                        "timestamp": snapshot.timestamp.isoformat(),
                        "status_code": snapshot.status_code,
                        "original_url": snapshot.original_url,
                        "archive_url": snapshot.archive_url
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"No archived snapshots found for: {url}"
                }

        except Exception as e:
            logger.exception(f"Error in dream_of_wayback: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def tool_dream_of_wayback_snapshots(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_wayback_snapshots

        List all available snapshots for a URL.

        Arguments:
            url (str): URL to search for
            year (int, optional): Filter by year

        Returns:
            {success: bool, snapshots: List[Dict]}
        """
        try:
            url = arguments.get('url')
            if not url:
                return {
                    "success": False,
                    "error": "Missing required argument: url"
                }

            client = self.get_archive_client()

            # Get all snapshots for the URL
            # This would require implementing list_snapshots in ArchiveClient
            # For now, just get latest as example
            snapshot = client.get_latest_snapshot(url)

            snapshots = []
            if snapshot:
                snapshots = [{
                    "url": snapshot.url,
                    "timestamp": snapshot.timestamp.isoformat(),
                    "status_code": snapshot.status_code,
                    "archive_url": snapshot.archive_url
                }]

            return {
                "success": True,
                "snapshots": snapshots,
                "metadata": {
                    "url": url,
                    "snapshot_count": len(snapshots),
                    "source": "Internet Archive Wayback Machine"
                }
            }

        except Exception as e:
            logger.exception(f"Error in dream_of_wayback_snapshots: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - Finance (Alpha Vantage)
    # -------------------------------------------------------------------------

    def get_finance_client(self) -> 'FinanceClient':
        """Get or create Finance client."""
        if not hasattr(self, '_finance_client') or self._finance_client is None:
            from data_fetching import FinanceClient
            self._finance_client = FinanceClient()
        return self._finance_client

    def tool_dream_of_finance_stock(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_finance_stock
        
        Get stock market data from Alpha Vantage.
        
        Arguments:
            symbol (str): Stock ticker symbol (e.g., "AAPL")
            interval (str, optional): Time interval (1min, 5min, 15min, 30min, 60min, daily)
            
        Returns:
            {success: bool, data: Dict, metadata: Dict}
        """
        try:
            symbol = arguments.get('symbol')
            if not symbol:
                return {
                    "success": False,
                    "error": "Missing required argument: symbol"
                }
            
            client = self.get_finance_client()
            interval = arguments.get('interval', 'daily')
            
            if interval == 'daily':
                data = client.get_daily(symbol)
            else:
                data = client.get_intraday(symbol, interval=interval)
            
            return {
                "success": True,
                "data": data,
                "metadata": {
                    "symbol": symbol,
                    "interval": interval,
                    "source": "Alpha Vantage",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        
        except Exception as e:
            logger.exception(f"Error in dream_of_finance_stock: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - GitHub
    # -------------------------------------------------------------------------

    def get_github_client(self) -> 'GitHubClient':
        """Get or create GitHub client."""
        if not hasattr(self, '_github_client') or self._github_client is None:
            from data_fetching import GitHubClient
            self._github_client = GitHubClient()
        return self._github_client

    def tool_dream_of_github_repos(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_github_repos
        
        Search GitHub repositories.
        
        Arguments:
            query (str): Search query
            sort (str, optional): Sort by (stars, forks, updated)
            per_page (int, optional): Results per page (default: 30)
            
        Returns:
            {success: bool, repositories: List[Dict], metadata: Dict}
        """
        try:
            query = arguments.get('query')
            if not query:
                return {
                    "success": False,
                    "error": "Missing required argument: query"
                }
            
            client = self.get_github_client()
            result = client.search_repositories(
                query=query,
                sort=arguments.get('sort', 'stars'),
                per_page=arguments.get('per_page', 30)
            )
            
            return {
                "success": True,
                "repositories": result.get('items', []),
                "total_count": result.get('total_count', 0),
                "metadata": {
                    "query": query,
                    "source": "GitHub API",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        
        except Exception as e:
            logger.exception(f"Error in dream_of_github_repos: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - NASA
    # -------------------------------------------------------------------------

    def get_nasa_client(self) -> 'NASAClient':
        """Get or create NASA client."""
        if not hasattr(self, '_nasa_client') or self._nasa_client is None:
            from data_fetching import NASAClient
            self._nasa_client = NASAClient()
        return self._nasa_client

    def tool_dream_of_nasa_apod(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_nasa_apod
        
        Get NASA Astronomy Picture of the Day.
        
        Arguments:
            date (str, optional): Date in YYYY-MM-DD format (default: today)
            count (int, optional): Number of random APODs
            
        Returns:
            {success: bool, apod: Dict, metadata: Dict}
        """
        try:
            client = self.get_nasa_client()
            apod = client.get_apod(
                date=arguments.get('date'),
                count=arguments.get('count')
            )
            
            return {
                "success": True,
                "apod": apod,
                "metadata": {
                    "source": "NASA APOD API",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        
        except Exception as e:
            logger.exception(f"Error in dream_of_nasa_apod: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - News API
    # -------------------------------------------------------------------------

    def get_news_client(self) -> 'NewsClient':
        """Get or create News client."""
        if not hasattr(self, '_news_client') or self._news_client is None:
            from data_fetching import NewsClient
            self._news_client = NewsClient()
        return self._news_client

    def tool_dream_of_news(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_news
        
        Get top news headlines.
        
        Arguments:
            query (str, optional): Search query
            country (str, optional): Country code (default: us)
            category (str, optional): Category (business, technology, etc.)
            page_size (int, optional): Results per page (default: 20)
            
        Returns:
            {success: bool, articles: List[Dict], metadata: Dict}
        """
        try:
            client = self.get_news_client()
            
            if arguments.get('query'):
                result = client.search_everything(
                    query=arguments['query'],
                    page_size=arguments.get('page_size', 20)
                )
            else:
                result = client.get_top_headlines(
                    country=arguments.get('country', 'us'),
                    category=arguments.get('category'),
                    page_size=arguments.get('page_size', 20)
                )
            
            return {
                "success": True,
                "articles": result.get('articles', []),
                "total_results": result.get('totalResults', 0),
                "metadata": {
                    "source": "News API",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        
        except Exception as e:
            logger.exception(f"Error in dream_of_news: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - OpenLibrary
    # -------------------------------------------------------------------------

    def get_openlibrary_client(self) -> 'OpenLibraryClient':
        """Get or create OpenLibrary client."""
        if not hasattr(self, '_openlibrary_client') or self._openlibrary_client is None:
            from data_fetching import OpenLibraryClient
            self._openlibrary_client = OpenLibraryClient()
        return self._openlibrary_client

    def tool_dream_of_books(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_books
        
        Search books via OpenLibrary.
        
        Arguments:
            query (str): Search query
            limit (int, optional): Max results (default: 10)
            
        Returns:
            {success: bool, books: List[Dict], metadata: Dict}
        """
        try:
            query = arguments.get('query')
            if not query:
                return {
                    "success": False,
                    "error": "Missing required argument: query"
                }
            
            client = self.get_openlibrary_client()
            books = client.search(query=query, limit=arguments.get('limit', 10))
            
            return {
                "success": True,
                "books": books,
                "count": len(books),
                "metadata": {
                    "query": query,
                    "source": "OpenLibrary",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        
        except Exception as e:
            logger.exception(f"Error in dream_of_books: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - Weather
    # -------------------------------------------------------------------------

    def get_weather_client(self) -> 'WeatherClient':
        """Get or create Weather client."""
        if not hasattr(self, '_weather_client') or self._weather_client is None:
            from data_fetching import WeatherClient
            self._weather_client = WeatherClient()
        return self._weather_client

    def tool_dream_of_weather(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_weather
        
        Get current weather for a location.
        
        Arguments:
            location (str): City name or location
            units (str, optional): Units (metric, imperial, standard)
            
        Returns:
            {success: bool, weather: Dict, metadata: Dict}
        """
        try:
            location = arguments.get('location')
            if not location:
                return {
                    "success": False,
                    "error": "Missing required argument: location"
                }
            
            client = self.get_weather_client()
            weather = client.get_current_weather(
                location=location,
                units=arguments.get('units', 'metric')
            )
            
            return {
                "success": True,
                "weather": weather,
                "metadata": {
                    "location": location,
                    "source": "OpenWeatherMap",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        
        except Exception as e:
            logger.exception(f"Error in dream_of_weather: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - Wikipedia
    # -------------------------------------------------------------------------

    def get_wikipedia_client(self) -> 'WikipediaClient':
        """Get or create Wikipedia client."""
        if not hasattr(self, '_wikipedia_client') or self._wikipedia_client is None:
            from data_fetching import WikipediaClient
            self._wikipedia_client = WikipediaClient()
        return self._wikipedia_client

    def tool_dream_of_wikipedia(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_wikipedia
        
        Search Wikipedia and get article content.
        
        Arguments:
            query (str): Search query
            sentences (int, optional): Number of sentences in summary (default: 3)
            
        Returns:
            {success: bool, article: Dict, metadata: Dict}
        """
        try:
            query = arguments.get('query')
            if not query:
                return {
                    "success": False,
                    "error": "Missing required argument: query"
                }
            
            client = self.get_wikipedia_client()
            article = client.search(
                query=query,
                sentences=arguments.get('sentences', 3)
            )
            
            return {
                "success": True,
                "article": article,
                "metadata": {
                    "query": query,
                    "source": "Wikipedia",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        
        except Exception as e:
            logger.exception(f"Error in dream_of_wikipedia: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Tools - YouTube
    # -------------------------------------------------------------------------

    def get_youtube_client(self) -> 'YouTubeClient':
        """Get or create YouTube client."""
        if not hasattr(self, '_youtube_client') or self._youtube_client is None:
            from data_fetching import YouTubeClient
            self._youtube_client = YouTubeClient()
        return self._youtube_client

    def tool_dream_of_youtube(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_of_youtube
        
        Search YouTube videos.
        
        Arguments:
            query (str): Search query
            max_results (int, optional): Max results (default: 10)
            order (str, optional): Sort order (relevance, date, rating, views)
            
        Returns:
            {success: bool, videos: List[Dict], metadata: Dict}
        """
        try:
            query = arguments.get('query')
            if not query:
                return {
                    "success": False,
                    "error": "Missing required argument: query"
                }
            
            client = self.get_youtube_client()
            videos = client.search(
                query=query,
                max_results=arguments.get('max_results', 10),
                order=arguments.get('order', 'relevance')
            )
            
            return {
                "success": True,
                "videos": videos,
                "count": len(videos),
                "metadata": {
                    "query": query,
                    "source": "YouTube Data API",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        
        except Exception as e:
            logger.exception(f"Error in dream_of_youtube: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Resources
    # -------------------------------------------------------------------------

    def resource_census_variables(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: census://variables/{table}

        Returns Census variable catalog for a table.

        Args:
            uri: Resource URI (e.g., "census://variables/B17001")

        Returns:
            Variable catalog
        """
        try:
            # Parse URI: census://variables/{table}
            parts = uri.replace('census://variables/', '')
            table = parts

            # This would query Census API for variable definitions
            # For now, return placeholder
            return {
                "uri": uri,
                "table": table,
                "variables": [],
                "message": "Census variable catalog not yet implemented"
            }

        except Exception as e:
            logger.exception(f"Error in resource_census_variables: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }

    def resource_arxiv_category(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: arxiv://category/{category}

        Returns arXiv category information.

        Args:
            uri: Resource URI (e.g., "arxiv://category/cs.CL")

        Returns:
            Category metadata
        """
        try:
            # Parse URI: arxiv://category/{category}
            parts = uri.replace('arxiv://category/', '')
            category = parts

            # arXiv category taxonomy
            categories = {
                'cs.CL': 'Computation and Language',
                'cs.AI': 'Artificial Intelligence',
                'cs.LG': 'Machine Learning',
                'cs.CV': 'Computer Vision and Pattern Recognition',
                'cs.NE': 'Neural and Evolutionary Computing',
                'math.ST': 'Statistics Theory',
                'stat.ML': 'Machine Learning (Statistics)',
                'physics.data-an': 'Data Analysis, Statistics and Probability',
                'q-bio.QM': 'Quantitative Methods'
            }

            category_name = categories.get(category, 'Unknown')

            return {
                "uri": uri,
                "category": category,
                "name": category_name,
                "all_categories": categories
            }

        except Exception as e:
            logger.exception(f"Error in resource_arxiv_category: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }

    def resource_archive_snapshot(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: archive://snapshot/{url}/{timestamp}

        Returns metadata about an archived snapshot.

        Args:
            uri: Resource URI (e.g., "archive://snapshot/example.com/20231201")

        Returns:
            Snapshot metadata
        """
        try:
            # Parse URI: archive://snapshot/{url}/{timestamp}
            parts = uri.replace('archive://snapshot/', '').split('/')
            url = parts[0]
            parts[1] if len(parts) > 1 else None

            client = self.get_archive_client()

            snapshot = client.get_latest_snapshot(url)

            if snapshot:
                return {
                    "uri": uri,
                    "url": url,
                    "snapshot": {
                        "archive_url": snapshot.archive_url,
                        "timestamp": snapshot.timestamp.isoformat(),
                        "status_code": snapshot.status_code
                    }
                }
            else:
                return {
                    "uri": uri,
                    "error": f"No snapshot found for: {url}"
                }

        except Exception as e:
            logger.exception(f"Error in resource_archive_snapshot: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Server Interface
    # -------------------------------------------------------------------------

    def get_tools_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP tools manifest.

        Returns:
            List of tool definitions
        """
        return [
            # Census tools
            {
                "name": "dream_of_census_acs",
                "description": "Fetch American Community Survey (ACS) demographic data",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "integer",
                            "description": "Census year (e.g., 2022)"
                        },
                        "variables": {
                            "type": "object",
                            "description": "Variable mapping {code: name}"
                        },
                        "geography": {
                            "type": "string",
                            "description": "Geographic level (default: county:*)"
                        },
                        "state": {
                            "type": "string",
                            "description": "State FIPS code filter (optional)"
                        }
                    },
                    "required": ["year", "variables"]
                }
            },
            {
                "name": "dream_of_census_saipe",
                "description": "Fetch Small Area Income and Poverty Estimates",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "integer",
                            "description": "Census year"
                        },
                        "geography": {
                            "type": "string",
                            "description": "county, state, or us (default: county)"
                        },
                        "state": {
                            "type": "string",
                            "description": "State FIPS code filter (optional)"
                        }
                    },
                    "required": ["year"]
                }
            },
            {
                "name": "dream_of_census_variables",
                "description": "Search Census variable catalog",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "search_term": {
                            "type": "string",
                            "description": "Keyword to search (optional)"
                        },
                        "table": {
                            "type": "string",
                            "description": "Specific table (e.g., 'B17001') (optional)"
                        }
                    }
                }
            },
            # arXiv tools
            {
                "name": "dream_of_arxiv",
                "description": "Search arXiv for academic papers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Max papers to return (default: 5)"
                        },
                        "sort_by": {
                            "type": "string",
                            "description": "relevance or date (default: relevance)"
                        },
                        "category": {
                            "type": "string",
                            "description": "arXiv category filter (e.g., 'cs.CL') (optional)"
                        }
                    },
                    "required": ["query"]
                }
            },
            # Semantic Scholar tools
            {
                "name": "dream_of_semantic_scholar",
                "description": "Search Semantic Scholar for research papers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max papers to return (default: 10)"
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields to return (optional)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "dream_of_semantic_scholar_paper",
                "description": "Get detailed information about a specific paper",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "paper_id": {
                            "type": "string",
                            "description": "Semantic Scholar paper ID"
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields to return (optional)"
                        }
                    },
                    "required": ["paper_id"]
                }
            },
            # Wayback Machine tools
            {
                "name": "dream_of_wayback",
                "description": "Get the most recent archived snapshot of a URL",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to search for"
                        },
                        "timestamp": {
                            "type": "string",
                            "description": "Specific timestamp (YYYYMMDDhhmmss) (optional)"
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "dream_of_wayback_snapshots",
                "description": "List all available snapshots for a URL",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to search for"
                        },
                        "year": {
                            "type": "integer",
                            "description": "Filter by year (optional)"
                        }
                    },
                    "required": ["url"]
                }
            },
            # Finance tools
            {
                "name": "dream_of_finance_stock",
                "description": "Get stock market data from Alpha Vantage",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock ticker symbol (e.g., AAPL)"
                        },
                        "interval": {
                            "type": "string",
                            "description": "Time interval (1min, 5min, 15min, 30min, 60min, daily)"
                        }
                    },
                    "required": ["symbol"]
                }
            },
            # GitHub tools
            {
                "name": "dream_of_github_repos",
                "description": "Search GitHub repositories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "sort": {
                            "type": "string",
                            "description": "Sort by (stars, forks, updated)"
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "Results per page (default: 30)"
                        }
                    },
                    "required": ["query"]
                }
            },
            # NASA tools
            {
                "name": "dream_of_nasa_apod",
                "description": "Get NASA Astronomy Picture of the Day",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format (optional)"
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of random APODs (optional)"
                        }
                    }
                }
            },
            # News tools
            {
                "name": "dream_of_news",
                "description": "Get top news headlines",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (optional)"
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code (default: us)"
                        },
                        "category": {
                            "type": "string",
                            "description": "Category (business, technology, etc.)"
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Results per page (default: 20)"
                        }
                    }
                }
            },
            # OpenLibrary tools
            {
                "name": "dream_of_books",
                "description": "Search books via OpenLibrary",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results (default: 10)"
                        }
                    },
                    "required": ["query"]
                }
            },
            # Weather tools
            {
                "name": "dream_of_weather",
                "description": "Get current weather for a location",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name or location"
                        },
                        "units": {
                            "type": "string",
                            "description": "Units (metric, imperial, standard)"
                        }
                    },
                    "required": ["location"]
                }
            },
            # Wikipedia tools
            {
                "name": "dream_of_wikipedia",
                "description": "Search Wikipedia and get article content",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "sentences": {
                            "type": "integer",
                            "description": "Number of sentences in summary (default: 3)"
                        }
                    },
                    "required": ["query"]
                }
            },
            # YouTube tools
            {
                "name": "dream_of_youtube",
                "description": "Search YouTube videos",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Max results (default: 10)"
                        },
                        "order": {
                            "type": "string",
                            "description": "Sort order (relevance, date, rating, views)"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

    def get_resources_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP resources manifest.

        Returns:
            List of resource templates
        """
        return [
            {
                "uri": "census://variables/{table}",
                "name": "Census Variable Catalog",
                "description": "Census variable definitions for a table",
                "mimeType": "application/json"
            },
            {
                "uri": "arxiv://category/{category}",
                "name": "arXiv Category Info",
                "description": "arXiv category taxonomy and metadata",
                "mimeType": "application/json"
            },
            {
                "uri": "archive://snapshot/{url}/{timestamp}",
                "name": "Wayback Snapshot Metadata",
                "description": "Internet Archive snapshot information",
                "mimeType": "application/json"
            }
        ]

