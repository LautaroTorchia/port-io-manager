"""Scorecard-related API endpoints for Port.io."""

import logging
from typing import Optional, Dict, List
from ..client import PortAPIClient

logger = logging.getLogger(__name__)

class ScorecardClient:
    """Client for interacting with Port.io scorecard endpoints."""

    def __init__(self, client: PortAPIClient):
        """Initialize the scorecard client.

        Args:
            client: Base Port.io API client
        """
        self._client = client

    def get_scorecard(self, blueprint_id: str, scorecard_id: str) -> Optional[Dict]:
        """Get a single scorecard by its identifier.

        Args:
            blueprint_id: The identifier of the blueprint.
            scorecard_id: The identifier of the scorecard.

        Returns:
            A dictionary containing the scorecard, or None if not found.
        """
        return self._client._make_request('GET', f'blueprints/{blueprint_id}/scorecards/{scorecard_id}', ignore_404=True)

    def create_scorecard(self, blueprint_id: str, scorecard: Dict) -> Dict:
        """Creates a new scorecard for a given blueprint.

        Args:
            blueprint_id: The identifier of the blueprint.
            scorecard: A scorecard object to create.

        Returns:
            The API response after creating the scorecard.
        """
        return self._client._make_request('POST', f'blueprints/{blueprint_id}/scorecards', data=scorecard)

    def update_scorecard(self, blueprint_id: str, scorecard_id: str, scorecard: Dict) -> Dict:
        """Update/overwrite a single scorecard for a given blueprint.

        Args:
            blueprint_id: The identifier of the blueprint.
            scorecard_id: The identifier of the scorecard to update.
            scorecard: The scorecard object to update.

        Returns:
            The API response after updating the scorecard.
        """
        return self._client._make_request('PUT', f'blueprints/{blueprint_id}/scorecards/{scorecard_id}', data=scorecard) 