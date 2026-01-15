"""
Tests for secure session management.

Tests encryption, decryption, and file handling for session storage.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from monarchmoney.secure_session import SecureSessionManager


class TestSecureSessionManager:
    """Test secure session storage."""

    def setup_method(self):
        """Create temporary directory for session files."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = SecureSessionManager(session_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test manager initializes correctly."""
        assert self.manager.session_dir == Path(self.temp_dir)
        assert self.manager.session_file == Path(self.temp_dir) / "session.enc"
        assert self.manager.key_file == Path(self.temp_dir) / "session.key"
        assert self.manager._cipher is not None

    def test_directory_created(self):
        """Test session directory is created."""
        assert Path(self.temp_dir).exists()
        assert Path(self.temp_dir).is_dir()

    def test_key_file_created(self):
        """Test encryption key file is created."""
        assert self.manager.key_file.exists()
        # Key file should have restricted permissions (600)
        # Note: This test might not work on Windows

    def test_save_and_load_session(self):
        """Test saving and loading session data."""
        session_data = {"token": "test_token_123", "user_id": "user_456"}

        # Save session
        self.manager.save_session(session_data)
        assert self.manager.session_file.exists()

        # Load session
        loaded_data = self.manager.load_session()
        assert loaded_data == session_data

    def test_session_exists(self):
        """Test session_exists method."""
        assert not self.manager.session_exists()

        # Save a session
        self.manager.save_session({"token": "test"})
        assert self.manager.session_exists()

    def test_delete_session(self):
        """Test deleting session file."""
        # Create session
        self.manager.save_session({"token": "test"})
        assert self.manager.session_exists()

        # Delete session
        self.manager.delete_session()
        assert not self.manager.session_exists()

    def test_load_nonexistent_session(self):
        """Test loading session when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            self.manager.load_session()

    def test_encrypted_storage(self):
        """Test that session data is actually encrypted."""
        session_data = {"token": "secret_token_xyz"}
        self.manager.save_session(session_data)

        # Read raw file contents
        with open(self.manager.session_file, "rb") as f:
            encrypted_content = f.read()

        # Raw content should NOT contain the plaintext token
        assert b"secret_token_xyz" not in encrypted_content

        # And should be different from JSON
        json_bytes = json.dumps(session_data).encode('utf-8')
        assert encrypted_content != json_bytes

    def test_multiple_save_loads(self):
        """Test multiple save/load cycles."""
        for i in range(5):
            session_data = {"token": f"token_{i}", "iteration": i}
            self.manager.save_session(session_data)
            loaded_data = self.manager.load_session()
            assert loaded_data == session_data

    def test_different_managers_same_key(self):
        """Test that different managers with same directory use same key."""
        session_data = {"token": "shared_token"}

        # Save with first manager
        self.manager.save_session(session_data)

        # Load with second manager (same directory)
        manager2 = SecureSessionManager(session_dir=self.temp_dir)
        loaded_data = manager2.load_session()

        assert loaded_data == session_data

    def test_complex_session_data(self):
        """Test saving complex nested session data."""
        session_data = {
            "token": "complex_token",
            "user": {
                "id": "123",
                "email": "test@example.com",
                "preferences": {
                    "theme": "dark",
                    "notifications": True
                }
            },
            "expires_at": "2026-12-31T23:59:59Z"
        }

        self.manager.save_session(session_data)
        loaded_data = self.manager.load_session()

        assert loaded_data == session_data
        assert loaded_data["user"]["preferences"]["theme"] == "dark"
