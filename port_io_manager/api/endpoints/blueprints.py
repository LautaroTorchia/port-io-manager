from typing import Optional, Dict, Any
from ..client import PortAPIClient

class BlueprintClient(PortAPIClient):
    """Client for managing Port.io Blueprints."""

    def __init__(self, client_id: str, client_secret: str):
        super().__init__(client_id, client_secret)
        self.endpoint = "blueprints"

    def get_blueprint(self, blueprint_id: str) -> Optional[Dict]:
        """Retrieves a blueprint by its ID."""
        response = self._make_request('GET', f"{self.endpoint}/{blueprint_id}")
        if response:
            print(f"Blueprint '{blueprint_id}' found.")
            return response.get("blueprint")
        print(f"Blueprint '{blueprint_id}' not found.")
        return None

    def create_blueprint(self, blueprint_data: Dict) -> Optional[Dict]:
        """Creates a new blueprint."""
        response = self._make_request('POST', self.endpoint, data=blueprint_data)
        if response:
            print("✅ Blueprint created successfully.")
            return response
        return None

    def update_blueprint(self, blueprint_id: str, blueprint_data: Dict) -> Optional[Dict]:
        """Updates an existing blueprint."""
        # Clean up server-managed fields
        update_payload = blueprint_data.copy()
        top_level_keys_to_remove = ['createdAt', 'updatedAt', 'createdBy', 'updatedBy']
        for key in top_level_keys_to_remove:
            update_payload.pop(key, None)

        # Clean up reserved properties in schema
        if 'schema' in update_payload and 'properties' in update_payload['schema']:
            schema_properties_to_remove = [
                'createdAt', 'updatedAt', 'createdBy', 'updatedBy',
                'resolvedAt', 'statusChangedAt'
            ]
            for key in schema_properties_to_remove:
                if key in update_payload['schema']['properties']:
                    del update_payload['schema']['properties'][key]

        response = self._make_request('PUT', f"{self.endpoint}/{blueprint_id}", data=update_payload)
        if response:
            print("✅ Blueprint updated successfully.")
            return response
        return None 