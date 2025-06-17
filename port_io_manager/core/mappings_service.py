import logging
import yaml
from typing import Dict, Optional, Tuple, Any
from deepdiff import DeepDiff
from colorama import Fore, Style

from ..api.client import PortAPIError
from ..api.endpoints.integrations import IntegrationClient

logger = logging.getLogger(__name__)

class MappingService:
    """Service for managing Port.io integration mappings."""

    def __init__(self, client: IntegrationClient):
        self.client = client
        self.has_failures = False

    def load_mapping_from_file(self, file_path: str) -> Optional[Dict]:
        """Loads a mapping definition from a YAML file."""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML file: {file_path}. Error: {e}")
            self.has_failures = True
            return None
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            self.has_failures = True
            return None

    def _format_diff_details(self, diff: DeepDiff, kind: str) -> list[str]:
        """Formats the details of a deepdiff object for a specific kind."""
        diff_lines = []
        parsed_diff = diff.to_dict()

        def clean_path(path_str):
            """Cleans the deepdiff path for better readability."""
            return path_str.replace("root", f"resources.{kind}").replace("['", ".").replace("']", "").replace("[", ".").replace("]", "")

        if 'values_changed' in parsed_diff:
            diff_lines.append(f"  {Fore.YELLOW}{Style.BRIGHT}Modified Resource Kind: '{kind}'{Style.RESET_ALL}")
            for path, changes in parsed_diff['values_changed'].items():
                diff_lines.append(f"    ~ {clean_path(path)}")
                diff_lines.append(f"      {Fore.RED}- {changes['old_value']}{Style.RESET_ALL}")
                diff_lines.append(f"      {Fore.GREEN}+ {changes['new_value']}{Style.RESET_ALL}")
        
        # Add more detailed handlers if needed for other change types
        
        return diff_lines

    def process_mapping_file(
        self, file_path: str, dry_run: bool = False, force: bool = False
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Processes a single mapping file, checks for changes, and returns the desired state."""
        local_config = self.load_mapping_from_file(file_path)
        if not local_config:
            return False, "file_error", None

        integration_id = local_config.get('integrationIdentifier')
        if not integration_id:
            logger.error(f"Mapping file '{file_path}' is missing 'integrationIdentifier'.")
            self.has_failures = True
            return False, "config_error", None

        logger.info(f"Processing mapping for integration '{integration_id}'...")

        try:
            remote_integration = self.client.get_integration(integration_id)
            if not remote_integration:
                logger.error(f"Integration '{integration_id}' not found.")
                self.has_failures = True
                return False, "api_error", None
            remote_config = remote_integration.get("integration", {}).get("config", {})
        except PortAPIError as e:
            logger.error(f"Failed to fetch integration '{integration_id}': {e}")
            self.has_failures = True
            return False, "api_error", None

        # Build the desired state by updating remote config with local changes
        desired_config = remote_config.copy()
        desired_config.update(local_config)
        # We pop 'integrationIdentifier' as it's our metadata, not part of Port's config schema
        desired_config.pop('integrationIdentifier', None)

        # Compare the configurations
        diff = DeepDiff(remote_config, desired_config, ignore_order=True)

        if not diff:
            logger.info(f"No changes detected for integration '{integration_id}'.")
            return True, "no_changes", None

        # Format and display the diff
        report_lines = self._format_diff(diff)
        logger.info("\n" + "\n".join(report_lines))

        if dry_run:
            logger.info(f"\n{Fore.CYAN}[DRY RUN] Would apply changes to integration '{integration_id}'.{Style.RESET_ALL}")
            return True, "dry_run", None
        
        if not force:
            return True, "confirmation_required", desired_config

        # If force is true, proceed with the update
        return self.apply_mapping_update(integration_id, desired_config)

    def apply_mapping_update(self, integration_id: str, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Applies the configuration update to the integration."""
        logger.info(f"Applying new configuration to integration '{integration_id}'...")
        try:
            self.client.update_integration_config(integration_id, config)
            logger.info(f"Successfully updated configuration for integration '{integration_id}'.")
            return True, "updated"
        except PortAPIError as e:
            logger.error(f"Failed to update integration '{integration_id}': {e}")
            self.has_failures = True
            return False, "api_error"

    def _format_diff(self, diff: DeepDiff) -> list[str]:
        """Formats the full diff for display."""
        report_lines = ["Found differences in mapping configuration:"]
        parsed_diff = diff.to_dict()

        def clean_path(path_str):
            return path_str.replace("root", "config").replace("['", ".").replace("']", "").replace("[", ".").replace("]", "")

        if 'dictionary_item_added' in parsed_diff:
            for path in parsed_diff['dictionary_item_added']:
                report_lines.append(f"  {Fore.GREEN}+ Added: {clean_path(path)}{Style.RESET_ALL}")
        
        if 'dictionary_item_removed' in parsed_diff:
            for path in parsed_diff['dictionary_item_removed']:
                report_lines.append(f"  {Fore.RED}- Removed: {clean_path(path)}{Style.RESET_ALL}")
        
        if 'values_changed' in parsed_diff:
            for path, changes in parsed_diff['values_changed'].items():
                report_lines.append(f"  {Fore.YELLOW}~ Modified: {clean_path(path)}{Style.RESET_ALL}")
                report_lines.append(f"    {Fore.RED}- {changes['old_value']}{Style.RESET_ALL}")
                report_lines.append(f"    {Fore.GREEN}+ {changes['new_value']}{Style.RESET_ALL}")

        # You can add more handlers for list changes etc. if needed
        return report_lines 