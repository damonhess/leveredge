"""
Google OAuth2 Authentication Handler for Calendar API
Manages credentials, token refresh, and OAuth flow
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build, Resource

logger = logging.getLogger(__name__)

# OAuth2 scopes required for Calendar access
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
]

# Default paths for credentials
DEFAULT_CREDENTIALS_PATH = Path('/opt/leveredge/integrations/google-calendar/credentials')
CLIENT_SECRETS_FILE = 'client_secrets.json'
TOKEN_FILE = 'token.json'


class GoogleAuthManager:
    """
    Manages Google OAuth2 authentication for Calendar API.
    Handles credential storage, token refresh, and OAuth flow.
    """

    def __init__(
        self,
        credentials_path: Optional[Path] = None,
        client_secrets_file: Optional[str] = None,
        token_file: Optional[str] = None
    ):
        """
        Initialize the auth manager.

        Args:
            credentials_path: Directory to store credentials
            client_secrets_file: Name of client secrets JSON file
            token_file: Name of token storage file
        """
        self.credentials_path = credentials_path or DEFAULT_CREDENTIALS_PATH
        self.client_secrets_file = client_secrets_file or CLIENT_SECRETS_FILE
        self.token_file = token_file or TOKEN_FILE

        # Ensure credentials directory exists
        self.credentials_path.mkdir(parents=True, exist_ok=True)

        self._credentials: Optional[Credentials] = None
        self._service: Optional[Resource] = None

    @property
    def client_secrets_path(self) -> Path:
        """Full path to client secrets file."""
        return self.credentials_path / self.client_secrets_file

    @property
    def token_path(self) -> Path:
        """Full path to token file."""
        return self.credentials_path / self.token_file

    def has_client_secrets(self) -> bool:
        """Check if client secrets file exists."""
        return self.client_secrets_path.exists()

    def has_valid_credentials(self) -> bool:
        """Check if we have valid (or refreshable) credentials."""
        creds = self._load_credentials()
        if not creds:
            return False
        return creds.valid or (creds.expired and creds.refresh_token)

    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from token file."""
        if not self.token_path.exists():
            return None

        try:
            with open(self.token_path, 'r') as f:
                token_data = json.load(f)

            return Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None

    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file."""
        token_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes,
            'expiry': creds.expiry.isoformat() if creds.expiry else None
        }

        with open(self.token_path, 'w') as f:
            json.dump(token_data, f, indent=2)

        # Secure the file
        os.chmod(self.token_path, 0o600)
        logger.info("Credentials saved successfully")

    def get_credentials(self) -> Optional[Credentials]:
        """
        Get valid credentials, refreshing if necessary.

        Returns:
            Valid Credentials object or None if authentication needed
        """
        if self._credentials and self._credentials.valid:
            return self._credentials

        creds = self._load_credentials()

        if creds:
            if creds.valid:
                self._credentials = creds
                return creds

            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self._save_credentials(creds)
                    self._credentials = creds
                    logger.info("Credentials refreshed successfully")
                    return creds
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    return None

        return None

    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> tuple[str, str]:
        """
        Generate OAuth2 authorization URL.

        Args:
            redirect_uri: Callback URL after authorization
            state: Optional state parameter for CSRF protection

        Returns:
            Tuple of (authorization_url, state)
        """
        if not self.has_client_secrets():
            raise ValueError(f"Client secrets not found at {self.client_secrets_path}")

        flow = Flow.from_client_secrets_file(
            str(self.client_secrets_path),
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )

        return authorization_url, state

    def exchange_code(self, code: str, redirect_uri: str) -> Credentials:
        """
        Exchange authorization code for credentials.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect_uri used in authorization request

        Returns:
            Credentials object
        """
        if not self.has_client_secrets():
            raise ValueError(f"Client secrets not found at {self.client_secrets_path}")

        flow = Flow.from_client_secrets_file(
            str(self.client_secrets_path),
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )

        flow.fetch_token(code=code)
        creds = flow.credentials

        self._save_credentials(creds)
        self._credentials = creds

        logger.info("Authorization code exchanged successfully")
        return creds

    def get_calendar_service(self) -> Resource:
        """
        Get authenticated Google Calendar API service.

        Returns:
            Google Calendar API service resource

        Raises:
            ValueError: If no valid credentials available
        """
        if self._service:
            return self._service

        creds = self.get_credentials()
        if not creds:
            raise ValueError("No valid credentials. Please authenticate first.")

        self._service = build('calendar', 'v3', credentials=creds)
        return self._service

    def revoke_credentials(self) -> bool:
        """
        Revoke current credentials and delete token file.

        Returns:
            True if successful, False otherwise
        """
        creds = self.get_credentials()

        if creds:
            try:
                import httpx
                httpx.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': creds.token},
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
            except Exception as e:
                logger.warning(f"Failed to revoke token: {e}")

        # Delete local token file
        if self.token_path.exists():
            self.token_path.unlink()

        self._credentials = None
        self._service = None

        logger.info("Credentials revoked")
        return True

    def get_auth_status(self) -> dict:
        """
        Get current authentication status.

        Returns:
            Dict with authentication status details
        """
        has_secrets = self.has_client_secrets()
        has_token = self.token_path.exists()
        creds = self._load_credentials() if has_token else None

        return {
            'client_secrets_configured': has_secrets,
            'token_exists': has_token,
            'credentials_valid': creds.valid if creds else False,
            'credentials_expired': creds.expired if creds else None,
            'has_refresh_token': bool(creds.refresh_token) if creds else False,
            'expiry': creds.expiry.isoformat() if creds and creds.expiry else None,
            'scopes': list(creds.scopes) if creds and creds.scopes else []
        }


# Singleton instance for application use
_auth_manager: Optional[GoogleAuthManager] = None


def get_auth_manager() -> GoogleAuthManager:
    """Get or create the singleton auth manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = GoogleAuthManager()
    return _auth_manager


def get_calendar_service() -> Resource:
    """Convenience function to get Calendar API service."""
    return get_auth_manager().get_calendar_service()
