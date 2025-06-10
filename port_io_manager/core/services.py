import json
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timezone
from deepdiff import DeepDiff
from ..api.client import PortAPIError, PortAPIConflictError
from ..api.endpoints.blueprints import BlueprintClient

logger = logging.getLogger(__name__)

class BlueprintService:
    """Service for managing blueprints and their synchronization with Port.io."""

    def __init__(self, client: BlueprintClient):
        """Initialize the Blueprint service.

        Args:
            client: Initialized Port.io blueprint client
        """
        self.client = client
        self.has_failures = False

    def load_blueprint_from_file(self, file_path: str) -> Optional[Dict]:
        """Load a blueprint definition from a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Blueprint data or None if loading fails
        """
        try:
            with open(file_path, 'r') as f:
                blueprint_data = json.load(f)
            return blueprint_data
        except json.JSONDecodeError:
            logger.error("Invalid JSON file: %s", file_path)
            self.has_failures = True
            return None
        except FileNotFoundError:
            logger.error("File not found: %s", file_path)
            self.has_failures = True
            return None

    def format_diff_for_display(self, diff: DeepDiff) -> Dict:
        """Format DeepDiff output for human-readable display."""
        processed_diff = {}

        # Process modified fields (values changed)
        if 'values_changed' in diff:
            processed_diff['values_changed'] = []
            for key, value in diff['values_changed'].items():
                # Modify the path to be more readable
                path = key.replace("root", "blueprint")
                processed_diff['values_changed'].append({
                    'key': path,
                    'remote_value': value['old_value'],
                    'local_value': value['new_value']
                })

        # Process added fields (dictionary_item_added)
        if 'dictionary_item_added' in diff:
            processed_diff['dictionary_item_added'] = [
                item.replace("root", "blueprint") for item in diff['dictionary_item_added']
            ]

        # Process removed fields (dictionary_item_removed)
        if 'dictionary_item_removed' in diff:
            processed_diff['dictionary_item_removed'] = [
                item.replace("root", "blueprint") for item in diff['dictionary_item_removed']
            ]

        return processed_diff

    def compare_blueprints(self, local_blueprint: Dict, remote_blueprint: Dict) -> Optional[Dict]:
        """Compare local and remote blueprint configurations."""
        exclude_paths = [
            "root['createdAt']",
            "root['updatedAt']",
            "root['createdBy']",
            "root['updatedBy']"
        ]
        
        # Perform the comparison with DeepDiff
        diff = DeepDiff(remote_blueprint, local_blueprint, ignore_order=True, exclude_paths=exclude_paths)

        if not diff:
            logger.info("No differences found between local and remote blueprints")
            return None

        # Format the differences into a more readable format
        formatted_diff = self.format_diff_for_display(diff)
        
        if not formatted_diff:  # If no meaningful changes after filtering
            logger.info("No meaningful changes found")
            return None

        logger.info("Found differences between local and remote blueprints:")

        # Log added fields (dictionary_item_added)
        if 'dictionary_item_added' in formatted_diff:
            logger.info("Added fields:")
            for item in formatted_diff['dictionary_item_added']:
                logger.info(f"  + {item}")

        # Log removed fields (dictionary_item_removed)
        if 'dictionary_item_removed' in formatted_diff:
            logger.info("Removed fields:")
            for item in formatted_diff['dictionary_item_removed']:
                logger.info(f"  - {item}")

        # Log modified fields (values_changed)
        if 'values_changed' in formatted_diff:
            logger.info("Modified fields:")
            for change in formatted_diff['values_changed']:
                logger.info(f"  Field: {change['key']}")
                logger.info(f"    - Remote: {change['remote_value']}")
                logger.info(f"    + Local:  {change['local_value']}")

        return formatted_diff



    def check_recent_update(self, blueprint_metadata: Dict, force_update: bool = False) -> bool:
        """Check if blueprint was recently updated in Port.io UI.

        Args:
            blueprint_metadata: Blueprint metadata containing update timestamp
            force_update: Whether to ignore recent updates

        Returns:
            True if safe to update, False if recently modified
        """
        if force_update:
            logger.info("Force update enabled, skipping recent update check")
            return True
        
        last_updated_str = blueprint_metadata.get('updatedAt')
        if not last_updated_str:
            return True

        last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
        time_difference = datetime.now(timezone.utc) - last_updated
        
        if time_difference.total_seconds() < 86400:  # Less than 24 hours
            logger.warning("Blueprint was updated in Port.io UI less than 24 hours ago")
            return False
        return True

    def process_blueprint_file(self, file_path: str, force_update: bool = False, skip_confirmation: bool = False) -> bool:
        logger.info("Processing blueprint file: %s", file_path)
        
        local_blueprint_data = self.load_blueprint_from_file(file_path)
        if not local_blueprint_data:
            self.has_failures = True
            return False

        blueprint_id = local_blueprint_data.get('identifier')
        if not blueprint_id:
            logger.error("Missing required 'identifier' field in blueprint: %s", file_path)
            self.has_failures = True
            return False

        try:
            try:
                remote_blueprint = self.client.get_blueprint(blueprint_id)
            except PortAPIError as e:
                if "404" not in str(e):
                    logger.error("Failed to check blueprint %s", blueprint_id)
                    self.has_failures = True
                    return False
                remote_blueprint = None

            if remote_blueprint:
                # Blueprint exists, try to update it
                diff = self.compare_blueprints(local_blueprint_data, remote_blueprint["blueprint"])
                if not diff:
                    logger.info("Blueprint '%s' is up to date", blueprint_id)
                    return True

                if not self.check_recent_update(remote_blueprint, force_update) and not skip_confirmation:
                    user_input = input("Blueprint was recently updated in Port.io UI. Continue with update? (y/N): ")
                    if user_input.lower() != 'y':
                        logger.info("Update cancelled by user for blueprint: %s", blueprint_id)
                        return True

                try:
                    logger.info("Updating blueprint: %s", blueprint_id)
                    self.client.update_blueprint(blueprint_id, local_blueprint_data)
                    logger.info("Successfully updated blueprint: %s", blueprint_id)
                    return True
                except PortAPIError as e:
                    # For 404 errors during update, it's likely a related entity issue
                    if "404" in str(e):
                        logger.error("Failed to update blueprint %s - this might be due to missing related entities", blueprint_id)
                        # Try to extract the missing entity name from the response
                        if e.response_data:
                            # First check validation errors
                            validation_errors = e.response_data.get('validationErrors', [])
                            for error in validation_errors:
                                if isinstance(error, dict) and error.get('type') == 'ENTITY_NOT_FOUND':
                                    missing_entity = error.get('entityIdentifier')
                                    if missing_entity:
                                        logger.error("Missing related blueprint: '%s'", missing_entity)
                                        break
                            else:
                                # If not found in validation errors, check details field
                                details = e.response_data.get('details', {})
                                if details.get('resource') == 'Blueprint':
                                    missing_entity = details.get('withValue')
                                    if missing_entity and missing_entity != blueprint_id:
                                        logger.error("Missing related blueprint: '%s'", missing_entity)
                    else:
                        logger.error("Failed to update blueprint %s: %s", blueprint_id, e.get_detailed_message())
                    self.has_failures = True
                    return False

            else:
                # Blueprint doesn't exist, try to create it
                try:
                    logger.info("Creating blueprint: %s", blueprint_id)
                    self.client.create_blueprint(local_blueprint_data)
                    logger.info("Successfully created blueprint: %s", blueprint_id)
                    return True
                except PortAPIConflictError as e:
                    logger.error("Race condition detected for blueprint %s - please try again", blueprint_id)
                    self.has_failures = True
                    return False
                except PortAPIError as e:
                    # For 404 errors during create, it's likely a related entity issue
                    if "404" in str(e):
                        logger.error("Failed to create blueprint %s - this might be due to missing related entities", blueprint_id)
                        # Try to extract the missing entity name from the response
                        if e.response_data:
                            # First check validation errors
                            validation_errors = e.response_data.get('validationErrors', [])
                            for error in validation_errors:
                                if isinstance(error, dict) and error.get('type') == 'ENTITY_NOT_FOUND':
                                    missing_entity = error.get('entityIdentifier')
                                    if missing_entity:
                                        logger.error("Missing related blueprint: '%s'", missing_entity)
                                        break
                            else:
                                # If not found in validation errors, check details field
                                details = e.response_data.get('details', {})
                                if details.get('resource') == 'Blueprint':
                                    missing_entity = details.get('withValue')
                                    if missing_entity and missing_entity != blueprint_id:
                                        logger.error("Missing related blueprint: '%s'", missing_entity)
                    else:
                        logger.error("Failed to create blueprint %s: %s", blueprint_id, e.get_detailed_message())
                    self.has_failures = True
                    return False

        except Exception as e:
            logger.error("Unexpected error while processing blueprint %s: %s", blueprint_id, str(e))
            self.has_failures = True
            return False