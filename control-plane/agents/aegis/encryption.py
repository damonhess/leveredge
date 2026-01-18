#!/usr/bin/env python3
"""
AEGIS Encryption Module
Manages encryption/decryption of credential values using Fernet (AES-256)
"""

from cryptography.fernet import Fernet
import os
import hashlib

MASTER_KEY_PATH = "/opt/leveredge/secrets/aegis_master.key"


class CredentialEncryption:
    """AES-256 encryption for credential values using Fernet (symmetric)"""

    def __init__(self):
        self.fernet = None
        self.key_id = None
        self._init_encryption()

    def _init_encryption(self):
        """Initialize encryption with master key from file"""
        os.makedirs(os.path.dirname(MASTER_KEY_PATH), exist_ok=True)

        if os.path.exists(MASTER_KEY_PATH):
            with open(MASTER_KEY_PATH, 'rb') as f:
                key = f.read()
        else:
            # Generate new key if doesn't exist
            key = Fernet.generate_key()
            with open(MASTER_KEY_PATH, 'wb') as f:
                f.write(key)
            os.chmod(MASTER_KEY_PATH, 0o600)

        self.fernet = Fernet(key)
        self.key_id = hashlib.sha256(key).hexdigest()[:16]

    def encrypt(self, value: str) -> str:
        """Encrypt a credential value"""
        if not value:
            return ""
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt a credential value"""
        if not encrypted_value:
            return ""
        return self.fernet.decrypt(encrypted_value.encode()).decode()

    def get_key_id(self) -> str:
        """Get the current encryption key ID for audit purposes"""
        return self.key_id


# Singleton instance
encryption = CredentialEncryption()
