import logging
from typing import Optional, Dict, Any
from ..client import PortAPIClient
from ..exceptions import PortAPIError, PortAPIConflictError

logger = logging.getLogger(__name__)

class BlueprintClient(PortAPIClient):
    """Client for managing Port.io Blueprints."""

    def __init__(self, client_id: str, client_secret: str):
        """Initialize the Blueprint client.

        Args:
            client_id: Port.io client ID
            client_secret: Port.io client secret
        """
        super().__init__(client_id, client_secret)
        self.endpoint = "blueprints"

    def get_blueprint(self, blueprint_id: str) -> Optional[Dict]:
        """Retrieve a blueprint by its ID.

        Args:
            blueprint_id: Unique identifier of the blueprint

        Returns:
            Blueprint data or None if not found

        Raises:
            PortAPIError: If there is an API error other than 404
        """
        try:
            response = self._make_request('GET', f"{self.endpoint}/{blueprint_id}")
            logger.info("Retrieved blueprint: %s", blueprint_id)
            return response.get("blueprint")
        except PortAPIError as e:
            if "404" in str(e):
                logger.warning("Blueprint not found: %s", blueprint_id)
                return None
            logger.error("Failed to get blueprint %s:\n%s", blueprint_id, e.get_detailed_message())
            raise

    def create_blueprint(self, blueprint_data: Dict) -> Dict:
        """Create a new blueprint.

        Args:
            blueprint_data: Blueprint definition data

        Returns:
            Created blueprint data

        Raises:
            PortAPIConflictError: If blueprint already exists
            PortAPIError: If there is any other API error
        """
        try:
            response = self._make_request('POST', self.endpoint, data=blueprint_data)
            logger.info("Created blueprint: %s", blueprint_data.get('identifier'))
            return response
        except PortAPIConflictError as e:
            logger.error("Failed to create blueprint %s - Already exists:\n%s", 
                        blueprint_data.get('identifier'), e.get_detailed_message())
            raise
        except PortAPIError as e:
            logger.error("Failed to create blueprint %s:\n%s", 
                        blueprint_data.get('identifier'), e.get_detailed_message())
            raise

    def update_blueprint(self, blueprint_id: str, blueprint_data: Dict) -> Dict:
        """Update an existing blueprint.

        Args:
            blueprint_id: Unique identifier of the blueprint
            blueprint_data: Updated blueprint definition data

        Returns:
            Updated blueprint data

        Raises:
            PortAPIError: If blueprint doesn't exist or any other API error occurs
        """
        try:
            update_payload = self._prepare_update_payload(blueprint_data)
            response = self._make_request('PUT', f"{self.endpoint}/{blueprint_id}", data=update_payload)
            logger.info("Updated blueprint: %s", blueprint_id)
            return response
        except PortAPIError as e:
            if "404" in str(e):
                logger.error("Failed to update blueprint %s - Not found:\n%s", 
                           blueprint_id, e.get_detailed_message())
            else:
                logger.error("Failed to update blueprint %s:\n%s", 
                           blueprint_id, e.get_detailed_message())
            raise

    def _prepare_update_payload(self, blueprint_data: Dict) -> Dict:
        """Prepare blueprint data for update by removing server-managed fields.

        Args:
            blueprint_data: Original blueprint data

        Returns:
            Cleaned blueprint data suitable for update
        """
        update_payload = blueprint_data.copy()

        # Remove server-managed top-level fields
        top_level_keys_to_remove = ['createdAt', 'updatedAt', 'createdBy', 'updatedBy']
        for key in top_level_keys_to_remove:
            update_payload.pop(key, None)

        # Remove reserved properties from schema
        if 'schema' in update_payload and 'properties' in update_payload['schema']:
            schema_properties_to_remove = [
                'createdAt', 'updatedAt', 'createdBy', 'updatedBy',
                'resolvedAt', 'statusChangedAt'
            ]
            for key in schema_properties_to_remove:
                if key in update_payload['schema']['properties']:
                    del update_payload['schema']['properties'][key]

        return update_payload 