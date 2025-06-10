# Port.io Manager

A professional Infrastructure as Code (IaC) tool for managing Port.io resources. This tool allows you to manage Port.io resources (currently blueprints) using local JSON files, enabling version control and GitOps practices.

## Features

### Core Functionality
- Create and update Port.io blueprints from JSON files
- Compare local and remote blueprint configurations
- Detect and warn about recent UI changes
- Support for both single files and directories
- Detailed change visualization
- Comprehensive error reporting

### CLI Features
- Modern command-line interface with subcommands
- Support for multiple input methods:
  ```bash
  # Process single file
  port-io-manager sync-blueprint -f blueprint.json

  # Process multiple files
  port-io-manager sync-blueprint -f blueprint1.json,blueprint2.json

  # Process entire directory
  port-io-manager sync-blueprint -d blueprints/
  ```
- Force update option: `--force`
- Non-interactive mode: `--no-prompt`

### Professional Logging
- Structured logging with metadata
- Color-coded output for better readability
- Detailed error messages with API response information
- Clear change visualization
- Progress tracking and operation status

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd port_io_manager
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

## Configuration

Create a `.env` file in your project directory with your Port.io credentials:

```env
PORT_CLIENT_ID=your_client_id
PORT_CLIENT_SECRET=your_client_secret
```

## Usage

### Basic Usage

1. Create or update a single blueprint:
```bash
port-io-manager sync-blueprint -f path/to/blueprint.json
```

2. Process multiple blueprints:
```bash
port-io-manager sync-blueprint -f blueprint1.json,blueprint2.json
```

3. Process all blueprints in a directory:
```bash
port-io-manager sync-blueprint -d path/to/blueprints/
```

### Advanced Options

- Force update (ignore recent UI changes):
```bash
port-io-manager sync-blueprint -f blueprint.json --force
```

- Skip confirmation prompts:
```bash
port-io-manager sync-blueprint -d blueprints/ --no-prompt
```

### Example Output

```
[Port.io Manager] - 2024-03-14 10:30:15 - INFO - Starting synchronization of 2 blueprint(s)
[Port.io Manager] - 2024-03-14 10:30:15 - INFO - Processing blueprint file: service.json
[Port.io Manager] - 2024-03-14 10:30:15 - INFO - Found differences between local and remote blueprints:
[Port.io Manager] - 2024-03-14 10:30:15 - INFO - Modified values:
[Port.io Manager] - 2024-03-14 10:30:15 - INFO -   Field: blueprint['title']
[Port.io Manager] - 2024-03-14 10:30:15 - INFO -     - Remote: ServiceOld
[Port.io Manager] - 2024-03-14 10:30:15 - INFO -     + Local:  ServiceNew
```

## Project Structure

```
port_io_manager/
├── api/                    # API interaction layer
│   ├── client.py          # Base API client
│   └── endpoints/         # Endpoint-specific clients
├── core/                  # Business logic
│   └── services.py       # Core services
├── cli/                   # CLI interface
│   └── commands.py       # CLI commands
└── utils/                # Utilities
    └── logger.py        # Logging configuration
```

## Architecture

The project follows a clean, modular architecture:

1. **API Layer** (`api/`):
   - Base client with authentication and request handling
   - Endpoint-specific clients for different Port.io resources
   - Comprehensive error handling and reporting

2. **Core Layer** (`core/`):
   - Business logic for blueprint management
   - Change detection and comparison
   - File handling and validation

3. **CLI Layer** (`cli/`):
   - Command-line interface with subcommands
   - Argument parsing and validation
   - User interaction handling

4. **Utils** (`utils/`):
   - Professional logging with metadata
   - Color-coded output
   - Reusable utilities

## Error Handling

The tool provides detailed error information:

- API errors with response details
- Validation errors with specific fields
- Configuration and file errors
- Network and authentication issues

## Future Enhancements

- Support for additional Port.io resources
- Git integration for change detection
- Batch operations and rollback support
- Extended validation capabilities
- CI/CD pipeline integration

## Contributing

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Submit a pull request

## License

[License Type] - See LICENSE file for details 