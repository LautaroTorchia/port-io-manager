from deepdiff import DeepDiff

def format_diff_for_display(diff):
    """Formatea el objeto DeepDiff para una visualización clara y correcta."""
    processed_diff = {}
    if 'values_changed' in diff:
        processed_diff['values_changed'] = [
            {'key': key.replace("root", "blueprint"), 'remote_value': value['old_value'], 'local_value': value['new_value']}
            for key, value in diff['values_changed'].items()
        ]
    if 'dictionary_item_added' in diff:
        processed_diff['items_added_locally'] = [item.replace("root", "blueprint") for item in diff['dictionary_item_added']]
    if 'dictionary_item_removed' in diff:
        processed_diff['items_removed_locally'] = [item.replace("root", "blueprint") for item in diff['dictionary_item_removed']]
    return processed_diff


class BlueprintComparator:
    """Comparador específico para Blueprints."""

    def compare(self, local_blueprint, remote_blueprint):
        exclude_paths = ["root['createdAt']", "root['updatedAt']", "root['createdBy']", "root['updatedBy']"]
        diff = DeepDiff(remote_blueprint, local_blueprint, ignore_order=True, exclude_paths=exclude_paths)
        
        if not diff:
            print("✅ No se encontraron diferencias. El blueprint está sincronizado.")
            return None

        print("🔎 Diferencias encontradas:")
        return diff
