import logging
import colorama
from datetime import datetime
from colorama import Fore, Style

# Initialize colorama for cross-platform color support
colorama.init()

class ColoredFormatter(logging.Formatter):
    """Custom formatter adding colors and metadata to log messages."""
    
    COLORS = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Color the level name
        level_color = self.COLORS.get(record.levelname, '')
        level_name = f"{level_color}{record.levelname}{Style.RESET_ALL}"

        # Format with metadata, using fixed module name
        record.metadata = f"[Port.io Manager] - {timestamp} - {level_name} -"
        
        # Add colors to specific keywords in the message
        if "differences found" in record.msg.lower():
            record.msg = f"{Fore.YELLOW}{record.msg}{Style.RESET_ALL}"
        elif "updated" in record.msg.lower():
            record.msg = f"{Fore.GREEN}{record.msg}{Style.RESET_ALL}"
        elif "error" in record.msg.lower():
            record.msg = f"{Fore.RED}{record.msg}{Style.RESET_ALL}"

        return super().format(record)

def setup_logging():
    """Configure logging with custom formatter and handlers."""
    formatter = ColoredFormatter('%(metadata)s %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers and add our custom handler
    root_logger.handlers = []
    root_logger.addHandler(console_handler)

    # Prevent propagation of messages to parent loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING) 