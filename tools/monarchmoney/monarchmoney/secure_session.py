"""
Secure session management with encryption for Monarch Money tokens.

This module provides encrypted storage for authentication tokens using
the cryptography library's Fernet symmetric encryption.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional

from cryptography.fernet import Fernet


class SecureSessionManager:
    """
    Manages encrypted session storage for Monarch Money authentication tokens.

    Uses Fernet symmetric encryption to protect session data at rest.
    The encryption key is stored in a separate file with restricted permissions.
    """

    def __init__(self, session_dir: str = ".mm"):
        """
        Initialize the secure session manager.

        Args:
            session_dir: Directory to store session files (default: .mm)
        """
        self.session_dir = Path(session_dir).expanduser()
        self.session_file = self.session_dir / "session.enc"
        self.key_file = self.session_dir / "session.key"

        # Ensure directory exists with restrictive permissions
        self.session_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.session_dir, 0o700)  # Owner read/write/execute only

        # Initialize or load encryption key
        self._cipher = self._get_or_create_cipher()

    def _get_or_create_cipher(self) -> Fernet:
        """
        Get existing cipher or create new one with a fresh key.

        Returns:
            Fernet cipher instance
        """
        if self.key_file.exists():
            # Load existing key
            with open(self.key_file, "rb") as f:
                key = f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)  # Owner read/write only

        return Fernet(key)

    def save_session(self, session_data: Dict[str, str]) -> None:
        """
        Save session data with encryption.

        Args:
            session_data: Dictionary containing session information (e.g., {"token": "..."})
        """
        # Convert to JSON and encrypt
        json_data = json.dumps(session_data).encode('utf-8')
        encrypted_data = self._cipher.encrypt(json_data)

        # Write encrypted data
        with open(self.session_file, "wb") as f:
            f.write(encrypted_data)
        os.chmod(self.session_file, 0o600)  # Owner read/write only

    def load_session(self) -> Dict[str, str]:
        """
        Load and decrypt session data.

        Returns:
            Dictionary containing session information

        Raises:
            FileNotFoundError: If session file doesn't exist
            cryptography.fernet.InvalidToken: If decryption fails
        """
        if not self.session_file.exists():
            raise FileNotFoundError(f"Session file not found: {self.session_file}")

        # Read and decrypt
        with open(self.session_file, "rb") as f:
            encrypted_data = f.read()

        decrypted_data = self._cipher.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode('utf-8'))

    def delete_session(self) -> None:
        """Delete the encrypted session file."""
        if self.session_file.exists():
            self.session_file.unlink()

    def session_exists(self) -> bool:
        """Check if a session file exists."""
        return self.session_file.exists()
