import logging
import yaml
from typing import Dict, Optional, Tuple, Any, List

from deepdiff import DeepDiff
from colorama import Fore, Style

from ..api.client import PortAPIError
# Asumo que esta importación es correcta para tu estructura de proyecto
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

    def process_mapping_file(
        self, file_path: str, dry_run: bool = False, force: bool = False
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Processes a single mapping file, checks for changes, and returns the desired state."""
        local_config = self.load_mapping_from_file(file_path)
        if not local_config:
            return False, "file_error", None

        integration_id = local_config.get('integrationIdentifier')
        if not integration_id:
            logger.error(
                f"Mapping file '{file_path}' is missing 'integrationIdentifier'.")
            self.has_failures = True
            return False, "config_error", None

        logger.info(f"Processing mapping for integration '{integration_id}'...")

        try:
            remote_integration = self.client.get_integration(integration_id)
            if not remote_integration:
                logger.error(f"Integration '{integration_id}' not found.")
                self.has_failures = True
                return False, "api_error", None
            remote_config = remote_integration.get(
                "integration", {}).get("config", {})
        except PortAPIError as e:
            logger.error(f"Failed to fetch integration '{integration_id}': {e}")
            self.has_failures = True
            return False, "api_error", None

        desired_config = remote_config.copy()
        desired_config.update(local_config)
        desired_config.pop('integrationIdentifier', None)

        diff = DeepDiff(remote_config, desired_config, ignore_order=True)

        if not diff:
            logger.info(f"No changes detected for integration '{integration_id}'.")
            return True, "no_changes", None

        report_lines = self._format_diff(diff)
        logger.info("\n" + "\n".join(report_lines))

        if dry_run:
            logger.info(
                f"\n{Fore.CYAN}[DRY RUN] Would apply changes to integration '{integration_id}'.{Style.RESET_ALL}")
            return True, "dry_run", None

        change_data = {
            "integration_id": integration_id,
            "config": desired_config
        }

        if not force:
            return True, "confirmation_required", change_data

        success, status = self.apply_mapping_update(
            change_data["integration_id"], change_data["config"])
        return success, status, None

    def apply_mapping_update(self, integration_id: str, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Applies the configuration update to the integration."""
        logger.info(
            f"Applying new configuration to integration '{integration_id}'...")
        try:
            self.client.update_integration_config(integration_id, config)
            logger.info(
                f"Successfully updated configuration for integration '{integration_id}'.")
            return True, "updated"
        except PortAPIError as e:
            if e.status_code == 422:
                logger.error(
                    f"Failed to update integration '{integration_id}': 422 Error code, indicating that the integration is not supported for the given resource kind")
            self.has_failures = True
            return False, "api_error"

    def _clean_diff_path(self, path_str: str) -> str:
        """Cleans the deepdiff path for better readability."""
        return path_str.replace("root", "config").replace("['", ".").replace("']", "").replace("[", ".").replace("]", "")

    def _format_dict_recursively(self, data: Any, indent_level: int) -> List[str]:
        """Recursively formats a dictionary or list for display."""
        lines = []
        indent = "  " * indent_level
        if isinstance(data, dict):
            # Comprobación de seguridad
            if not data:
                return []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{indent}{key}:")
                    lines.extend(self._format_dict_recursively(
                        value, indent_level + 1))
                else:
                    lines.append(f"{indent}{key}: {value}")
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    lines.extend(self._format_dict_recursively(
                        item, indent_level + 1))
                else:
                    lines.append(f"{indent}- {item}")
        return lines

    def _format_resource_block(self, resource_data: Dict[str, Any]) -> str:
        """Formats a resource block for display safely."""
        lines = []
        kind = resource_data.get('kind', 'unknown')
        lines.append(f"  Kind: {kind}")
        
        # Usar .get() para evitar KeyErrors y comprobar si es un diccionario
        selector = resource_data.get('selector')
        if isinstance(selector, dict):
            lines.append("  Selector:")
            lines.extend(self._format_dict_recursively(selector, 2))

        port = resource_data.get('port')
        if isinstance(port, dict):
            lines.append("  Port Configuration:")
            lines.extend(self._format_dict_recursively(port, 2))

        return "\n".join(lines)

    def _format_diff(self, diff: DeepDiff) -> list[str]:
        """Formats the full diff for display."""
        report_lines = ["Found differences in mapping configuration:"]
        parsed_diff = diff.to_dict()

        # --- Handle ADDED items ---
        if 'iterable_item_added' in parsed_diff:
            added_items = parsed_diff['iterable_item_added']
            # Comprobación de seguridad
            if isinstance(added_items, dict):
                report_lines.append(
                    f"\n{Fore.GREEN}{Style.BRIGHT}Added Resources:{Style.RESET_ALL}")
                for path, block in added_items.items():
                    if 'resources' in path and isinstance(block, dict):
                        report_lines.append(f"{Fore.GREEN}+ New Resource Block:{Style.RESET_ALL}")
                        report_lines.append(self._format_resource_block(block))
                    else:
                        report_lines.append(f"{Fore.GREEN}+ Added: {self._clean_diff_path(path)}{Style.RESET_ALL}")
                        lines = self._format_dict_recursively(block, 1)
                        report_lines.extend(f"  {line}" for line in lines)

        # --- Handle REMOVED items ---
        if 'iterable_item_removed' in parsed_diff:
            removed_items = parsed_diff['iterable_item_removed']
            # Comprobación de seguridad
            if isinstance(removed_items, dict):
                report_lines.append(
                    f"\n{Fore.RED}{Style.BRIGHT}Removed Resources:{Style.RESET_ALL}")
                for path, block in removed_items.items():
                    if 'resources' in path and isinstance(block, dict):
                        report_lines.append(f"{Fore.RED}- Removed Resource Block:{Style.RESET_ALL}")
                        report_lines.append(self._format_resource_block(block))
                    else:
                        report_lines.append(f"{Fore.RED}- Removed: {self._clean_diff_path(path)}{Style.RESET_ALL}")
                        lines = self._format_dict_recursively(block, 1)
                        report_lines.extend(f"  {line}" for line in lines)

        # --- Handle MODIFIED values ---
        if 'values_changed' in parsed_diff:
            changed_items = parsed_diff['values_changed']
            # Comprobación de seguridad
            if isinstance(changed_items, dict):
                 report_lines.append(
                    f"\n{Fore.YELLOW}{Style.BRIGHT}Modified Fields:{Style.RESET_ALL}")
                 for path, changes in changed_items.items():
                    cleaned_path = self._clean_diff_path(path)
                    report_lines.append(f"  ~ {cleaned_path}")
                    report_lines.append(f"    {Fore.RED}- {changes['old_value']}{Style.RESET_ALL}")
                    report_lines.append(f"    {Fore.GREEN}+ {changes['new_value']}{Style.RESET_ALL}")
        
        # Puedes añadir manejadores para 'dictionary_item_added/removed' si son necesarios,
        # siguiendo el mismo patrón de seguridad.

        return report_lines