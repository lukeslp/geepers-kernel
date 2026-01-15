"""
PubMed API Client
Provides programmatic access to PubMed medical/biomedical literature.

This module offers a clean interface for searching and retrieving papers from PubMed,
completing the academic research trio alongside ArxivClient and SemanticScholarClient.

Author: Luke Steuber
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import logging
import requests

logger = logging.getLogger(__name__)

# API URLs
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Common headers
HEADERS = {
    "User-Agent": "DrEamerAI/1.0 (https://dr.eamer.dev; api@dr.eamer.dev)"
}


@dataclass
class PubMedArticle:
    """Dataclass representing a PubMed article"""
    pmid: str
    title: str
    authors: List[str]
    journal: str
    publication_date: str
    abstract: Optional[str] = None
    doi: Optional[str] = None
    publication_types: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    mesh_terms: Optional[List[str]] = None

    @property
    def url(self) -> str:
        """Get the PubMed URL for this article"""
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"

    @classmethod
    def from_summary(cls, pmid: str, data: Dict[str, Any]) -> 'PubMedArticle':
        """Create PubMedArticle from PubMed summary API response"""
        # Extract authors
        authors = []
        if "authors" in data:
            for author in data["authors"]:
                if "name" in author:
                    authors.append(author["name"])

        # Extract DOI from elocationid
        doi = None
        elocationid = data.get("elocationid", "")
        if elocationid and "doi:" in elocationid.lower():
            doi = elocationid.replace("doi:", "").strip()

        return cls(
            pmid=pmid,
            title=data.get("title", ""),
            authors=authors,
            journal=data.get("fulljournalname", data.get("source", "")),
            publication_date=data.get("pubdate", ""),
            abstract=data.get("abstract"),
            doi=doi,
            publication_types=data.get("pubtype", []),
            keywords=data.get("keywords", []),
            mesh_terms=None  # Requires separate fetch
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'pmid': self.pmid,
            'title': self.title,
            'authors': self.authors,
            'journal': self.journal,
            'publication_date': self.publication_date,
            'abstract': self.abstract,
            'doi': self.doi,
            'publication_types': self.publication_types,
            'keywords': self.keywords,
            'mesh_terms': self.mesh_terms,
            'url': self.url,
            'source': 'PubMed'
        }


class PubMedClient:
    """Client for interacting with the PubMed API"""

    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None):
        """
        Initialize the PubMed client.

        Args:
            api_key: Optional NCBI API key for higher rate limits
            email: Optional email for NCBI to contact about usage
        """
        self.api_key = api_key
        self.email = email
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _add_api_params(self, params: Dict) -> Dict:
        """Add API key and email to request params if available"""
        if self.api_key:
            params['api_key'] = self.api_key
        if self.email:
            params['email'] = self.email
        return params

    def search(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance",
        date_range: Optional[str] = None,
        journal: Optional[str] = None
    ) -> List[PubMedArticle]:
        """
        Search PubMed for articles matching the query.

        Args:
            query: Search query string
            max_results: Maximum number of results to return (default: 10)
            sort_by: Sort order - "relevance" or "date" (default: "relevance")
            date_range: Optional date filter (e.g., "2020/01/01:2024/01/01")
            journal: Optional journal name filter

        Returns:
            List of PubMedArticle objects

        Raises:
            ValueError: If sort_by is invalid
            requests.RequestException: If API request fails
        """
        if sort_by not in ["relevance", "date"]:
            raise ValueError(f"Invalid sort_by: {sort_by}. Must be 'relevance' or 'date'")

        try:
            logger.info(f"Searching PubMed for: '{query}' (max: {max_results}, sort: {sort_by})")

            # Build search query with filters
            search_query = query

            if journal:
                search_query += f" AND {journal}[Journal]"

            if date_range:
                search_query += f" AND {date_range}[Date - Publication]"

            # Step 1: Search for IDs
            search_params = self._add_api_params({
                "db": "pubmed",
                "term": search_query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance" if sort_by == "relevance" else "pub date"
            })

            search_response = self.session.get(PUBMED_SEARCH_URL, params=search_params, timeout=30)
            search_response.raise_for_status()

            search_data = search_response.json()
            id_list = search_data.get("esearchresult", {}).get("idlist", [])

            if not id_list:
                logger.info(f"No results found for PubMed query: {query}")
                return []

            logger.info(f"Found {len(id_list)} article IDs, fetching summaries...")

            # Step 2: Get summaries for the IDs
            articles = self._get_summaries(id_list)

            logger.info(f"Retrieved {len(articles)} articles for query: '{query}'")
            return articles

        except requests.RequestException as e:
            logger.error(f"Error searching PubMed: {e}")
            raise

    def _get_summaries(self, pmids: List[str]) -> List[PubMedArticle]:
        """
        Get article summaries for a list of PMIDs.

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of PubMedArticle objects
        """
        if not pmids:
            return []

        summary_params = self._add_api_params({
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json"
        })

        summary_response = self.session.get(PUBMED_SUMMARY_URL, params=summary_params, timeout=30)
        summary_response.raise_for_status()

        summary_data = summary_response.json()
        result_list = summary_data.get("result", {})

        # Get ordered UIDs
        uids = result_list.pop("uids", pmids) if "uids" in result_list else pmids

        # Build article list
        articles = []
        for uid in uids:
            if uid in result_list:
                article = PubMedArticle.from_summary(uid, result_list[uid])
                articles.append(article)

        return articles

    def get_by_id(self, pmid: str) -> Optional[PubMedArticle]:
        """
        Get a specific article by its PubMed ID.

        Args:
            pmid: PubMed ID (e.g., "12345678")

        Returns:
            PubMedArticle object if found, None otherwise

        Raises:
            requests.RequestException: If API request fails
        """
        try:
            # Clean PMID
            clean_pmid = pmid.strip().replace("PMID:", "").replace("pmid:", "")

            logger.info(f"Fetching PubMed article: {clean_pmid}")

            articles = self._get_summaries([clean_pmid])

            if not articles:
                logger.warning(f"Article not found: {clean_pmid}")
                return None

            return articles[0]

        except requests.RequestException as e:
            logger.error(f"Error fetching PubMed article {pmid}: {e}")
            raise

    def get_by_ids(self, pmids: List[str]) -> List[PubMedArticle]:
        """
        Get multiple articles by their PubMed IDs.

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of PubMedArticle objects (may be shorter than input if some not found)

        Raises:
            requests.RequestException: If API request fails
        """
        try:
            # Clean PMIDs
            clean_ids = [p.strip().replace("PMID:", "").replace("pmid:", "") for p in pmids]

            logger.info(f"Fetching {len(clean_ids)} PubMed articles")

            articles = self._get_summaries(clean_ids)

            logger.info(f"Retrieved {len(articles)}/{len(clean_ids)} articles")
            return articles

        except requests.RequestException as e:
            logger.error(f"Error fetching PubMed articles: {e}")
            raise

    def search_by_author(
        self,
        author: str,
        max_results: int = 10,
        sort_by: str = "date"
    ) -> List[PubMedArticle]:
        """
        Search for articles by a specific author.

        Args:
            author: Author name (e.g., "Smith J" or "Smith John")
            max_results: Maximum number of results (default: 10)
            sort_by: Sort order - "relevance" or "date" (default: "date")

        Returns:
            List of PubMedArticle objects
        """
        query = f'{author}[Author]'
        return self.search(query, max_results, sort_by)

    def search_by_mesh(
        self,
        mesh_term: str,
        max_results: int = 10,
        sort_by: str = "relevance"
    ) -> List[PubMedArticle]:
        """
        Search for articles by MeSH (Medical Subject Heading) term.

        Args:
            mesh_term: MeSH term (e.g., "Diabetes Mellitus")
            max_results: Maximum number of results (default: 10)
            sort_by: Sort order - "relevance" or "date" (default: "relevance")

        Returns:
            List of PubMedArticle objects
        """
        query = f'{mesh_term}[MeSH Terms]'
        return self.search(query, max_results, sort_by)

    def search_clinical_trials(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance"
    ) -> List[PubMedArticle]:
        """
        Search for clinical trial articles.

        Args:
            query: Search query string
            max_results: Maximum number of results (default: 10)
            sort_by: Sort order - "relevance" or "date" (default: "relevance")

        Returns:
            List of PubMedArticle objects
        """
        full_query = f'{query} AND "Clinical Trial"[Publication Type]'
        return self.search(full_query, max_results, sort_by)

    def search_reviews(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance"
    ) -> List[PubMedArticle]:
        """
        Search for review articles.

        Args:
            query: Search query string
            max_results: Maximum number of results (default: 10)
            sort_by: Sort order - "relevance" or "date" (default: "relevance")

        Returns:
            List of PubMedArticle objects
        """
        full_query = f'{query} AND "Review"[Publication Type]'
        return self.search(full_query, max_results, sort_by)

    def format_article(self, article: PubMedArticle, index: Optional[int] = None) -> str:
        """
        Format an article for display.

        Args:
            article: PubMedArticle object
            index: Optional article number for display

        Returns:
            Formatted string representation of the article
        """
        output = []

        if index:
            output.append(f"\n{'='*70}")
            output.append(f"Article #{index}")
            output.append('='*70)

        output.append(f"Title: {article.title}")
        output.append(f"Authors: {', '.join(article.authors)}")
        output.append(f"Journal: {article.journal}")
        output.append(f"Published: {article.publication_date}")
        output.append(f"PMID: {article.pmid}")
        output.append(f"URL: {article.url}")

        if article.doi:
            output.append(f"DOI: {article.doi}")

        if article.publication_types:
            output.append(f"Type: {', '.join(article.publication_types)}")

        if article.abstract:
            output.append(f"\nAbstract:\n{article.abstract}")

        return '\n'.join(output)


# Convenience functions for backward compatibility and ease of use
def search_pubmed(query: str, max_results: int = 10, sort_by: str = "relevance") -> List[Dict]:
    """
    Convenience function for searching PubMed (returns dicts).

    Args:
        query: Search query string
        max_results: Maximum number of results (default: 10)
        sort_by: Sort order - "relevance" or "date" (default: "relevance")

    Returns:
        List of article dictionaries
    """
    client = PubMedClient()
    articles = client.search(query, max_results, sort_by)
    return [article.to_dict() for article in articles]


def get_article_by_pmid(pmid: str) -> Optional[Dict]:
    """
    Convenience function for getting an article by PMID (returns dict).

    Args:
        pmid: PubMed ID

    Returns:
        Article dictionary if found, None otherwise
    """
    client = PubMedClient()
    article = client.get_by_id(pmid)
    return article.to_dict() if article else None
