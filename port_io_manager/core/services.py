import json
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
from ..api.client import PortAPIError, PortAPIConflictError
from ..api.endpoints.blueprints import BlueprintClient
from ..comparator import BlueprintComparator, format_diff_for_display
from colorama import Fore, Style

logger = logging.getLogger(__name__)

class BlueprintService:
    """Service for managing blueprints and their synchronization with Port.io."""

    def __init__(self, client: BlueprintClient):
        """Initialize the Blueprint service.

        Args:
            client: Initialized Port.io blueprint client
        """
        self.client = client
        self.comparator = BlueprintComparator()
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
                return json.load(f)
        except json.JSONDecodeError:
            logger.error("Invalid JSON file: %s", file_path)
            self.has_failures = True
            return None
        except FileNotFoundError:
            logger.error("File not found: %s", file_path)
            self.has_failures = True
            return None

    def _check_related_entities_exist(self, blueprint_data: Dict) -> bool:
        """Checks if all related blueprints defined in the local file exist in Port.io."""
        relations = blueprint_data.get("relations", {})
        if not isinstance(relations, dict):
            return True  # No relations to check or invalid format

        blueprint_id = blueprint_data.get("identifier", "N/A")
        all_relations_exist = True

        for relation_name, relation_spec in relations.items():
            if not isinstance(relation_spec, dict):
                continue

            target_id = relation_spec.get("target")
            if not target_id:
                continue

            try:
                logger.debug(f"[{blueprint_id}] Validating relation '{relation_name}' -> '{target_id}'...")
                related_blueprint = self.client.get_blueprint(target_id)
                if not related_blueprint:
                    logger.error(
                        f"Validation failed for blueprint '{blueprint_id}': "
                        f"Related blueprint '{target_id}' (from relation '{relation_name}') does not exist."
                    )
                    all_relations_exist = False
            except PortAPIError as e:
                logger.error(
                    f"Validation failed for blueprint '{blueprint_id}': "
                    f"API error while checking related blueprint '{target_id}': {e}"
                )
                all_relations_exist = False

        return all_relations_exist

    def _log_diff(self, formatted_diff: Dict):
        """Builds a colorized, formatted string for the diff and logs it."""
        diff_lines = ["Found differences:"]

        def add_lines(title, items, prefix, color):
            if items:
                diff_lines.append(f"  {color}{Style.BRIGHT}{title}:{Style.RESET_ALL}")
                for item in items:
                    if 'local_value' in item:  # This is a 'value_changed' item
                        key = item['key']
                        remote = item['remote_value']
                        local = item['local_value']
                        diff_lines.append(f"    {color}{prefix} {key}{Style.RESET_ALL}")
                        diff_lines.append(f"      {Fore.RED}- {remote}{Style.RESET_ALL}")
                        diff_lines.append(f"      {Fore.GREEN}+ {local}{Style.RESET_ALL}")
                    else:
                        key = item['key']
                        diff_lines.append(f"    {color}{prefix} {key}{Style.RESET_ALL}")
        
        add_lines("Added", formatted_diff.get('items_added_locally', []), "+", Fore.GREEN)
        add_lines("Removed", formatted_diff.get('items_removed_locally', []), "-", Fore.RED)
        add_lines("Modified", formatted_diff.get('values_changed', []), "~", Fore.YELLOW)

        # Log the entire block as a single message
        logger.info("\n" + "\n".join(diff_lines))

    def _check_recent_update(self, blueprint_metadata: Dict) -> bool:
        """
        Check if blueprint was recently updated in Port.io UI.

        Args:
            blueprint_metadata: Blueprint metadata containing update timestamp

        Returns:
            True if recently modified (within 24 hours), False otherwise.
        """
        last_updated_str = blueprint_metadata.get('updatedAt')
        if not last_updated_str:
            return False

        last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
        time_difference = datetime.now(timezone.utc) - last_updated
        
        return time_difference.total_seconds() < 86400

    def process_blueprint_file(
        self, file_path: str, force_update: bool = False, dry_run: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Processes a single blueprint file.

        Args:
            file_path: Path to the blueprint file.
            force_update: If true, forces the update even if recently modified.
            dry_run: If true, previews changes without applying them.

        Returns:
            A tuple containing:
            - bool: Overall success of the operation for this file.
            - str | None: A status string. Can be 'confirmation_required' if user
                          interaction is needed, or None otherwise.
        """
        logger.info("Processing blueprint file: %s", file_path)
        
        local_blueprint_data = self.load_blueprint_from_file(file_path)
        if not local_blueprint_data:
            self.has_failures = True
            return False, None

        # Validate that all related entities exist before proceeding
        if not self._check_related_entities_exist(local_blueprint_data):
            self.has_failures = True
            return False, None

        blueprint_id = local_blueprint_data.get('identifier')
        if not blueprint_id:
            logger.error("Missing required 'identifier' field in blueprint: %s", file_path)
            self.has_failures = True
            return False, None

        if dry_run:
            logger.info(f"{Fore.CYAN}[DRY RUN] The tool is running in dry-run mode. No changes will be applied.{Style.RESET_ALL}")

        try:
            remote_blueprint_wrapper = self.client.get_blueprint(blueprint_id)
        except PortAPIError as e:
            logger.error("Failed to check blueprint %s: %s", blueprint_id, e.get_detailed_message())
            self.has_failures = True
            return False, None

        if remote_blueprint_wrapper:
            return self._update_blueprint(blueprint_id, local_blueprint_data, remote_blueprint_wrapper, force_update, dry_run)
        else:
            return self._create_blueprint(blueprint_id, local_blueprint_data, dry_run)

    def _create_blueprint(self, blueprint_id: str, local_blueprint_data: Dict, dry_run: bool) -> Tuple[bool, None]:
        """Handles the creation of a new blueprint."""
        logger.info(f"Blueprint '{blueprint_id}' does not exist remotely. Planning to create.")
        
        if dry_run:
            logger.info(f"{Fore.GREEN}[DRY RUN] Blueprint '{blueprint_id}' will be created.{Style.RESET_ALL}")
            return True, None

        try:
            logger.info(f"Creating blueprint: {blueprint_id}")
            self.client.create_blueprint(local_blueprint_data)
            logger.info("Successfully created blueprint: %s", blueprint_id)
            return True, None
        except PortAPIConflictError:
            logger.error("Race condition detected for blueprint %s - please try again", blueprint_id)
            self.has_failures = True
            return False, None
        except PortAPIError as e:
            logger.error("Failed to create blueprint %s: %s", blueprint_id, e.get_detailed_message())
            self.has_failures = True
            return False, None

    def _update_blueprint(
        self, blueprint_id: str, local_blueprint_data: Dict, remote_blueprint_wrapper: Dict, force_update: bool, dry_run: bool
    ) -> Tuple[bool, Optional[str]]:
        """Handles the update of an existing blueprint."""
        remote_blueprint = remote_blueprint_wrapper.get("blueprint", {})
        diff = self.comparator.compare(local_blueprint_data, remote_blueprint)

        if not diff:
            logger.info("Blueprint '%s' is up to date", blueprint_id)
            return True, None

        formatted_diff = format_diff_for_display(diff)
        self._log_diff(formatted_diff)
        
        if not force_update and self._check_recent_update(remote_blueprint):
            logger.warning(
                f"Remote blueprint '{blueprint_id}' was modified in the UI within the last 24 hours."
            )
            return False, 'confirmation_required'

        if dry_run:
            logger.info(f"{Fore.YELLOW}[DRY RUN] Blueprint '{blueprint_id}' will be updated with the changes above.{Style.RESET_ALL}")
            return True, None

        try:
            logger.info(f"Updating blueprint: {blueprint_id}")
            self.client.update_blueprint(blueprint_id, local_blueprint_data)
            logger.info("Successfully updated blueprint: %s", blueprint_id)
            return True, None
        except PortAPIError as e:
            logger.error("Failed to update blueprint %s: %s", blueprint_id, e.get_detailed_message())
            self.has_failures = True
            return False, None