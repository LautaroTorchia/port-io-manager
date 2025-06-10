"""Blueprint-related API endpoints for Port.io."""

import logging
from typing import Optional, Dict
from ..client import PortAPIClient

logger = logging.getLogger(__name__)

class BlueprintClient:
    """Client for interacting with Port.io blueprint endpoints."""

    def __init__(self, client: PortAPIClient):
        """Initialize the blueprint client.

        Args:
            client: Base Port.io API client
        """
        self._client = client

    def get_blueprint(self, blueprint_id: str) -> Optional[Dict]:
        """Get a blueprint by ID.

        Args:
            blueprint_id: Blueprint identifier

        Returns:
            Blueprint data or None if not found
        """
        return self._client._make_request('GET', f'blueprints/{blueprint_id}', ignore_404=True)

    def create_blueprint(self, blueprint_data: Dict) -> Dict:
        """Create a new blueprint.

        Args:
            blueprint_data: Blueprint definition

        Returns:
            Created blueprint data
        """
        # Ensure we're using the correct endpoint
        return self._client._make_request('POST', 'blueprints', data=blueprint_data)

    def update_blueprint(self, blueprint_id: str, blueprint_data: Dict) -> Dict:
        """Update an existing blueprint.

        Args:
            blueprint_id: Blueprint identifier
            blueprint_data: Updated blueprint definition

        Returns:
            Updated blueprint data
        """
        return self._client._make_request('PUT', f'blueprints/{blueprint_id}', data=blueprint_data)

    def delete_blueprint(self, blueprint_id: str) -> None:
        """Delete a blueprint.

        Args:
            blueprint_id: Blueprint identifier
        """
        self._client._make_request('DELETE', f'blueprints/{blueprint_id}', ignore_404=True) 