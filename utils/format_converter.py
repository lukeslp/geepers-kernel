"""
Format Converter Utility
Convert data between JSON, YAML, TOML, XML, and CSV formats.

Author: Luke Steuber
"""

import json
import csv
import io
import xml.dom.minidom
import logging
from typing import Any, Dict, List, Union, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Optional imports
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    logger.debug("PyYAML not installed - YAML conversion unavailable")

try:
    import toml
    HAS_TOML = True
except ImportError:
    HAS_TOML = False
    logger.debug("toml not installed - TOML conversion unavailable")


@dataclass
class ConversionResult:
    """Result of a format conversion"""
    success: bool
    data: Optional[str] = None
    source_format: Optional[str] = None
    target_format: Optional[str] = None
    error: Optional[str] = None


class FormatConverter:
    """
    Convert data between various formats.

    Supported formats: JSON, YAML, TOML, XML, CSV
    """

    SUPPORTED_FORMATS = ['json', 'yaml', 'toml', 'xml', 'csv']

    @classmethod
    def convert(
        cls,
        data: Union[str, Dict, List],
        target_format: str,
        source_format: str = 'json',
        pretty: bool = True
    ) -> ConversionResult:
        """
        Convert data to the target format.

        Args:
            data: Input data (string, dict, or list)
            target_format: Target format (json, yaml, toml, xml, csv)
            source_format: Source format if data is string (default: json)
            pretty: Use pretty formatting (default: True)

        Returns:
            ConversionResult with converted data
        """
        target_format = target_format.lower()
        source_format = source_format.lower()

        if target_format not in cls.SUPPORTED_FORMATS:
            return ConversionResult(
                success=False,
                error=f"Unsupported target format: {target_format}"
            )

        try:
            # Parse input if string
            if isinstance(data, str):
                parsed = cls._parse(data, source_format)
            else:
                parsed = data

            # Convert to target format
            result = cls._serialize(parsed, target_format, pretty)

            return ConversionResult(
                success=True,
                data=result,
                source_format=source_format,
                target_format=target_format
            )

        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return ConversionResult(
                success=False,
                source_format=source_format,
                target_format=target_format,
                error=str(e)
            )

    @classmethod
    def _parse(cls, data: str, format: str) -> Any:
        """Parse string data from a format"""
        if format == 'json':
            return json.loads(data)
        elif format == 'yaml':
            if not HAS_YAML:
                raise ImportError("PyYAML required for YAML parsing")
            return yaml.safe_load(data)
        elif format == 'toml':
            if not HAS_TOML:
                raise ImportError("toml package required for TOML parsing")
            return toml.loads(data)
        elif format == 'csv':
            return cls._parse_csv(data)
        elif format == 'xml':
            return cls._parse_xml(data)
        else:
            raise ValueError(f"Cannot parse format: {format}")

    @classmethod
    def _serialize(cls, data: Any, format: str, pretty: bool = True) -> str:
        """Serialize data to a format"""
        if format == 'json':
            return cls.to_json(data, pretty)
        elif format == 'yaml':
            return cls.to_yaml(data)
        elif format == 'toml':
            return cls.to_toml(data)
        elif format == 'xml':
            return cls.to_xml(data, pretty)
        elif format == 'csv':
            return cls.to_csv(data)
        else:
            raise ValueError(f"Cannot serialize to format: {format}")

    @staticmethod
    def to_json(data: Any, pretty: bool = True) -> str:
        """Convert data to JSON string"""
        indent = 2 if pretty else None
        return json.dumps(data, indent=indent, ensure_ascii=False)

    @staticmethod
    def to_yaml(data: Any) -> str:
        """Convert data to YAML string"""
        if not HAS_YAML:
            raise ImportError("PyYAML required: pip install pyyaml")
        return yaml.dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)

    @staticmethod
    def to_toml(data: Any) -> str:
        """Convert data to TOML string"""
        if not HAS_TOML:
            raise ImportError("toml package required: pip install toml")
        return toml.dumps(data)

    @staticmethod
    def to_xml(data: Any, pretty: bool = True, root_name: str = "root") -> str:
        """Convert data to XML string"""
        doc = xml.dom.minidom.Document()
        root = doc.createElement(root_name)
        doc.appendChild(root)

        def add_element(parent, key, value):
            if isinstance(value, dict):
                child = doc.createElement(str(key))
                for k, v in value.items():
                    add_element(child, k, v)
                parent.appendChild(child)
            elif isinstance(value, list):
                for item in value:
                    child = doc.createElement(str(key))
                    if isinstance(item, dict):
                        for k, v in item.items():
                            add_element(child, k, v)
                    else:
                        child.appendChild(doc.createTextNode(str(item)))
                    parent.appendChild(child)
            else:
                child = doc.createElement(str(key))
                child.appendChild(doc.createTextNode(str(value) if value is not None else ''))
                parent.appendChild(child)

        if isinstance(data, dict):
            for key, value in data.items():
                add_element(root, key, value)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                add_element(root, 'item', item)
        else:
            root.appendChild(doc.createTextNode(str(data)))

        if pretty:
            return doc.toprettyxml(indent="  ")
        return doc.toxml()

    @staticmethod
    def to_csv(data: Any) -> str:
        """Convert data to CSV string"""
        output = io.StringIO()

        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                # List of dicts - use DictWriter
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            else:
                # List of lists/values
                writer = csv.writer(output)
                for row in data:
                    if isinstance(row, (list, tuple)):
                        writer.writerow(row)
                    else:
                        writer.writerow([row])
        elif isinstance(data, dict):
            # Dict - key/value pairs
            writer = csv.writer(output)
            writer.writerow(['key', 'value'])
            for k, v in data.items():
                writer.writerow([k, v])
        else:
            output.write(str(data))

        return output.getvalue()

    @staticmethod
    def _parse_csv(data: str) -> List:
        """Parse CSV string to list"""
        reader = csv.reader(io.StringIO(data))
        rows = list(reader)

        if len(rows) < 2:
            return rows

        # Try to detect if first row is header
        header = rows[0]
        if all(isinstance(h, str) and not h.replace('.', '').replace('-', '').isdigit() for h in header):
            # Likely a header row - return as list of dicts
            return [dict(zip(header, row)) for row in rows[1:]]
        return rows

    @staticmethod
    def _parse_xml(data: str) -> Dict:
        """Parse XML string to dict (simplified)"""
        doc = xml.dom.minidom.parseString(data)

        def element_to_dict(element):
            result = {}
            for child in element.childNodes:
                if child.nodeType == child.ELEMENT_NODE:
                    key = child.tagName
                    if child.childNodes and child.childNodes[0].nodeType == child.TEXT_NODE:
                        value = child.childNodes[0].data.strip()
                    else:
                        value = element_to_dict(child)

                    if key in result:
                        if not isinstance(result[key], list):
                            result[key] = [result[key]]
                        result[key].append(value)
                    else:
                        result[key] = value
            return result

        root = doc.documentElement
        return {root.tagName: element_to_dict(root)}


# Convenience functions
def json_to_yaml(data: Union[str, Dict, List]) -> str:
    """Convert JSON to YAML"""
    result = FormatConverter.convert(data, 'yaml', 'json')
    if not result.success:
        raise ValueError(result.error)
    return result.data

def json_to_xml(data: Union[str, Dict, List]) -> str:
    """Convert JSON to XML"""
    result = FormatConverter.convert(data, 'xml', 'json')
    if not result.success:
        raise ValueError(result.error)
    return result.data

def json_to_csv(data: Union[str, Dict, List]) -> str:
    """Convert JSON to CSV"""
    result = FormatConverter.convert(data, 'csv', 'json')
    if not result.success:
        raise ValueError(result.error)
    return result.data

def yaml_to_json(data: str) -> str:
    """Convert YAML to JSON"""
    result = FormatConverter.convert(data, 'json', 'yaml')
    if not result.success:
        raise ValueError(result.error)
    return result.data

def csv_to_json(data: str) -> str:
    """Convert CSV to JSON"""
    result = FormatConverter.convert(data, 'json', 'csv')
    if not result.success:
        raise ValueError(result.error)
    return result.data
