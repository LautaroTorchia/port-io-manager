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
        self, file_path: str, dry_run: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Processes a single mapping file."""
        local_config = self.load_mapping_from_file(file_path)
        if not local_config:
            return False, None

        integration_id = local_config.pop('integrationIdentifier', None)
        if not integration_id:
            logger.error(f"Mapping file '{file_path}' is missing the required 'integrationIdentifier' key at the root.")
            self.has_failures = True
            return False, None

        logger.info(f"Processing mapping file for integration '{integration_id}': {file_path}")

        try:
            remote_integration = self.client.get_integration(integration_id)
            if not remote_integration:
                logger.error(f"Integration '{integration_id}' not found.")
                self.has_failures = True
                return False, None
            remote_config = remote_integration.get("integration", {}).get("config", {})
        except PortAPIError as e:
            logger.error(f"Failed to fetch integration '{integration_id}': {e}")
            self.has_failures = True
            return False, None
            
        # --- New Granular Diff Logic ---
        report_lines = ["Found differences in mapping configuration:"]
        has_changes = False

        # 1. Compare top-level keys (anything except 'resources')
        top_level_local = {k: v for k, v in local_config.items() if k != 'resources'}
        top_level_remote = {k: v for k, v in remote_config.items() if k != 'resources'}
        top_level_diff = DeepDiff(top_level_remote, top_level_local, ignore_order=True)

        if top_level_diff:
            has_changes = True
            # For simplicity, we log the top-level changes directly. Can be enhanced later.
            report_lines.append(f"  {Fore.YELLOW}{Style.BRIGHT}Modified top-level attributes:{Style.RESET_ALL}")
            for change_type, changes in top_level_diff.to_dict().items():
                 report_lines.append(f"    - {change_type}: {changes}")
        
        # 2. Compare resources granularly by 'kind'
        local_resources = {res['kind']: res for res in local_config.get('resources', [])}
        remote_resources = {res['kind']: res for res in remote_config.get('resources', [])}
        all_kinds = set(local_resources.keys()) | set(remote_resources.keys())

        for kind in sorted(list(all_kinds)):
            local_res = local_resources.get(kind)
            remote_res = remote_resources.get(kind)

            if local_res and not remote_res:
                has_changes = True
                report_lines.append(f"  {Fore.GREEN}{Style.BRIGHT}Added Resource Kind: '{kind}'{Style.RESET_ALL}")
            elif not local_res and remote_res:
                has_changes = True
                report_lines.append(f"  {Fore.RED}{Style.BRIGHT}Removed Resource Kind: '{kind}'{Style.RESET_ALL}")
            elif local_res and remote_res:
                diff = DeepDiff(remote_res, local_res, ignore_order=True)
                if diff:
                    has_changes = True
                    report_lines.extend(self._format_diff_details(diff, kind))
        
        if not has_changes:
            logger.info(f"No changes detected for integration '{integration_id}'.")
            return True, None
        
        logger.info("\n" + "\n".join(report_lines))

        # --- Execution Logic (remains the same) ---
        # Build the final desired state that will be sent to the API
        desired_config = remote_config.copy()
        desired_config.update(local_config)

        if dry_run:
            logger.info(f"\n{Fore.CYAN}[DRY RUN] Configuration for integration '{integration_id}' will be updated as shown above.{Style.RESET_ALL}")
            return True, None
            
        try:
            logger.info(f"Applying new configuration to integration '{integration_id}'...")
            self.client.update_integration_config(integration_id, desired_config)
            logger.info(f"Successfully updated configuration for integration '{integration_id}'.")
            return True, None
        except PortAPIError as e:
            logger.error(f"Failed to update integration '{integration_id}': {e}")
            self.has_failures = True
            return False, None 