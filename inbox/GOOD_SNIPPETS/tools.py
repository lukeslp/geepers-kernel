"""
Snippet for utility tools and AI function calling.
Contains endpoints for executing various tools like archive retrieval, code execution, etc.
"""

from flask import Blueprint, request, jsonify
import logging
import json
import requests
import tempfile
import os
import sys
from typing import Dict, Any, List, Optional
import yaml
import toml
import urllib.parse
import xml.dom.minidom
import csv
import io
import asyncio

# Logger for this module
logger = logging.getLogger(__name__)

# Blueprint for tools routes
tools_bp = Blueprint('tools', __name__)

# Configuration for API keys
API_KEYS = {
    'wolframalpha': os.environ.get('WOLFRAMALPHA_APP_ID', '')
}


@tools_bp.route('/call', methods=['POST'])
def call_tool():
    """Call a tool/function with an AI provider."""
    data = request.json or {}
    
    # Get required parameters
    provider_name = data.get('provider', 'anthropic')
    model = data.get('model')
    prompt = data.get('prompt', '')
    tools = data.get('tools', [])
    
    # Validate parameters
    if not model:
        return jsonify({"error": "Model parameter is required"}), 400
    
    if not tools or not isinstance(tools, list):
        return jsonify({"error": "Tools parameter must be a non-empty array"}), 400
    
    # Optional parameters
    conversation_id = data.get('conversation_id')
    user_id = data.get('user_id', 'default_user')
    tool_choice = data.get('tool_choice', 'auto')
    
    logger.info(f"Tool call request: provider={provider_name}, model={model}, tools={len(tools)}")
    
    try:
        # This is a placeholder - in v3 we'll implement provider-agnostic tool calling
        return jsonify({
            "success": False,
            "message": "Tool calling not implemented in this snippet version"
        }), 501
    except Exception as e:
        logger.error(f"Error calling tool: {str(e)}")
        return jsonify({"error": str(e)}), 500


@tools_bp.route('/archive', methods=['GET', 'POST'])
def archive_retrieval():
    """
    Retrieve archived versions of web pages using various archive services.
    
    This endpoint proxies requests to archive services like the Wayback Machine,
    Archive.is, and Memento Aggregator to retrieve archived versions of web pages.
    
    Query Parameters (GET) or JSON body (POST):
        - url: The URL to find an archived version for (required)
        - provider: The archive provider to use (wayback, archiveis, memento, 12ft)
                   Default is 'wayback'
        - capture: Whether to capture a new snapshot (for archiveis only)
                  Default is False
    
    Returns:
        JSON object with the archived URL and metadata
    """
    # Define a User-Agent string to mimic a real browser
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/90.0.4430.93 Safari/537.36"
    )
    
    # Get parameters from request
    if request.method == 'POST':
        data = request.json or {}
        target_url = data.get('url')
        provider = data.get('provider', 'wayback')
        capture = data.get('capture', False)
    else:
        target_url = request.args.get('url')
        provider = request.args.get('provider', 'wayback')
        capture = request.args.get('capture', 'false').lower() in ['true', '1', 't', 'yes']
    
    if not target_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        from datetime import datetime
        
        result = {
            "original_url": target_url,
            "provider": provider,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "archived_url": None,
            "message": ""
        }
        
        if provider == "wayback":
            try:
                # Import here to avoid dependency issues if not installed
                from waybackpy import Url
                
                try:
                    # Create a Url object
                    url_obj = Url(target_url, USER_AGENT)
                    
                    # Get the newest snapshot as a string
                    archived_url = str(url_obj.newest())
                    
                    # Get the timestamp as a string
                    try:
                        # In waybackpy 2.4.4, timestamp might be an attribute or a method
                        timestamp = url_obj.timestamp
                        if callable(timestamp):
                            timestamp = timestamp()
                        
                        # Convert datetime to string for JSON serialization
                        if hasattr(timestamp, 'isoformat'):
                            timestamp = timestamp.isoformat()
                        else:
                            timestamp = str(timestamp)
                    except Exception as e:
                        # If there's any error getting the timestamp, use the current time
                        timestamp = datetime.now().isoformat()
                        logger.warning(f"Error getting timestamp from Wayback Machine: {str(e)}")
                    
                    # Create a new result dictionary with only serializable data
                    result = {
                        "original_url": target_url,
                        "provider": provider,
                        "timestamp": timestamp,
                        "success": True,
                        "archived_url": archived_url,
                        "message": "Successfully retrieved the most recent snapshot from the Wayback Machine"
                    }
                except Exception as e:
                    result["message"] = f"Error processing Wayback Machine response: {str(e)}"
                    logger.error(f"Error processing Wayback Machine response: {str(e)}")
            
            except Exception as e:
                result["message"] = f"Wayback Machine API error: {str(e)}"
                logger.error(f"Wayback Machine API error: {str(e)}")
        
        elif provider == "archiveis":
            try:
                # Import here to avoid dependency issues if not installed
                import archiveis
                
                if capture:
                    # Capture a new snapshot
                    archived_url = archiveis.capture(target_url)
                    result["archived_url"] = archived_url
                    result["success"] = True
                    result["message"] = "Successfully captured a new snapshot with Archive.is"
                else:
                    # Try to find an existing snapshot
                    # Note: Archive.is doesn't have a direct API for retrieving existing snapshots
                    # This is a workaround that might not always work
                    archived_url = f"https://archive.is/{target_url}"
                    
                    # Check if the archive exists by making a HEAD request
                    response = requests.head(archived_url, headers={"User-Agent": USER_AGENT}, timeout=10)
                    
                    if response.status_code == 200:
                        result["archived_url"] = archived_url
                        result["success"] = True
                        result["message"] = "Found an existing snapshot on Archive.is"
                    else:
                        result["message"] = "No existing snapshot found on Archive.is. Set 'capture=true' to create a new one."
            
            except Exception as e:
                result["message"] = f"Archive.is error: {str(e)}"
                logger.error(f"Archive.is error: {str(e)}")
        
        elif provider == "memento":
            try:
                encoded_url = urllib.parse.quote(target_url, safe="")
                # The correct URL format for Memento Aggregator
                # Make sure the URL is properly formatted with http:// or https:// prefix
                if not target_url.startswith(('http://', 'https://')):
                    target_url = 'http://' + target_url
                
                # Use the full URL format that Memento expects
                api_url = f"http://timetravel.mementoweb.org/timemap/json/{target_url}"
                
                response = requests.get(api_url, headers={"User-Agent": USER_AGENT}, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                mementos = data.get("mementos", {}).get("list", [])
                
                if mementos:
                    # Get the most recent memento
                    latest_memento = mementos[-1]
                    result["archived_url"] = latest_memento.get("uri")
                    result["timestamp"] = latest_memento.get("datetime")
                    result["success"] = True
                    result["message"] = "Successfully retrieved the most recent snapshot from Memento Aggregator"
                    
                    # Add additional metadata
                    result["total_snapshots"] = len(mementos)
                    result["first_snapshot_date"] = mementos[0].get("datetime") if mementos else None
                    result["last_snapshot_date"] = latest_memento.get("datetime") if mementos else None
                else:
                    result["message"] = "No snapshots found via Memento Aggregator"
            
            except Exception as e:
                result["message"] = f"Memento Aggregator error: {str(e)}"
                logger.error(f"Memento Aggregator error: {str(e)}")
        
        elif provider == "12ft":
            try:
                # 12ft.io simply prepends the URL with 12ft.io/
                archived_url = f"https://12ft.io/{target_url}"
                
                # 12ft.io often returns a 302 redirect, which is normal and expected
                # We'll consider both 200 and 302 as success
                response = requests.head(archived_url, headers={"User-Agent": USER_AGENT}, timeout=10, allow_redirects=False)
                
                if response.status_code in [200, 302]:
                    result["archived_url"] = archived_url
                    result["success"] = True
                    result["message"] = "Successfully created a 12ft.io link to bypass paywalls and remove distractions"
                else:
                    result["message"] = f"12ft.io service returned unexpected status code: {response.status_code}"
            
            except Exception as e:
                result["message"] = f"12ft.io error: {str(e)}"
                logger.error(f"12ft.io error: {str(e)}")
        
        else:
            return jsonify({"error": f"Unknown provider: {provider}"}), 400
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in archive retrieval: {str(e)}")
        return jsonify({"error": str(e)}), 500


@tools_bp.route('/execute/code', methods=['POST'])
def execute_code():
    """
    Execute Python code in a restricted environment.
    
    This endpoint safely executes Python code in a restricted sandbox.
    
    JSON body:
        - code: The Python code to execute (required)
    
    Returns:
        JSON object with the execution results
    """
    # Get parameters from request
    data = request.json or {}
    code = data.get('code')
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    try:
        # Create a minimal code executor implementation
        class Tools:
            """Tools for running code in a restricted environment"""
            
            def __init__(self):
                self.python_path = sys.executable
                self.temp_dir = tempfile.gettempdir()
                
            async def run_python_code(self, code: str) -> str:
                """Run Python code in a restricted environment"""
                try:
                    # Create a temporary file
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                        f.write(code)
                        temp_path = f.name
                    
                    # Run with restricted permissions
                    process = await asyncio.create_subprocess_exec(
                        self.python_path,
                        temp_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=self.temp_dir,
                        env={
                            'PATH': os.environ.get('PATH', ''),
                            'PYTHONPATH': '',  # Restrict imports
                            'PYTHONHOME': '',  # Restrict Python environment
                        }
                    )
                    
                    stdout, stderr = await process.communicate()
                    os.unlink(temp_path)  # Clean up temp file
                    
                    output = stdout.decode() if stdout else ''
                    error = stderr.decode() if stderr else ''
                    
                    if error:
                        return f"Error:\n{error}"
                    return output if output else "No output"
                    
                except Exception as e:
                    return f"Error running Python code: {str(e)}"
        
        # Execute the code
        tool = Tools()
        result = asyncio.run(tool.run_python_code(code))
        
        return jsonify({
            "success": True, 
            "result": result,
            "code": code
        })
        
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "code": code
        }), 500


@tools_bp.route('/process/format', methods=['POST'])
def format_data():
    """
    Convert data between JSON and other formats (YAML, TOML, XML, CSV).
    
    JSON body:
        - data: The data to convert (required)
        - target_format: The target format (json, yaml, toml, xml, csv)
        - style: Output style (pretty, compact, single_line)
    
    Returns:
        JSON object with the converted data
    """
    # Get parameters from request
    data = request.json or {}
    input_data = data.get('data')
    target_format = data.get('target_format', 'json')
    style = data.get('style', 'pretty')
    
    if not input_data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        # Convert input to Python object if it's a string
        if isinstance(input_data, str):
            try:
                input_data = json.loads(input_data)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON data provided"}), 400
        
        # Define conversion functions
        def _convert_to_json(data, indent=None):
            return json.dumps(data, indent=indent)
            
        def _convert_to_yaml(data):
            try:
                return yaml.dump(data, sort_keys=False, allow_unicode=True)
            except Exception as e:
                logger.error(f"Error in YAML conversion: {str(e)}")
                # Fallback to a simple conversion if PyYAML methods fail
                result = ""
                if isinstance(data, dict):
                    for k, v in data.items():
                        result += f"{k}: {v}\n"
                return result
            
        def _convert_to_toml(data):
            return toml.dumps(data)
            
        def _convert_to_xml(data):
            def dict_to_xml(data, root_name="root"):
                doc = xml.dom.minidom.Document()
                root = doc.createElement(root_name)
                doc.appendChild(root)
                
                def add_element(parent, key, value):
                    if isinstance(value, dict):
                        child = doc.createElement(key)
                        for k, v in value.items():
                            add_element(child, k, v)
                        parent.appendChild(child)
                    elif isinstance(value, list):
                        for item in value:
                            child = doc.createElement(key)
                            if isinstance(item, dict):
                                for k, v in item.items():
                                    add_element(child, k, v)
                            else:
                                child.appendChild(doc.createTextNode(str(item)))
                            parent.appendChild(child)
                    else:
                        child = doc.createElement(key)
                        child.appendChild(doc.createTextNode(str(value)))
                        parent.appendChild(child)
                
                for key, value in data.items():
                    add_element(root, key, value)
                
                return doc.toprettyxml(indent="  ")
            
            return dict_to_xml(data)
            
        def _convert_to_csv(data):
            output = io.StringIO()
            writer = None
            
            if isinstance(data, list):
                if data and isinstance(data[0], dict):
                    writer = csv.DictWriter(output, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                else:
                    writer = csv.writer(output)
                    writer.writerows(data)
            elif isinstance(data, dict):
                writer = csv.writer(output)
                writer.writerows([[k, v] for k, v in data.items()])
            
            return output.getvalue()
        
        # Perform the conversion
        if target_format == "json":
            indent = 2 if style == "pretty" else None
            result = _convert_to_json(input_data, indent)
        elif target_format == "yaml":
            result = _convert_to_yaml(input_data)
        elif target_format == "toml":
            result = _convert_to_toml(input_data)
        elif target_format == "xml":
            result = _convert_to_xml(input_data)
        elif target_format == "csv":
            result = _convert_to_csv(input_data)
        else:
            return jsonify({"error": f"Unsupported format: {target_format}"}), 400
        
        # Apply style
        if style == "single_line" and target_format != "csv":
            result = result.replace("\n", " ").strip()
        
        return jsonify({
            "success": True,
            "result": result,
            "original_data": input_data,
            "target_format": target_format,
            "style": style
        })
        
    except Exception as e:
        logger.error(f"Error formatting data: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "data": input_data
        }), 500


@tools_bp.route('/wolframalpha/query', methods=['POST'])
def wolfram_alpha_query():
    """
    Query the Wolfram Alpha API to solve problems or answer questions.
    
    Required parameters:
    - query: The question or problem to solve with Wolfram Alpha
    
    Optional parameters:
    - app_id: The Wolfram Alpha API key (if not provided, uses environment variable)
    - simple: Boolean to determine if the simple API should be used (defaults to False)
    """
    data = request.json or {}
    
    # Get required parameters
    query = data.get('query')
    
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
    
    # Get optional parameters
    app_id = data.get('app_id', API_KEYS['wolframalpha'])
    simple = data.get('simple', False)
    
    if not app_id:
        return jsonify({"error": "Wolfram Alpha API key is required. Please provide it via app_id parameter or set the WOLFRAMALPHA_APP_ID environment variable."}), 400
    
    try:
        if simple:
            # Use the simple API (returns an image URL)
            base_url = "http://api.wolframalpha.com/v1/simple"
            params = {"i": query, "appid": app_id}
            result_url = f"{base_url}?{urllib.parse.urlencode(params)}"
            
            return jsonify({
                "success": True,
                "result_type": "image",
                "result_url": result_url,
                "query": query
            })
        else:
            # Use the short answer API
            base_url = "http://api.wolframalpha.com/v1/result"
            params = {
                "i": query,
                "appid": app_id,
                "format": "plaintext",
            }
            
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            
            return jsonify({
                "success": True,
                "result_type": "text",
                "result": response.text,
                "query": query
            })
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying Wolfram Alpha: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "query": query
        }), 500 