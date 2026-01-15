"""
Tests for document parsing utilities.
"""
import tempfile
from pathlib import Path
from shared.utils.document_parsers import (
    FileParser,
    ParseResult,
    parse_file,
    get_supported_extensions,
    is_supported_file,
    get_file_type
)


class TestParseResult:
    """Test ParseResult dataclass."""

    def test_parse_result_success(self):
        """Test successful ParseResult."""
        result = ParseResult(
            content="File content",
            metadata={"file_size": 100},
            success=True
        )

        assert result.success is True
        assert result.content == "File content"
        assert result.error is None

    def test_parse_result_error(self):
        """Test ParseResult with error."""
        result = ParseResult(
            content="",
            metadata={},
            success=False,
            error="File not found"
        )

        assert result.success is False
        assert result.error == "File not found"


class TestFileParser:
    """Test FileParser class."""

    def test_get_supported_extensions(self):
        """Test getting all supported extensions."""
        extensions = FileParser.get_supported_extensions()

        assert len(extensions) > 50
        assert '.txt' in extensions
        assert '.py' in extensions
        assert '.pdf' in extensions
        assert '.csv' in extensions

    def test_is_supported(self):
        """Test file support detection."""
        assert FileParser.is_supported(Path("test.txt")) is True
        assert FileParser.is_supported(Path("test.py")) is True
        assert FileParser.is_supported(Path("test.pdf")) is True
        assert FileParser.is_supported(Path("test.unknown")) is False

    def test_get_file_type(self):
        """Test file type categorization."""
        assert FileParser.get_file_type(Path("test.txt")) == "text"
        assert FileParser.get_file_type(Path("script.py")) == "code"
        assert FileParser.get_file_type(Path("doc.pdf")) == "document"
        assert FileParser.get_file_type(Path("data.csv")) == "data"
        assert FileParser.get_file_type(Path("page.html")) == "web"
        assert FileParser.get_file_type(Path("sheet.xlsx")) == "spreadsheet"
        assert FileParser.get_file_type(Path("notebook.ipynb")) == "notebook"
        assert FileParser.get_file_type(Path("mail.eml")) == "email"
        assert FileParser.get_file_type(Path("archive.zip")) == "archive"
        assert FileParser.get_file_type(Path("app.conf")) == "config"

    def test_parse_nonexistent_file(self):
        """Test parsing non-existent file."""
        parser = FileParser()
        result = parser.parse_file(Path("/nonexistent/file.txt"))

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_parse_text_file(self):
        """Test parsing text file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test file.\nLine 2.\nLine 3.")
            temp_path = Path(f.name)

        try:
            parser = FileParser()
            result = parser.parse_file(temp_path)

            assert result.success is True
            assert "test file" in result.content
            assert result.metadata['file_type'] == 'text'
            assert result.metadata['lines'] == 3
        finally:
            temp_path.unlink()

    def test_parse_json_file(self):
        """Test parsing JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"name": "test", "value": 42}')
            temp_path = Path(f.name)

        try:
            parser = FileParser()
            result = parser.parse_file(temp_path)

            assert result.success is True
            assert "test" in result.content
            assert "42" in result.content
            assert result.metadata['json_type'] == 'dict'
        finally:
            temp_path.unlink()

    def test_parse_csv_file(self):
        """Test parsing CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Name,Age,City\nAlice,30,NYC\nBob,25,LA")
            temp_path = Path(f.name)

        try:
            parser = FileParser()
            result = parser.parse_file(temp_path)

            assert result.success is True
            assert "Alice" in result.content
            assert "NYC" in result.content
            assert result.metadata['rows'] == 2
        finally:
            temp_path.unlink()

    def test_clean_text(self):
        """Test text cleaning."""
        parser = FileParser()

        # Test excessive whitespace removal
        text = "Too    many     spaces"
        cleaned = parser._clean_text(text)
        assert "  " not in cleaned

        # Test line ending normalization
        text = "Line1\r\nLine2\rLine3\n"
        cleaned = parser._clean_text(text)
        assert "\r" not in cleaned


class TestFunctionalInterface:
    """Test functional interface convenience functions."""

    def test_parse_file_function(self):
        """Test parse_file convenience function."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_path = Path(f.name)

        try:
            result = parse_file(temp_path)
            assert result.success is True
            assert "Test content" in result.content
        finally:
            temp_path.unlink()

    def test_get_supported_extensions_function(self):
        """Test get_supported_extensions convenience function."""
        extensions = get_supported_extensions()
        assert len(extensions) > 0
        assert isinstance(extensions, set)

    def test_is_supported_file_function(self):
        """Test is_supported_file convenience function."""
        assert is_supported_file(Path("test.txt")) is True
        assert is_supported_file(Path("test.unknown")) is False

    def test_get_file_type_function(self):
        """Test get_file_type convenience function."""
        assert get_file_type(Path("test.txt")) == "text"
        assert get_file_type(Path("script.py")) == "code"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_file(self):
        """Test parsing empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = Path(f.name)

        try:
            parser = FileParser()
            result = parser.parse_file(temp_path)

            assert result.success is True
            assert result.content == ""
        finally:
            temp_path.unlink()

    def test_large_csv_truncation(self):
        """Test CSV truncation for very large files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            # Write header
            f.write("Col1,Col2,Col3\n")
            # Write many rows (more than 10000)
            for i in range(15000):
                f.write(f"{i},data,value\n")
            temp_path = Path(f.name)

        try:
            parser = FileParser()
            result = parser.parse_file(temp_path)

            assert result.success is True
            assert "truncated" in result.content.lower()
        finally:
            temp_path.unlink()

    def test_invalid_encoding(self):
        """Test handling of files with various encodings."""
        # Create file with Latin-1 encoding
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            f.write("Café résumé".encode('latin-1'))
            temp_path = Path(f.name)

        try:
            parser = FileParser()
            result = parser.parse_file(temp_path)

            # Should succeed with encoding detection
            assert result.success is True
            assert result.content != ""
        finally:
            temp_path.unlink()

    def test_jsonl_file(self):
        """Test parsing JSONL (line-delimited JSON) file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": 1, "text": "first"}\n')
            f.write('{"id": 2, "text": "second"}\n')
            temp_path = Path(f.name)

        try:
            parser = FileParser()
            result = parser.parse_file(temp_path)

            assert result.success is True
            assert "first" in result.content
            assert "second" in result.content
        finally:
            temp_path.unlink()
