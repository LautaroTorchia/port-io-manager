import json
import logging

logger = logging.getLogger(__name__)

def sanitize_diff(diff):
    """Sanitiza el objeto DeepDiff para ser serializado y manejado."""
    if 'values_changed' in diff:
        for key, value in diff['values_changed'].items():
            if isinstance(value, set):
                diff['values_changed'][key] = list(value)
    return diff
