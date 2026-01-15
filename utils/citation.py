"""
Citation Management Utilities
BibTeX generation, citation formatting, and citation database management.

Extracted from schollama for reuse across projects.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


# Check for bibtexparser availability
try:
    from bibtexparser.bwriter import BibTexWriter
    from bibtexparser.bibdatabase import BibDatabase
    BIBTEX_PARSER_AVAILABLE = True
except ImportError:
    BIBTEX_PARSER_AVAILABLE = False
    logger.warning("bibtexparser not installed. BibTeX features disabled. Install with: pip install bibtexparser")


@dataclass
class Citation:
    """Represents a bibliographic citation"""
    title: str
    authors: List[str]
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = None
    citation_key: Optional[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.citation_key is None:
            self.citation_key = self.generate_citation_key()

    def generate_citation_key(self) -> str:
        """
        Generate a citation key from author and year.

        Returns:
            Citation key string (e.g., "Smith2023")
        """
        if not self.authors:
            base = "Unknown"
        else:
            # Get first author's last name
            first_author = self.authors[0]
            # Try to get last name (assume "First Last" or "Last, First" format)
            if ',' in first_author:
                last_name = first_author.split(',')[0].strip()
            else:
                parts = first_author.split()
                last_name = parts[-1] if parts else first_author

            base = last_name.replace(' ', '')

        year_str = str(self.year) if self.year else "n.d."
        return f"{base}{year_str}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'title': self.title,
            'authors': self.authors,
            'year': self.year,
            'journal': self.journal,
            'doi': self.doi,
            'url': self.url,
            'abstract': self.abstract,
            'keywords': self.keywords,
            'citation_key': self.citation_key
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Citation':
        """Create Citation from dictionary"""
        return cls(
            title=data.get('title', ''),
            authors=data.get('authors', []),
            year=data.get('year'),
            journal=data.get('journal'),
            doi=data.get('doi'),
            url=data.get('url'),
            abstract=data.get('abstract'),
            keywords=data.get('keywords', []),
            citation_key=data.get('citation_key')
        )


class CitationManager:
    """Manage collections of citations"""

    def __init__(self):
        """Initialize citation manager"""
        self.citations: List[Citation] = []

    def add(self, citation: Citation):
        """Add a citation to the collection"""
        self.citations.append(citation)
        logger.debug(f"Added citation: {citation.citation_key}")

    def add_from_dict(self, data: Dict[str, Any]):
        """Add a citation from a dictionary"""
        citation = Citation.from_dict(data)
        self.add(citation)

    def remove(self, citation_key: str) -> bool:
        """
        Remove a citation by its key.

        Args:
            citation_key: Citation key to remove

        Returns:
            True if removed, False if not found
        """
        original_length = len(self.citations)
        self.citations = [c for c in self.citations if c.citation_key != citation_key]
        removed = len(self.citations) < original_length

        if removed:
            logger.debug(f"Removed citation: {citation_key}")
        else:
            logger.warning(f"Citation not found: {citation_key}")

        return removed

    def get(self, citation_key: str) -> Optional[Citation]:
        """Get a citation by its key"""
        for citation in self.citations:
            if citation.citation_key == citation_key:
                return citation
        return None

    def to_bibtex(self, output_path: Optional[Path] = None) -> str:
        """
        Convert citations to BibTeX format.

        Args:
            output_path: Optional path to write BibTeX file

        Returns:
            BibTeX string

        Raises:
            ImportError: If bibtexparser not installed
        """
        if not BIBTEX_PARSER_AVAILABLE:
            raise ImportError("bibtexparser required. Install with: pip install bibtexparser")

        db = BibDatabase()
        db.entries = []

        for citation in self.citations:
            entry = {
                'ID': citation.citation_key,
                'ENTRYTYPE': 'article',
                'title': citation.title,
                'author': ' and '.join(citation.authors) if citation.authors else 'Unknown',
                'year': str(citation.year) if citation.year else '',
            }

            # Add optional fields
            if citation.journal:
                entry['journal'] = citation.journal
            if citation.doi:
                entry['doi'] = citation.doi
            if citation.url:
                entry['url'] = citation.url
            if citation.abstract:
                entry['abstract'] = citation.abstract
            if citation.keywords:
                entry['keywords'] = ', '.join(citation.keywords)

            # Remove empty fields
            entry = {k: v for k, v in entry.items() if v}
            db.entries.append(entry)

        writer = BibTexWriter()
        writer.indent = '    '  # 4 spaces
        writer.comma_first = False

        bibtex_str = writer.write(db)

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(bibtex_str)
            logger.info(f"Wrote BibTeX to {output_path}")

        return bibtex_str

    def to_csv(self, output_path: Path):
        """
        Export citations to CSV.

        Args:
            output_path: Path to write CSV file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            'citation_key',
            'title',
            'authors',
            'year',
            'journal',
            'doi',
            'url',
            'abstract',
            'keywords',
        ]

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for citation in self.citations:
                row = {
                    'citation_key': citation.citation_key,
                    'title': citation.title,
                    'authors': '; '.join(citation.authors) if citation.authors else '',
                    'year': citation.year if citation.year else '',
                    'journal': citation.journal if citation.journal else '',
                    'doi': citation.doi if citation.doi else '',
                    'url': citation.url if citation.url else '',
                    'abstract': citation.abstract if citation.abstract else '',
                    'keywords': ', '.join(citation.keywords) if citation.keywords else '',
                }
                writer.writerow(row)

        logger.info(f"Wrote CSV to {output_path} ({len(self.citations)} citations)")

    def to_json(self) -> List[Dict]:
        """Export citations as list of dictionaries"""
        return [c.to_dict() for c in self.citations]

    def __len__(self) -> int:
        """Get number of citations"""
        return len(self.citations)

    def __iter__(self):
        """Iterate over citations"""
        return iter(self.citations)


# Convenience functions
def write_bibtex(citations: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write citations to BibTeX file.

    Args:
        citations: List of citation dictionaries
        output_path: Path to write BibTeX file

    Raises:
        ImportError: If bibtexparser not installed
    """
    manager = CitationManager()
    for citation_data in citations:
        manager.add_from_dict(citation_data)

    manager.to_bibtex(output_path)


def write_csv(citations: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write citations to CSV file.

    Args:
        citations: List of citation dictionaries
        output_path: Path to write CSV file
    """
    manager = CitationManager()
    for citation_data in citations:
        manager.add_from_dict(citation_data)

    manager.to_csv(output_path)


def format_apa(citation: Citation) -> str:
    """
    Format citation in APA style.

    Args:
        citation: Citation object

    Returns:
        APA-formatted citation string

    Example:
        >>> c = Citation(title="Test", authors=["Smith, J."], year=2023)
        >>> format_apa(c)
        'Smith, J. (2023). Test.'
    """
    parts = []

    # Authors
    if citation.authors:
        if len(citation.authors) == 1:
            parts.append(citation.authors[0])
        elif len(citation.authors) == 2:
            parts.append(f"{citation.authors[0]} & {citation.authors[1]}")
        else:
            parts.append(f"{citation.authors[0]} et al.")

    # Year
    year_str = f"({citation.year})" if citation.year else "(n.d.)"
    parts.append(year_str)

    # Title
    parts.append(f"{citation.title}.")

    # Journal
    if citation.journal:
        journal_part = f"*{citation.journal}*"
        parts.append(journal_part)

    # DOI or URL
    if citation.doi:
        parts.append(f"https://doi.org/{citation.doi}")
    elif citation.url:
        parts.append(citation.url)

    return ' '.join(parts)


def format_mla(citation: Citation) -> str:
    """
    Format citation in MLA style.

    Args:
        citation: Citation object

    Returns:
        MLA-formatted citation string

    Example:
        >>> c = Citation(title="Test Article", authors=["Smith, John"], year=2023)
        >>> format_mla(c)
        'Smith, John. "Test Article." 2023.'
    """
    parts = []

    # Authors (Last, First)
    if citation.authors:
        parts.append(f"{citation.authors[0]}.")

    # Title (in quotes)
    parts.append(f'"{citation.title}."')

    # Journal (italicized)
    if citation.journal:
        parts.append(f"*{citation.journal}*,")

    # Year
    if citation.year:
        parts.append(f"{citation.year}.")

    # URL
    if citation.url:
        parts.append(citation.url)
    elif citation.doi:
        parts.append(f"https://doi.org/{citation.doi}")

    return ' '.join(parts)


def format_chicago(citation: Citation) -> str:
    """
    Format citation in Chicago style.

    Args:
        citation: Citation object

    Returns:
        Chicago-formatted citation string

    Example:
        >>> c = Citation(title="Test", authors=["Smith, John"], year=2023, journal="Nature")
        >>> format_chicago(c)
        'Smith, John. "Test." *Nature* (2023).'
    """
    parts = []

    # Authors (Last, First)
    if citation.authors:
        parts.append(f"{citation.authors[0]}.")

    # Title (in quotes)
    parts.append(f'"{citation.title}."')

    # Journal (italicized)
    if citation.journal:
        journal_str = f"*{citation.journal}*"
        if citation.year:
            journal_str += f" ({citation.year})"
        parts.append(f"{journal_str}.")

    # DOI
    if citation.doi:
        parts.append(f"https://doi.org/{citation.doi}.")

    return ' '.join(parts)
