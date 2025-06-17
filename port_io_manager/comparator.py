from typing import Dict, Optional, List, Any
from deepdiff import DeepDiff

def format_diff_for_display(diff: DeepDiff) -> Dict[str, List[Dict[str, Any]]]:
    """Formats the DeepDiff object for a clear and correct visualization."""
    processed_diff = {
        'values_changed': [],
        'items_added_locally': [],
        'items_removed_locally': []
    }

    if 'values_changed' in diff:
        processed_diff['values_changed'] = [
            {'key': key.replace("root", "blueprint"), 'remote_value': value['old_value'], 'local_value': value['new_value']}
            for key, value in diff['values_changed'].items()
        ]
    if 'dictionary_item_added' in diff:
        processed_diff['items_added_locally'] = [
            {'key': item.replace("root", "blueprint")} for item in diff['dictionary_item_added']
        ]
    if 'dictionary_item_removed' in diff:
        processed_diff['items_removed_locally'] = [
            {'key': item.replace("root", "blueprint")} for item in diff['dictionary_item_removed']
        ]
    return processed_diff


class BlueprintComparator:
    """Specific comparator for Blueprints."""

    def compare(self, local_blueprint: Dict, remote_blueprint: Dict) -> Optional[DeepDiff]:
        """
        Compares a local blueprint with a remote one.

        Args:
            local_blueprint: The local blueprint dictionary.
            remote_blueprint: The remote blueprint dictionary.

        Returns:
            A DeepDiff object if differences are found, otherwise None.
        """
        exclude_paths = ["root['createdAt']", "root['updatedAt']", "root['createdBy']", "root['updatedBy']"]
        diff = DeepDiff(remote_blueprint, local_blueprint, ignore_order=True, exclude_paths=exclude_paths)
        
        if not diff:
            return None

        return diff
