# Port.io Manager

**Port.io Manager** is a command-line interface (CLI) tool designed to manage [Port.io](https://www.getport.io/) resources using an Infrastructure as Code (IaC) approach. It allows you to define your Port configurations (Blueprints, Scorecards, Integration Mappings) in local files (JSON/YAML) and synchronize them with the Port.io platform, enabling a GitOps-style workflow for your internal developer portal.

This prototype provides a solid foundation for managing your Port.io environment, ensuring consistency, version control, and automated deployments.

[![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)
[![Issues](https://img.shields.io/github/issues/your-repo/port-io-manager)](https://github.com/your-repo/port-io-manager/issues) <!-- TODO: Update with actual repo link -->

---

## 🚀 Core Functionality

The main goal of this tool is to synchronize local configuration files with the Port.io API. It makes the local files the **single source of truth**.

The synchronization process follows these steps:
1.  **Load Local State:** Read the resource definitions from your local files (`.json` or `.yaml`).
2.  **Fetch Remote State:** Query the Port.io API to get the current configuration.
3.  **Compare and Diff:** Compare the local and remote states to identify differences.
4.  **Display Plan:** Show a clear, color-coded execution plan (`--dry-run`) detailing what will be created, updated, or deleted.
5.  **Apply Changes:** Upon confirmation (or if running without `--dry-run`), apply the changes via the Port.io API.

This enables a robust **GitOps workflow**:
-   Define all your Port.io resources in a Git repository.
-   Use Pull Requests to review changes.
-   Automate the synchronization process in a CI/CD pipeline to apply changes upon merging.

## 📦 Supported Resources

The prototype currently supports managing the following Port.io resources:

| Resource    | File Format | Sync Command                  | Description                                                                                             |
|-------------|-------------|-------------------------------|---------------------------------------------------------------------------------------------------------|
| **Blueprints**  | JSON        | `sync-blueprint`              | Synchronizes a single Port.io Blueprint. It manages properties, relations, and other configurations.      |
| **Mappings**    | YAML        | `sync-mapping`                | Synchronizes the `entity-mappings` for a Port.io Integration. Supports a "prune" behavior by default. |
| **Scorecards**  | JSON        | `sync-scorecard`              | Synchronizes individual Scorecards for a given Blueprint. Supports aggregation of multiple files.     |

## 🛠️ Available Commands

The CLI is organized into logical groups for each resource type.

### `sync-blueprint`
Synchronizes a single Blueprint from a JSON file.

```bash
port-io-manager sync-blueprint --file <path-to-blueprint.json> [--dry-run]
```
-   `--file`: Path to the Blueprint definition file.
-   `--dry-run`: (Optional) Show a plan of changes without applying them.

### `sync-mapping`
Synchronizes Integration Mappings from a YAML file.

```bash
port-io-manager sync-mapping --file <path-to-mapping.yaml> [--dry-run]
```
-   `--file`: Path to the Integration Mapping definition file.
-   `--dry-run`: (Optional) Show a plan of changes without applying them.

### `sync-scorecard`
Synchronizes one or more Scorecards from JSON files. If multiple files target the same blueprint, they are merged before syncing.

```bash
port-io-manager sync-scorecard --files <path1.json> [<path2.json>...] [--dry-run]
```
-   `--files`: One or more paths to Scorecard definition files.
-   `--dry-run`: (Optional) Show a plan of changes without applying them.

---

## 🔧 Installation and Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd port-io-manager
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies and the CLI:**
    ```bash
    pip install -e .
    ```
    The `-e` flag installs the package in "editable" mode, so changes to the source code are immediately reflected.

4.  **Configure Credentials:**
    Create a `.env` file in the root of the project and add your Port.io API credentials:
    ```env
    PORT_CLIENT_ID="<your-port-client-id>"
    PORT_CLIENT_SECRET="<your-port-client-secret>"
    ```

## Extend the Prototype

This tool is built with modularity in mind, making it easy to extend. To add support for a new Port.io resource (e.g., `Action` or `Report`), you would typically follow these steps:

1.  **Create an API Client:** Add a new client in `port_io_manager/api/endpoints/` to handle the specific API requests for the new resource.
2.  **Implement the Core Service:** Create a new service in `port_io_manager/core/` that contains the business logic for fetching, comparing, and syncing the resource.
3.  **Expose a CLI Command:** Add a new command in `port_io_manager/cli/commands.py` to expose the new functionality to the user.
4.  **Add Examples:** Provide example configuration files in the `examples/` directory.

## 🤝 Contributing

This prototype is just the beginning! Contributions, bug reports, and feature requests are highly welcome.

-   **Found a bug?** Please [open an issue](https://github.com/your-repo/port-io-manager/issues) and provide detailed steps to reproduce it.
-   **Have a feature idea?** Open an issue to discuss the proposal. We would love to hear your thoughts.
-   **Want to contribute code?** Fork the repository, make your changes, and submit a Pull Request.

Together, we can build a powerful and comprehensive IaC tool for the Port.io ecosystem. 