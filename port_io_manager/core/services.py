import json
from typing import Dict, Optional, List
from datetime import datetime, timezone
from deepdiff import DeepDiff
from ..api.endpoints.blueprints import BlueprintClient

class BlueprintService:
    """Service class for managing blueprints and their synchronization."""

    def __init__(self, client: BlueprintClient):
        self.client = client

    def load_blueprint_from_file(self, file_path: str) -> Optional[Dict]:
        """Loads a blueprint from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                blueprint_data = json.load(f)
            return blueprint_data
        except json.JSONDecodeError:
            print(f"❌ Error: The file '{file_path}' is not valid JSON.")
            return None
        except FileNotFoundError:
            print(f"❌ Error: The file '{file_path}' was not found.")
            return None

    def format_diff_for_display(self, diff: DeepDiff) -> Dict:
        """Formats the DeepDiff object for clear display."""
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
        """Compares local and remote blueprints and shows differences."""
        exclude_paths = [
            "root['createdAt']",
            "root['updatedAt']",
            "root['createdBy']",
            "root['updatedBy']"
        ]
        diff = DeepDiff(remote_blueprint, local_blueprint, ignore_order=True, exclude_paths=exclude_paths)
        
        if not diff:
            print("✅ No differences found. Blueprint is synchronized.")
            return None

        print("🔎 Differences found:")
        formatted_diff = self.format_diff_for_display(diff)
        print(json.dumps(formatted_diff, indent=2, ensure_ascii=False))
        return formatted_diff

    def check_recent_update(self, blueprint_metadata: Dict, force_update: bool = False) -> bool:
        """Checks if the blueprint was recently updated in the UI."""
        if force_update:
            print("Forcing update (--force). Ignoring last modification date.")
            return True
        
        last_updated_str = blueprint_metadata.get('updatedAt')
        if not last_updated_str:
            return True

        last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
        time_difference = datetime.now(timezone.utc) - last_updated
        
        print(f"Last remote update: {last_updated}")
        if time_difference.total_seconds() < 86400:  # Less than 24 hours
            print("⚠️  Warning! Blueprint has been updated from the UI less than 24 hours ago.")
            return False
        return True

    def process_blueprint_file(self, file_path: str, force_update: bool = False, skip_confirmation: bool = False) -> None:
        """Processes a single blueprint file."""
        print(f"\n{'='*20} \n📂 Processing: {file_path} \n{'='*20}")
        
        local_blueprint_data = self.load_blueprint_from_file(file_path)
        if not local_blueprint_data:
            return

        blueprint_id = local_blueprint_data.get('identifier')
        if not blueprint_id:
            print(f"❌ Error: JSON in '{file_path}' must have an 'identifier' key.")
            return

        remote_blueprint = self.client.get_blueprint(blueprint_id)

        if remote_blueprint:
            diff = self.compare_blueprints(local_blueprint_data, remote_blueprint)
            if not diff:
                return

            if not self.check_recent_update(remote_blueprint, force_update) and not skip_confirmation:
                user_input = input("Do you want to continue and overwrite remote changes? (y/N): ")
                if user_input.lower() != 'y':
                    print("Operation aborted by user for this file.")
                    return
            elif skip_confirmation:
                print("Skipping confirmation due to --no-prompt flag.")
            
            print(f"Updating blueprint '{blueprint_id}'...")
            self.client.update_blueprint(blueprint_id, local_blueprint_data)
        else:
            print(f"Creating new blueprint '{blueprint_id}'...")
            self.client.create_blueprint(local_blueprint_data) 