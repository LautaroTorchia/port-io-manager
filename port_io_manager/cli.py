"""Command line interface for Port.io Manager."""

import os
import sys
import click
import logging
from typing import List, Optional
from .core.services import BlueprintService
from .api.client import PortAPIClient
from .utils.logger import setup_logging

logger = logging.getLogger(__name__)

@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
def cli(debug: bool):
    """Port.io Manager CLI."""
    setup_logging(debug)

@cli.command()
@click.argument('blueprint_paths', nargs=-1, type=click.Path(exists=True))
@click.option('--force', is_flag=True, help='Force update even if recently modified')
@click.option('--yes', is_flag=True, help='Skip confirmation prompts')
def sync(blueprint_paths: List[str], force: bool, yes: bool):
    """Synchronize blueprints with Port.io."""
    if not blueprint_paths:
        logger.error("No blueprint paths provided")
        sys.exit(1)

    client_id = os.getenv('PORT_CLIENT_ID')
    client_secret = os.getenv('PORT_CLIENT_SECRET')
    if not client_id or not client_secret:
        logger.error("PORT_CLIENT_ID and PORT_CLIENT_SECRET environment variables must be set")
        sys.exit(1)

    try:
        client = PortAPIClient(client_id, client_secret)
        service = BlueprintService(client)

        logger.info("Successfully authenticated with Port.io API")

        # Process each blueprint path
        valid_paths = []
        for path in blueprint_paths:
            if not os.path.exists(path):
                logger.error("Path does not exist: %s", path)
                continue
            if os.path.isfile(path) and path.endswith('.json'):
                valid_paths.append(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith('.json'):
                            valid_paths.append(os.path.join(root, file))

        if not valid_paths:
            logger.error("No valid blueprint files found")
            sys.exit(1)

        logger.info("Starting synchronization of %d blueprint(s)", len(valid_paths))
        logger.info("--------------------------------------------------")

        for path in valid_paths:
            if not service.process_blueprint_file(path, force, yes):
                continue
            logger.info("--------------------------------------------------")

        logger.info("Blueprint synchronization completed")
        if service.has_failures:
            logger.error("Some blueprints failed to synchronize. Please check the logs above for details.")
            sys.exit(1)

    except Exception as e:
        logger.error("Failed to synchronize blueprints: %s", str(e))
        logger.debug("Stack trace:", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    cli()
