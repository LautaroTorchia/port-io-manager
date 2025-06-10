import os
import glob
import logging
import argparse
import sys
from typing import List
from dotenv import load_dotenv
from ..api.client import PortAPIClient
from ..api.endpoints.blueprints import BlueprintClient
from ..core.services import BlueprintService
from ..utils.logger import setup_logging

logger = logging.getLogger(__name__)

def process_input_paths(input_paths: str) -> List[str]:
    """Process input paths and return a list of JSON files.

    Handles multiple input types:
    - Single JSON file path
    - Multiple JSON file paths (comma-separated)
    - Directory path(s)

    Args:
        input_paths: Comma-separated list of file or directory paths

    Returns:
        List of JSON file paths to process
    """
    json_files = []
    paths = [p.strip() for p in input_paths.split(',')]

    for path in paths:
        if not os.path.exists(path):
            logger.error("Path does not exist: %s", path)
            continue

        if os.path.isfile(path):
            if path.endswith('.json'):
                json_files.append(path)
            else:
                logger.error("Not a JSON file: %s", path)
        elif os.path.isdir(path):
            # Recursively find all JSON files in directory
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith('.json'):
                        json_files.append(os.path.join(root, file))
            if not any(f.endswith('.json') for f in json_files):
                logger.warning("No JSON files found in directory: %s", path)
    
    return list(dict.fromkeys(json_files))

def sync_blueprint_command(args: argparse.Namespace) -> None:
    """Handle the sync-blueprint command execution.

    Args:
        args: Parsed command line arguments
    """
    client_id = os.getenv("PORT_CLIENT_ID")
    client_secret = os.getenv("PORT_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.error("PORT_CLIENT_ID and PORT_CLIENT_SECRET environment variables must be set")
        sys.exit(1)

    try:
        # Initialize API client and services
        api_client = PortAPIClient(client_id, client_secret)
        blueprint_client = BlueprintClient(api_client)
        service = BlueprintService(blueprint_client)

        # Process input paths
        json_files = process_input_paths(args.files if args.files else args.directory)
        if not json_files:
            logger.error("No valid JSON files found to process")
            sys.exit(1)

        logger.info("Starting synchronization of %d blueprint(s)", len(json_files))
        logger.info("--------------------------------------------------")

        for file_path in json_files:
            service.process_blueprint_file(
                file_path, 
                force_update=args.force,
                skip_confirmation=args.no_prompt
            )

        logger.info("Blueprint synchronization completed")
        if service.has_failures:
            sys.exit(1)

    except Exception as e:
        logger.error("Failed to synchronize blueprints: %s", str(e))
        logger.debug("Stack trace:", exc_info=True)
        sys.exit(1)

def setup_sync_blueprint_parser(subparsers: argparse._SubParsersAction) -> None:
    """Set up the parser for the sync-blueprint command.

    Args:
        subparsers: Subparser collection to add to
    """
    sync_parser = subparsers.add_parser(
        'sync-blueprint',
        help='Synchronize blueprints from local JSON files to Port.io',
        description='Create or update blueprints in Port.io using local JSON files.'
    )

    source_group = sync_parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        '-f', '--files',
        help='Comma-separated list of JSON files to process'
    )
    source_group.add_argument(
        '-d', '--directory',
        help='Directory containing JSON files to process (recursive)'
    )

    sync_parser.add_argument(
        '--force',
        action='store_true',
        help='Force update, ignoring last modification date'
    )
    sync_parser.add_argument(
        '--no-prompt',
        action='store_true',
        help='Skip confirmation prompts'
    )
    sync_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    sync_parser.set_defaults(func=sync_blueprint_command)

def main():
    """Main CLI entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Port.io resource manager - Infrastructure as Code tool"
    )
    
    # Add global debug flag
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    subparsers = parser.add_subparsers(
        title='commands',
        description='valid commands',
        help='additional help',
        dest='command'
    )
    subparsers.required = True

    setup_sync_blueprint_parser(subparsers)

    args = parser.parse_args()
    
    # Setup logging with debug flag
    setup_logging(args.debug)
    
    args.func(args) 