import os
import glob
import argparse
from typing import List
from dotenv import load_dotenv
from ..api.endpoints.blueprints import BlueprintClient
from ..core.services import BlueprintService

def process_input_paths(input_paths: str) -> List[str]:
    """
    Processes input paths and returns a list of JSON files to process.
    Accepts:
    - A directory path
    - A single JSON file path
    - Multiple JSON file paths separated by commas
    """
    json_files = []
    paths = [p.strip() for p in input_paths.split(',')]

    for path in paths:
        if not os.path.exists(path):
            print(f"❌ Error: Path '{path}' does not exist.")
            continue

        if os.path.isfile(path):
            if path.endswith('.json'):
                json_files.append(path)
            else:
                print(f"❌ Error: File '{path}' is not a JSON file.")
        elif os.path.isdir(path):
            search_path = os.path.join(path, '*.json')
            dir_files = glob.glob(search_path)
            if not dir_files:
                print(f"ℹ️ No JSON files found in directory '{path}'.")
            else:
                json_files.extend(dir_files)
    
    # Remove duplicates while preserving order
    return list(dict.fromkeys(json_files))

def sync_blueprint_command(args: argparse.Namespace) -> None:
    """Handler for the sync-blueprint command."""
    # Initialize clients and services
    client = BlueprintClient(
        client_id=os.getenv("PORT_CLIENT_ID"),
        client_secret=os.getenv("PORT_CLIENT_SECRET")
    )
    service = BlueprintService(client)

    # Process input paths based on source type
    if args.files:
        json_files = process_input_paths(args.files)
    else:
        json_files = process_input_paths(args.directory)

    if not json_files:
        print("No valid JSON files found to process.")
        return

    total_files = len(json_files)
    print(f"\n🚀 Processing {total_files} blueprint(s).")

    for file_path in json_files:
        service.process_blueprint_file(
            file_path, 
            force_update=args.force,
            skip_confirmation=args.no_prompt
        )
    
    print(f"\n✨ Process completed. Processed {total_files} file(s).")

def setup_sync_blueprint_parser(subparsers: argparse._SubParsersAction) -> None:
    """Sets up the parser for the sync-blueprint command."""
    sync_parser = subparsers.add_parser(
        'sync-blueprint',
        help='Synchronize blueprints from local JSON files to Port.io',
        description='Create or update blueprints in Port.io using local JSON files.'
    )

    # Create a mutually exclusive group for input source
    source_group = sync_parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        '-f', '--files',
        help='Comma-separated list of JSON files to process'
    )
    source_group.add_argument(
        '-d', '--directory',
        help='Directory containing JSON files to process'
    )

    # Add flags for force update and no prompt
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
    # Load environment variables
    load_dotenv()

    # Create main parser
    parser = argparse.ArgumentParser(
        description="Port.io resource manager - Infrastructure as Code tool"
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(
        title='commands',
        description='valid commands',
        help='additional help',
        dest='command'
    )
    subparsers.required = True

    # Set up parsers for each command
    setup_sync_blueprint_parser(subparsers)

    # Parse arguments and execute appropriate command
    args = parser.parse_args()
    args.func(args) 