# Port.io Manager

A tool for managing Port.io resources through Infrastructure as Code. This tool allows you to manage Port.io resources (currently blueprints) using local JSON files, enabling version control and Infrastructure as Code practices.

## Features

- Manage Port.io blueprints through JSON files
- Compare local and remote blueprint configurations
- Create and update blueprints
- Detect and warn about recent UI changes
- Support for both single files and directories

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

The tool can be used to process either a single JSON file or a directory containing multiple JSON files:

```bash
# Process a single blueprint file
port-io-manager path/to/blueprint.json

# Process all JSON files in a directory
port-io-manager path/to/blueprints/

# Force update (ignore recent UI changes warning)
port-io-manager path/to/blueprint.json --force
```

### JSON File Format

Your blueprint JSON files should follow this structure:

```json
{
    "identifier": "unique_blueprint_id",
    "title": "Blueprint Title",
    "icon": "Blueprint Icon",
    "schema": {
        "properties": {
            // Blueprint properties
        }
    }
    // Other blueprint configurations
}
```

## Development

To set up the development environment:

1. Clone the repository
2. Create a virtual environment
3. Install development dependencies:
```bash
pip install -e .
```

## License

[License Type] - See LICENSE file for details 