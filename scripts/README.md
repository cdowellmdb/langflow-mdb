# Langflow Component Removal Script

Amongst other things, this repository contains a script to remove specified components and unused dependencies from the Langflow project. The script reads configuration from a YAML file and executes the necessary commands to clean up the project.

## Getting Started

### Configuration

Before running the script, you need to specify which components to remove in the `component_config.yml` file located in the `scripts` directory. The configuration format is as follows:

```yaml
components_to_remove:
  - <component_name>  # Specify component directories to remove
  - <component_name>: # Specify a directory for the file you want to remove
      files:
        - <file_name>  # Specify files to remove within the parent directory
```

## Usage

1. **Edit the Configuration File:** Open `component_config.yml` and specify the components and files you want to remove.

2. **Run the Script:** Execute the `remove_components.py` script from the command line:

```bash
cd scripts && uv run python remove_components.py
```

3. **Review the Output:** The script will log the removal process, including any unused dependencies identified by the `deptry` command.

### Notes
- The script will remove entire directories if no specific files are listed.
- If there are unused dependencies, the script will attempt to remove them automatically.
- **Ensure you have backups or version control in place before running the script to prevent accidental data loss.**