"""Logging configuration for the Port.io Manager."""

import logging
import sys
import os
from typing import Dict

# Using colorama for cross-platform colored logging
from colorama import Fore, Style, init

# Initialize colorama for cross-platform colored output
init(autoreset=True)

class ColorFormatter(logging.Formatter):
    """A custom logging formatter that adds color to log levels for console output."""

    LOG_COLORS: Dict[int, str] = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.WHITE,  # Standard info is neutral
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }
    
    # Custom prefixes for styling
    PREFIXES: Dict[int, str] = {
        logging.DEBUG: f"{Fore.CYAN}DEBUG{Style.RESET_ALL}",
        logging.INFO: f"{Fore.GREEN}INFO{Style.RESET_ALL}",
        logging.WARNING: f"{Fore.YELLOW}WARN{Style.RESET_ALL}",
        logging.ERROR: f"{Fore.RED}ERROR{Style.RESET_ALL}",
        logging.CRITICAL: f"{Fore.RED}{Style.BRIGHT}CRITICAL{Style.RESET_ALL}",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Formats a log record with color and a simple prefix."""
        log_color = self.LOG_COLORS.get(record.levelno, Fore.WHITE)
        prefix = self.PREFIXES.get(record.levelno, "")
        
        # For INFO, we just show the message without a prefix for a cleaner look
        if record.levelno == logging.INFO:
            return f"{log_color}{record.getMessage()}"
            
        # For other levels, add the styled prefix
        return f"{prefix}: {log_color}{record.getMessage()}"

def setup_logging(debug: bool = False) -> None:
    """Configure logging for the application.
    
    Args:
        debug: Whether to enable debug logging
    """
    log_level = logging.DEBUG if debug else logging.INFO
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers to prevent duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console Handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(ColorFormatter())
    root_logger.addHandler(console_handler)

    # File Handler (optional, only if env var is set)
    log_file = os.getenv('PORT_LOG_FILE')
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(log_level)
        # File logger should not have color codes
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress overly verbose logs from third-party libraries
    if not debug:
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("deepdiff").setLevel(logging.WARNING) 