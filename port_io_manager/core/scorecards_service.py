import logging
import json
from typing import Dict, Optional, Tuple
from deepdiff import DeepDiff
from colorama import Fore, Style

from ..api.client import PortAPIError
from ..api.endpoints.scorecards import ScorecardClient
from ..api.endpoints.blueprints import BlueprintClient

logger = logging.getLogger(__name__)

class ScorecardService:
    """Service for managing Port.io blueprint scorecards individually."""

    def __init__(self, scorecard_client: ScorecardClient, blueprint_client: BlueprintClient):
        self.scorecard_client = scorecard_client
        self.blueprint_client = blueprint_client
        self.has_failures = False

    def _load_scorecard_file(self, file_path: str) -> Optional[Dict]:
        """Loads a single scorecard definition from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                # We now expect a top-level object, not a list
                if isinstance(data, list):
                    logger.error(f"Invalid format in {file_path}: file should be a JSON object, not a list.")
                    return None
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON file: {file_path}. Error: {e}")
            self.has_failures = True
            return None
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            self.has_failures = True
            return None
    
    def _validate_scorecard_properties(self, blueprint_id: str, scorecard: Dict) -> bool:
        """Validates that all properties used in a scorecard's rules exist in the target blueprint."""
        try:
            blueprint_wrapper = self.blueprint_client.get_blueprint(blueprint_id)
            if not blueprint_wrapper:
                logger.error(f"Validation failed: Blueprint '{blueprint_id}' not found.")
                return False
            
            blueprint_properties = blueprint_wrapper.get("blueprint", {}).get("schema", {}).get("properties", {}).keys()
            
            for rule in scorecard.get("rules", []):
                for condition in rule.get("query", {}).get("conditions", []):
                    prop = condition.get("property")
                    if prop and not prop.startswith('$') and prop not in blueprint_properties:
                        logger.error(
                            f"Validation failed in scorecard '{scorecard.get('identifier')}': "
                            f"Property '{prop}' does not exist in blueprint '{blueprint_id}'."
                        )
                        return False
            return True
        except PortAPIError as e:
            logger.error(f"API error during scorecard validation for blueprint '{blueprint_id}': {e}")
            return False

    def _log_diff(self, diff: DeepDiff):
        """Builds and logs a more granular, colorized diff for a single scorecard."""
        diff_lines = ["Found differences in scorecard:"]
        parsed_diff = diff.to_dict()

        def clean_path(path_str):
            # Converts deepdiff path to a more readable format
            # e.g., "root['rules'][0]" to "scorecard.rules[0]"
            return path_str.replace("root", "scorecard").replace("['", ".").replace("']", "").replace(".[", "[")

        if 'values_changed' in parsed_diff:
            diff_lines.append(f"  {Fore.YELLOW}{Style.BRIGHT}Modified Fields:{Style.RESET_ALL}")
            for path, changes in parsed_diff['values_changed'].items():
                diff_lines.append(f"    ~ Field `{clean_path(path)}`")
                diff_lines.append(f"      {Fore.RED}- From: {changes['old_value']}{Style.RESET_ALL}")
                diff_lines.append(f"      {Fore.GREEN}+ To:   {changes['new_value']}{Style.RESET_ALL}")
        
        if 'dictionary_item_added' in parsed_diff:
            diff_lines.append(f"  {Fore.GREEN}{Style.BRIGHT}Added Fields:{Style.RESET_ALL}")
            for path in parsed_diff['dictionary_item_added']:
                diff_lines.append(f"    + {clean_path(path)}")

        if 'dictionary_item_removed' in parsed_diff:
            diff_lines.append(f"  {Fore.RED}{Style.BRIGHT}Removed Fields:{Style.RESET_ALL}")
            for path in parsed_diff['dictionary_item_removed']:
                diff_lines.append(f"    - {clean_path(path)}")
        
        if 'iterable_item_added' in parsed_diff:
            diff_lines.append(f"  {Fore.GREEN}{Style.BRIGHT}Added Items (in a list):{Style.RESET_ALL}")
            for path, value in parsed_diff['iterable_item_added'].items():
                value_str = json.dumps(value, indent=2)
                indented_value_str = "\n".join(["        " + line for line in value_str.splitlines()])
                diff_lines.append(f"    + At `{clean_path(path)}`:\n{Fore.GREEN}{indented_value_str}{Style.RESET_ALL}")

        if 'iterable_item_removed' in parsed_diff:
            diff_lines.append(f"  {Fore.RED}{Style.BRIGHT}Removed Items (in a list):{Style.RESET_ALL}")
            for path, value in parsed_diff['iterable_item_removed'].items():
                value_str = json.dumps(value, indent=2)
                indented_value_str = "\n".join(["        " + line for line in value_str.splitlines()])
                diff_lines.append(f"    - At `{clean_path(path)}`:\n{Fore.RED}{indented_value_str}{Style.RESET_ALL}")

        logger.info("\n" + "\n".join(diff_lines))

    def process_scorecard_file(
        self, file_path: str, dry_run: bool = False, force: bool = False
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Processes a single scorecard file.
        Returns a tuple: (success, status, data_for_apply).
        """
        wrapper = self._load_scorecard_file(file_path)
        if not wrapper:
            self.has_failures = True
            return False, "file_error", None

        blueprint_id = wrapper.get('blueprintIdentifier')
        local_scorecard = wrapper.get('scorecard')

        if not blueprint_id or not local_scorecard:
            logger.error(f"File '{file_path}' is missing 'blueprintIdentifier' or 'scorecard' keys.")
            self.has_failures = True
            return False, "config_error", None

        scorecard_id = local_scorecard.get("identifier")
        if not scorecard_id:
            logger.error(f"Scorecard in '{file_path}' is missing its 'identifier'.")
            self.has_failures = True
            return False, "config_error", None

        logger.info(f"Processing scorecard '{scorecard_id}' for blueprint '{blueprint_id}'...")

        if not self._validate_scorecard_properties(blueprint_id, local_scorecard):
            self.has_failures = True
            return False, "validation_error", None

        try:
            remote_scorecard_wrapper = self.scorecard_client.get_scorecard(blueprint_id, scorecard_id)
            remote_scorecard = remote_scorecard_wrapper.get("scorecard") if remote_scorecard_wrapper else None
        except PortAPIError as e:
            logger.error(f"Failed to fetch scorecard '{scorecard_id}' from blueprint '{blueprint_id}': {e}")
            self.has_failures = True
            return False, "api_error", None

        change_data = {
            "blueprint_id": blueprint_id,
            "scorecard_id": scorecard_id,
            "payload": local_scorecard,
        }

        if remote_scorecard: # UPDATE logic
            normalized_remote_scorecard = {
                key: remote_scorecard.get(key) for key in local_scorecard.keys()
            }
            diff = DeepDiff(normalized_remote_scorecard, local_scorecard, ignore_order=True)

            if not diff:
                logger.info("No changes detected.")
                return True, "no_changes", None

            self._log_diff(diff)
            change_data["action"] = "update"

            if dry_run:
                logger.info(f"{Fore.CYAN}[DRY RUN] Scorecard will be updated.{Style.RESET_ALL}")
                return True, "dry_run", None
            
            if not force:
                return True, "confirmation_required", change_data
            
            return self.apply_scorecard_change(change_data)

        else: # CREATE logic
            logger.info("Scorecard does not exist remotely. Planning to create.")
            change_data["action"] = "create"

            if dry_run:
                logger.info(f"{Fore.GREEN}[DRY RUN] Scorecard '{scorecard_id}' will be created.{Style.RESET_ALL}")
                return True, "dry_run", None
            
            if not force:
                return True, "confirmation_required", change_data
            
            return self.apply_scorecard_change(change_data)

    def apply_scorecard_change(self, change_data: Dict) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Applies a create or update action for a scorecard."""
        action = change_data.get("action")
        blueprint_id = change_data.get("blueprint_id")
        scorecard_id = change_data.get("scorecard_id")
        payload = change_data.get("payload")

        try:
            if action == "update":
                logger.info(f"Applying update for scorecard '{scorecard_id}'...")
                self.scorecard_client.update_scorecard(blueprint_id, scorecard_id, payload)
                logger.info(f"Successfully updated scorecard '{scorecard_id}'.")
                return True, "updated", None
            elif action == "create":
                logger.info(f"Applying create for scorecard '{scorecard_id}'...")
                self.scorecard_client.create_scorecard(blueprint_id, payload)
                logger.info(f"Successfully created scorecard '{scorecard_id}'.")
                return True, "created", None
            else:
                logger.error(f"Invalid action '{action}' for scorecard '{scorecard_id}'.")
                self.has_failures = True
                return False, "internal_error", None
        except PortAPIError as e:
            logger.error(f"Failed to {action} scorecard '{scorecard_id}': {e}")
            self.has_failures = True
            return False, "api_error", None 