"""Integration-related API endpoints for Port.io."""

import logging
from typing import Optional, Dict
from ..client import PortAPIClient

logger = logging.getLogger(__name__)

class IntegrationClient:
    """Client for interacting with Port.io integration endpoints."""

    def __init__(self, client: PortAPIClient):
        """Initialize the integration client.

        Args:
            client: Base Port.io API client
        """
        self._client = client

    def get_integration(self, integration_id: str) -> Optional[Dict]:
        """Get an integration by ID.

        Args:
            integration_id: Integration identifier

        Returns:
            Integration data or None if not found
        """
        return self._client._make_request('GET', f'integration/{integration_id}', ignore_404=True)

    def update_integration_config(self, integration_id: str, config: Dict) -> Dict:
        """Update the configuration of an existing integration.

        Args:
            integration_id: Integration identifier
            config: The new configuration object

        Returns:
            The API response after updating the config
        """
        payload = {"config": config}
        return self._client._make_request('PATCH', f'integration/{integration_id}/config', data=payload) 