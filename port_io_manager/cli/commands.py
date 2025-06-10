import os
import glob
import logging
import argparse
import sys
from typing import List
from dotenv import load_dotenv
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
            search_path = os.path.join(path, '*.json')
            dir_files = glob.glob(search_path)
            if not dir_files:
                logger.warning("No JSON files found in directory: %s", path)
            else:
                json_files.extend(dir_files)
    
    return list(dict.fromkeys(json_files))

def sync_blueprint_command(args: argparse.Namespace) -> None:
    """Handle the sync-blueprint command execution.

    Args:
        args: Parsed command line arguments
    """
    client = BlueprintClient(
        client_id=os.getenv("PORT_CLIENT_ID"),
        client_secret=os.getenv("PORT_CLIENT_SECRET")
    )
    service = BlueprintService(client)

    json_files = process_input_paths(args.files if args.files else args.directory)
    if not json_files:
        logger.error("No valid JSON files found to process")
        sys.exit(1)

    logger.info("Starting synchronization of %d blueprint(s)", len(json_files))
    
    for file_path in json_files:
        logger.info("-" * 50)
        service.process_blueprint_file(
            file_path, 
            force_update=args.force,
            skip_confirmation=args.no_prompt
        )
    
    logger.info("-" * 50)
    logger.info("Blueprint synchronization completed")
    
    if service.has_failures:
        logger.error("Some blueprints failed to synchronize. Please check the logs above for details.")
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
        help='Directory containing JSON files to process'
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

    sync_parser.set_defaults(func=sync_blueprint_command)

def main():
    """Main CLI entry point."""
    load_dotenv()
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Port.io resource manager - Infrastructure as Code tool"
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
    args.func(args) 