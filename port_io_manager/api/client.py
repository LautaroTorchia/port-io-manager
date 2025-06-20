import requests
import sys
import json
import logging
from typing import Optional, Dict, Any
from pprint import pformat
from .exceptions import PortAPIError, PortAPIConflictError

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

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, ignore_404: bool = False) -> Any:
        """Make a request to the Port.io API.

        Args:
            method: HTTP method to use
            endpoint: API endpoint to call
            data: Optional request payload
            ignore_404: Whether to ignore 404 errors and return None instead

        Returns:
            API response data or None if ignore_404=True and resource not found

        Raises:
            PortAPIConflictError: When a 409 Conflict occurs
            PortAPIError: When any other API error occurs
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        try:
            logger.debug("Making %s request to %s", method, url)
            if data:
                logger.debug("Request payload: %s", json.dumps(data, indent=2))
            
            response = self._session.request(method, url, json=data)
            
            # Always log response payload for debugging
            try:
                response_data = response.json()
                logger.debug("Response payload: %s", json.dumps(response_data, indent=2))
            except ValueError:
                logger.debug("Response payload (raw): %s", response.text)

            # Handle 404 specially if requested
            if ignore_404 and response.status_code == 404:
                return None
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            try:
                response_data = e.response.json() if e.response else None
            except ValueError:
                response_data = {'raw_text': e.response.text} if e.response else None

            # Log complete error information only in debug
            logger.debug("API Error Details:")
            logger.debug("URL: %s", url)
            logger.debug("Method: %s", method)
            logger.debug("Response Status: %s", e.response.status_code)
            logger.debug("Response Headers: %s", dict(e.response.headers))
            if response_data:
                logger.debug("Response Data: %s", json.dumps(response_data, indent=2))

            error_details = self._extract_error_details(e)
            
            sanitized_data = None
            if data:
                # Create a copy of the data and remove sensitive fields
                sanitized_data = data.copy()
                sensitive_fields = ['clientId', 'clientSecret', 'token', 'password']
                for field in sensitive_fields:
                    if field in sanitized_data:
                        sanitized_data[field] = '***REDACTED***'
            
            if ignore_404 and e.response.status_code == 404:
                return None
            elif e.response.status_code == 409:
                raise PortAPIConflictError(
                    409,
                    error_details,
                    response_data=response_data,
                    request_data=sanitized_data
                )
            raise PortAPIError(
                e.response.status_code,
                error_details,
                response_data=response_data,
                request_data=sanitized_data
            )
        except requests.exceptions.RequestException as e:
            error_details = self._extract_error_details(e)
            raise PortAPIError(500, error_details)
