"""
Snippet for academic research APIs.
Contains endpoints for querying various academic search services.
"""

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
import logging
import requests
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create blueprint
research_bp = Blueprint('research', __name__)

# API URLs
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_API_URL = "http://export.arxiv.org/api/query"
PUBMED_API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# Common headers
HEADERS = {
    "User-Agent": "CaminaAPI/1.0 (https://github.com/coolhand/camina-chat; api@assisted.space)"
}

@research_bp.route('/semantic-scholar', methods=["GET", "OPTIONS", "POST"])
@cross_origin()
def semantic_scholar_search():
    """
    Search academic papers using Semantic Scholar.
    
    Query parameters (GET) or JSON body (POST):
    - query: The search term to look up (required)
    - limit: Max number of papers to return (default: 10)
    - fields: Fields to include in response (default: "url,abstract,authors,title,venue,year,publicationTypes,tldr")
    - fieldsOfStudy: Filter by specific field(s)
    - year: Filter by publication year
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({"allowed_methods": ["GET", "POST", "OPTIONS"]})
        return response
    
    try:
        # Get parameters from either query string (GET) or JSON body (POST)
        if request.method == "GET":
            query = request.args.get("query")
            limit = int(request.args.get("limit", "10"))
            fields = request.args.get("fields", "url,abstract,authors,title,venue,year,publicationTypes,tldr")
            fields_of_study = request.args.get("fieldsOfStudy")
            year = request.args.get("year")
        else:  # POST
            data = request.get_json() or {}
            query = data.get("query")
            limit = int(data.get("limit", 10))
            fields = data.get("fields", "url,abstract,authors,title,venue,year,publicationTypes,tldr")
            fields_of_study = data.get("fieldsOfStudy")
            year = data.get("year")
        
        # Validate required parameters
        if not query:
            logger.error("Missing required parameter: query")
            return jsonify({"error": "Missing required parameter: query"}), 400
        
        logger.info(f"Semantic Scholar search: query={query}, limit={limit}")
        
        # Prepare parameters
        params = {
            "query": query,
            "limit": limit,
            "fields": fields
        }
        
        # Add optional filters
        if fields_of_study:
            params["fieldsOfStudy"] = fields_of_study
            
        if year:
            params["year"] = year
            
        # Perform the search
        response = requests.get(SEMANTIC_SCHOLAR_URL, params=params, headers=HEADERS)
        
        if response.status_code != 200:
            logger.error(f"Semantic Scholar API error: {response.status_code} - {response.text}")
            return jsonify({
                "error": "Semantic Scholar API error",
                "status_code": response.status_code,
                "message": response.text
            }), response.status_code
            
        # Parse the results
        results = response.json()
        
        # Return the results
        return jsonify({
            "query": query,
            "results": results.get("data", []),
            "count": len(results.get("data", [])),
            "total": results.get("total", 0),
            "next_offset": results.get("next", None),
            "offset": results.get("offset", 0)
        })
        
    except ValueError as ve:
        logger.error(f"Value error in semantic_scholar_search: {str(ve)}")
        return jsonify({"error": f"Invalid parameter value: {str(ve)}"}), 400
    except Exception as e:
        logger.error(f"Error in semantic_scholar_search: {str(e)}")
        return jsonify({"error": str(e)}), 500


@research_bp.route('/arxiv', methods=["GET", "OPTIONS", "POST"])
@cross_origin()
def arxiv_search():
    """
    Search academic papers on arXiv.
    
    Query parameters (GET) or JSON body (POST):
    - query: The search term to look up (required)
    - max_results: Maximum number of results to return (default: 10)
    - sort_by: Sorting criteria (default: "relevance")
    - sort_order: Sorting order (default: "descending")
    - category: Filter by arXiv category
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({"allowed_methods": ["GET", "POST", "OPTIONS"]})
        return response
    
    try:
        # Get parameters from either query string (GET) or JSON body (POST)
        if request.method == "GET":
            query = request.args.get("query")
            max_results = int(request.args.get("max_results", "10"))
            sort_by = request.args.get("sort_by", "relevance")
            sort_order = request.args.get("sort_order", "descending")
            category = request.args.get("category")
        else:  # POST
            data = request.get_json() or {}
            query = data.get("query")
            max_results = int(data.get("max_results", 10))
            sort_by = data.get("sort_by", "relevance")
            sort_order = data.get("sort_order", "descending")
            category = data.get("category")
        
        # Validate required parameters
        if not query:
            logger.error("Missing required parameter: query")
            return jsonify({"error": "Missing required parameter: query"}), 400
        
        logger.info(f"arXiv search: query={query}, max_results={max_results}")
        
        # Prepare parameters
        if category:
            search_query = f"cat:{category} AND all:{query}"
        else:
            search_query = f"all:{query}"
            
        params = {
            "search_query": search_query,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }
        
        # Perform the search
        response = requests.get(ARXIV_API_URL, params=params, headers=HEADERS)
        
        if response.status_code != 200:
            logger.error(f"arXiv API error: {response.status_code} - {response.text}")
            return jsonify({
                "error": "arXiv API error",
                "status_code": response.status_code,
                "message": response.text
            }), response.status_code
            
        # Parse the XML response
        root = ET.fromstring(response.content)
        
        # Extract namespace
        ns = {"atom": "http://www.w3.org/2005/Atom",
              "arxiv": "http://arxiv.org/schemas/atom"}
        
        # Extract results
        entries = root.findall("atom:entry", ns)
        results = []
        
        for entry in entries:
            # Extract basic information
            title = entry.find("atom:title", ns).text.strip()
            summary = entry.find("atom:summary", ns).text.strip()
            published = entry.find("atom:published", ns).text
            
            # Extract authors
            authors = [author.find("atom:name", ns).text for author in entry.findall("atom:author", ns)]
            
            # Extract links
            links = {}
            for link in entry.findall("atom:link", ns):
                link_rel = link.get("rel", "alternate")
                link_href = link.get("href")
                link_title = link.get("title")
                links[link_rel] = {"href": link_href, "title": link_title}
            
            # Extract arXiv specific info
            paper_id = entry.find("atom:id", ns).text.split("/")[-1]
            
            # Extract categories
            categories = []
            for category in entry.findall("atom:category", ns):
                categories.append(category.get("term"))
            
            # Compile result
            result = {
                "id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "published": published,
                "updated": entry.find("atom:updated", ns).text,
                "categories": categories,
                "links": links,
                "pdf_url": next((link["href"] for rel, link in links.items() if rel == "alternate" and link.get("title") == "pdf"), None)
            }
            
            results.append(result)
        
        # Return the results
        return jsonify({
            "query": query,
            "results": results,
            "count": len(results),
            "total_results": int(root.find("atom:totalResults", ns).text) if root.find("atom:totalResults", ns) is not None else len(results)
        })
        
    except ValueError as ve:
        logger.error(f"Value error in arxiv_search: {str(ve)}")
        return jsonify({"error": f"Invalid parameter value: {str(ve)}"}), 400
    except Exception as e:
        logger.error(f"Error in arxiv_search: {str(e)}")
        return jsonify({"error": str(e)}), 500


@research_bp.route('/pubmed', methods=["GET", "OPTIONS", "POST"])
@cross_origin()
def pubmed_search():
    """
    Search medical literature on PubMed.
    
    Query parameters (GET) or JSON body (POST):
    - query: The search term to look up (required)
    - max_results: Maximum number of results to return (default: 10)
    - sort: Sort by (default: "relevance")
    - date_range: Filter by date range (e.g., "2020/01/01:2023/01/01")
    - journal: Filter by journal
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({"allowed_methods": ["GET", "POST", "OPTIONS"]})
        return response
    
    try:
        # Get parameters from either query string (GET) or JSON body (POST)
        if request.method == "GET":
            query = request.args.get("query")
            max_results = int(request.args.get("max_results", "10"))
            sort = request.args.get("sort", "relevance")
            date_range = request.args.get("date_range")
            journal = request.args.get("journal")
        else:  # POST
            data = request.get_json() or {}
            query = data.get("query")
            max_results = int(data.get("max_results", 10))
            sort = data.get("sort", "relevance")
            date_range = data.get("date_range")
            journal = data.get("journal")
        
        # Validate required parameters
        if not query:
            logger.error("Missing required parameter: query")
            return jsonify({"error": "Missing required parameter: query"}), 400
        
        logger.info(f"PubMed search: query={query}, max_results={max_results}")
        
        # Build search query with filters
        search_query = query
        
        if journal:
            search_query += f" AND {journal}[Journal]"
            
        if date_range:
            search_query += f" AND {date_range}[Date - Publication]"
        
        # Step 1: Search for IDs
        search_params = {
            "db": "pubmed",
            "term": search_query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance" if sort == "relevance" else "pub date"
        }
        
        search_response = requests.get(PUBMED_API_URL, params=search_params, headers=HEADERS)
        
        if search_response.status_code != 200:
            logger.error(f"PubMed API error: {search_response.status_code} - {search_response.text}")
            return jsonify({
                "error": "PubMed API error",
                "status_code": search_response.status_code,
                "message": search_response.text
            }), search_response.status_code
            
        # Parse search results
        search_data = search_response.json()
        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        
        if not id_list:
            logger.info(f"No results found for PubMed query: {query}")
            return jsonify({
                "query": query,
                "results": [],
                "count": 0,
                "total": 0
            })
        
        # Step 2: Get summaries for the IDs
        summary_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json"
        }
        
        summary_response = requests.get(PUBMED_SUMMARY_URL, params=summary_params, headers=HEADERS)
        
        if summary_response.status_code != 200:
            logger.error(f"PubMed Summary API error: {summary_response.status_code} - {summary_response.text}")
            return jsonify({
                "error": "PubMed Summary API error",
                "status_code": summary_response.status_code,
                "message": summary_response.text
            }), summary_response.status_code
            
        # Parse summaries
        summary_data = summary_response.json()
        result_list = summary_data.get("result", {})
        
        # Remove 'uids' from the results
        if "uids" in result_list:
            uids = result_list.pop("uids")
        else:
            uids = id_list
            
        # Format results
        results = []
        for uid in uids:
            if uid in result_list:
                article = result_list[uid]
                
                # Extract authors
                authors = []
                if "authors" in article:
                    for author in article["authors"]:
                        if "name" in author:
                            authors.append(author["name"])
                
                # Format publication date
                pub_date = None
                if "pubdate" in article:
                    try:
                        pub_date = article["pubdate"]
                    except:
                        pub_date = article.get("pubdate", "")
                
                # Extract article details
                result = {
                    "id": uid,
                    "title": article.get("title", ""),
                    "abstract": article.get("abstract", ""),
                    "authors": authors,
                    "journal": article.get("fulljournalname", ""),
                    "publication_date": pub_date,
                    "publication_types": article.get("pubtype", []),
                    "doi": article.get("elocationid", ""),
                    "pmid": uid,
                    "source": "PubMed",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
                }
                
                results.append(result)
        
        # Return the results
        return jsonify({
            "query": query,
            "results": results,
            "count": len(results),
            "total": int(search_data.get("esearchresult", {}).get("count", 0))
        })
        
    except ValueError as ve:
        logger.error(f"Value error in pubmed_search: {str(ve)}")
        return jsonify({"error": f"Invalid parameter value: {str(ve)}"}), 400
    except Exception as e:
        logger.error(f"Error in pubmed_search: {str(e)}")
        return jsonify({"error": str(e)}), 500 