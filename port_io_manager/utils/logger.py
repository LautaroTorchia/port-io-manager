"""Logging configuration for the Port.io Manager."""

import os
import logging
import logging.config
from typing import Optional

def setup_logging(debug: bool = False) -> None:
    """Configure logging for the application.
    
    Args:
        debug: Whether to enable debug logging
    """
    log_level = logging.DEBUG if debug else logging.INFO
    
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '[Port.io Manager] - %(asctime)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'debug': {
                'format': '[Port.io Manager] - %(asctime)s - %(levelname)s - %(name)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'debug' if debug else 'standard',
                'level': log_level,
                'stream': 'ext://sys.stdout'
            },
            'error_console': {
                'class': 'logging.StreamHandler',
                'formatter': 'debug' if debug else 'standard',
                'level': logging.ERROR,
                'stream': 'ext://sys.stderr'
            }
        },
        'loggers': {
            'port_io_manager': {
                'handlers': ['console', 'error_console'],
                'level': log_level,
                'propagate': False
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['console', 'error_console']
        }
    }

    # Create log directory if specified
    log_file = os.getenv('PORT_LOG_FILE')
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        logging_config['handlers']['file'] = {
            'class': 'logging.FileHandler',
            'formatter': 'debug',
            'filename': log_file,
            'mode': 'a'
        }
        logging_config['loggers']['port_io_manager']['handlers'].append('file')
        logging_config['root']['handlers'].append('file')

    logging.config.dictConfig(logging_config) 