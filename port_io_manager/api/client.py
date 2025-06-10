import requests
import sys
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class PortAPIClient:
    """Base client for interacting with the Port.io API."""
    
    AUTH_URL = "https://api.port.io/v1/auth/access_token"
    BASE_URL = "https://api.port.io/v1"

    def __init__(self, client_id: str, client_secret: str):
        """Initialize the Port.io API client.

        Args:
            client_id: Port.io client ID
            client_secret: Port.io client secret
        """
        if not client_id or not client_secret:
            logger.error("Missing required credentials: PORT_CLIENT_ID and PORT_CLIENT_SECRET must be defined")
            sys.exit(1)

        self._client_id = client_id
        self._client_secret = client_secret
        self._session = requests.Session()
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Port.io API and configure session with access token."""
        payload = {"clientId": self._client_id, "clientSecret": self._client_secret}
        try:
            response = self._session.post(self.AUTH_URL, json=payload)
            response.raise_for_status()
            access_token = response.json()['accessToken']
            self._session.headers.update({
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            })
            logger.info("Successfully authenticated with Port.io API")
        except requests.exceptions.RequestException as e:
            error_details = self._extract_error_details(e)
            logger.error("Failed to authenticate with Port.io API: %s", error_details)
            sys.exit(1)

    def _extract_error_details(self, error: requests.exceptions.RequestException) -> str:
        """Extract detailed error information from API response.

        Args:
            error: The request exception

        Returns:
            Formatted error message with details
        """
        if not hasattr(error, 'response') or not error.response:
            return str(error)

        try:
            error_json = error.response.json()
            if isinstance(error_json, dict):
                # Extract useful fields from the error response
                error_msg = error_json.get('message', '')
                error_code = error_json.get('code', '')
                validation_errors = error_json.get('validationErrors', [])
                
                details = []
                if error_msg:
                    details.append(f"Message: {error_msg}")
                if error_code:
                    details.append(f"Code: {error_code}")
                if validation_errors:
                    details.append("Validation Errors:")
                    for error in validation_errors:
                        details.append(f"  - {error}")
                
                if details:
                    return f"{error.response.status_code} {error.response.reason}: {' | '.join(details)}"
            
            # Fallback to raw JSON if structure is different
            return f"{error.response.status_code} {error.response.reason}: {json.dumps(error_json)}"
        except ValueError:
            # If response is not JSON, return raw text
            return f"{error.response.status_code} {error.response.reason}: {error.response.text}"

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Any:
        """Make a request to the Port.io API.

        Args:
            method: HTTP method to use
            endpoint: API endpoint to call
            data: Optional request payload

        Returns:
            API response data or None if request failed
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        try:
            response = self._session.request(method, url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_details = self._extract_error_details(e)
            logger.error("API request failed: %s", error_details)
            return None 