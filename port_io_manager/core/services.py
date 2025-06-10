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
        """Format DeepDiff output for human-readable display.

        Args:
            diff: DeepDiff comparison result

        Returns:
            Formatted difference data
        """
        processed_diff = {}
        if 'values_changed' in diff:
            processed_diff['values_changed'] = [
                {
                    'key': key.replace("root", "blueprint"),
                    'remote_value': value['old_value'],
                    'local_value': value['new_value']
                }
                for key, value in diff['values_changed'].items()
            ]
        if 'dictionary_item_added' in diff:
            processed_diff['items_added_locally'] = [
                item.replace("root", "blueprint") for item in diff['dictionary_item_added']
            ]
        if 'dictionary_item_removed' in diff:
            processed_diff['items_removed_locally'] = [
                item.replace("root", "blueprint") for item in diff['dictionary_item_removed']
            ]
        return processed_diff

    def compare_blueprints(self, local_blueprint: Dict, remote_blueprint: Dict) -> Optional[Dict]:
        """Compare local and remote blueprint configurations.

        Args:
            local_blueprint: Local blueprint definition
            remote_blueprint: Remote blueprint definition from Port.io

        Returns:
            Formatted differences or None if blueprints are identical
        """
        exclude_paths = [
            "root['createdAt']",
            "root['updatedAt']",
            "root['createdBy']",
            "root['updatedBy']"
        ]
        diff = DeepDiff(remote_blueprint, local_blueprint, ignore_order=True, exclude_paths=exclude_paths)
        
        if not diff:
            logger.info("No differences found between local and remote blueprints")
            return None

        formatted_diff = self.format_diff_for_display(diff)
        logger.info("Found differences between local and remote blueprints:")
        
        # Display changes in a readable format
        if 'values_changed' in formatted_diff:
            logger.info("Modified values:")
            for change in formatted_diff['values_changed']:
                logger.info("  Field: %s", change['key'])
                logger.info("    - Remote: %s", change['remote_value'])
                logger.info("    + Local:  %s", change['local_value'])

        if 'items_added_locally' in formatted_diff:
            logger.info("Added fields:")
            for item in formatted_diff['items_added_locally']:
                logger.info("  + %s", item)

        if 'items_removed_locally' in formatted_diff:
            logger.info("Removed fields:")
            for item in formatted_diff['items_removed_locally']:
                logger.info("  - %s", item)

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
        """Process a blueprint file for synchronization with Port.io.

        Args:
            file_path: Path to the blueprint JSON file
            force_update: Whether to force update regardless of recent changes
            skip_confirmation: Whether to skip user confirmation prompts

        Returns:
            bool: True if the process was successful, False otherwise
        """
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
            remote_blueprint = None
            try:
                remote_blueprint = self.client.get_blueprint(blueprint_id)
            except PortAPIError as e:
                if "404" not in str(e):
                    raise

            if remote_blueprint:
                diff = self.compare_blueprints(local_blueprint_data, remote_blueprint)
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
                except PortAPIError as update_error:
                    if "404" in str(update_error):
                        logger.warning("Blueprint '%s' not found during update, attempting to create it", blueprint_id)
                    else:
                        raise update_error

            # If we get here, either:
            # 1. The blueprint didn't exist
            # 2. The update failed with 404
            # In both cases, we try to create it
            logger.info("Creating new blueprint: %s", blueprint_id)
            try:
                self.client.create_blueprint(local_blueprint_data)
                logger.info("Successfully created blueprint: %s", blueprint_id)
                return True
            except PortAPIConflictError as create_error:
                if "already exists" in str(create_error).lower():
                    logger.error("Conflict: Blueprint '%s' already exists but couldn't be retrieved or updated", blueprint_id)
                    logger.error("This might indicate an issue with Port.io API permissions or a race condition")
                raise

        except PortAPIConflictError as e:
            logger.error("Conflict error while processing blueprint %s: %s", blueprint_id, e.message)
            if "already exists" in e.message.lower():
                logger.error("A blueprint with identifier '%s' already exists. Please choose a different identifier.", blueprint_id)
            self.has_failures = True
            return False
        except PortAPIError as e:
            logger.error("API error while processing blueprint %s: %s", blueprint_id, e.message)
            self.has_failures = True
            return False
        except Exception as e:
            logger.error("Unexpected error while processing blueprint %s: %s", blueprint_id, str(e))
            self.has_failures = True
            return False 