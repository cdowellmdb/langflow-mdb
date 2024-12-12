"""This script removes specified component directories and unused dependencies from the project. It uses a YAML configuration file to identify components to remove and leverages the `deptry` tool to detect unused dependencies."""

import re
import subprocess
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "scripts" / "component_config.yml"
COMPONENTS_DIR = PROJECT_ROOT / "src" / "backend" / "base" / "langflow" / "components"


def remove_component_dirs(components):
    """Removes the specified components. Components can be either entire directories or specific files within them.

    Args:
        components (list): A list of components to remove. Each component can be:
          - A string: representing a directory to remove entirely.
          - A dict: representing a directory with a 'files' list of specific files to remove.
    """
    print("Starting to remove specified components...")
    print(f"Components to remove: {components}")

    for comp in components:
        # Handle either a string or a dict with {component_name: {files: [...]}}
        if isinstance(comp, str):
            # Entire directory removal
            dir_name = comp
            files_to_remove = None
        elif isinstance(comp, dict):
            # Dictionary specifying a directory and possibly files
            dir_name = list(comp.keys())[0]
            files_to_remove = comp[dir_name].get("files", [])
        else:
            print(f"Unsupported component format: {comp}")
            continue

        comp_path = COMPONENTS_DIR / dir_name
        print(f"Checking component: {comp_path}")

        if comp_path.is_dir():
            if files_to_remove:
                # Remove only specified files
                for file_name in files_to_remove:
                    file_path = comp_path / file_name
                    if file_path.is_file():
                        print(f"Removing file: {file_path}")
                        file_path.unlink()
                    else:
                        print(f"File not found or not a file: {file_path}")
                # If no other files left, and you want to keep directory, do nothing.
                # Directory stays if not explicitly removed.
            else:
                # No files specified, remove entire directory
                print(f"Removing entire directory: {comp_path}")
                for file_path in comp_path.glob("**/*"):
                    if file_path.is_file():
                        print(f"Removing file: {file_path}")
                        file_path.unlink()
                comp_path.rmdir()
        else:
            print(f"Directory does not exist: {comp_path}")

    print("Finished removing specified components.")


def run_deptry(verbose=False):
    """Runs `deptry` to identify unused dependencies.

    Args:
        verbose (bool): If True, print the output of the `deptry` command.

    Returns:
        str: The output of the `deptry` command.
    """
    print("Running `deptry` to identify unused dependencies...")
    result = subprocess.run(
        ["uv", "run", "deptry", "."],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=PROJECT_ROOT,
    )
    if verbose:
        print("Deptry combined output:")
        print(result.stdout)
    return result.stdout


def remove_unused_dependencies(deptry_output, remove_optional=True):
    print("Starting to remove unused dependencies...")
    unused_deps = []
    for line in deptry_output.splitlines():
        print(f"Analyzing line: {line}")
        if "DEP002" in line:
            dep = line.split("'")[1]
            print(f"Identified unused dependency: {dep}")
            unused_deps.append(dep)

    if not unused_deps:
        print("No unused dependencies found.")
        return

    for dep in unused_deps:
        print(f"Removing unused dependency: {dep}")
        # Run uv remove with capture to analyze output on failure
        result = subprocess.run(
            ["uv", "remove", dep], capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        if result.returncode != 0:
            print(f"Warning: Failed to remove {dep} normally. Output:")
            print(result.stdout)
            print(result.stderr)

            if remove_optional:
                # Try to parse the suggested optional keyword
                # Looking for a line like: "try calling `uv remove --optional deploy`"
                match = re.search(
                    r"try calling `uv remove --optional (\S+)`", result.stderr
                )
                if match:
                    optional_keyword = match.group(1)
                    print(
                        f"Attempting to remove {dep} as an optional dependency using keyword '{optional_keyword}'..."
                    )
                    opt_result = subprocess.run(
                        ["uv", "remove", dep, "--optional", optional_keyword],
                        capture_output=True,
                        text=True,
                        cwd=PROJECT_ROOT,
                    )
                    if opt_result.returncode != 0:
                        print(
                            f"Warning: Failed to remove {dep} even as optional with '{optional_keyword}'."
                        )
                        print(opt_result.stdout)
                        print(opt_result.stderr)
                    else:
                        print(
                            f"Successfully removed optional dependency {dep} using keyword {optional_keyword}."
                        )
                else:
                    # Could not parse the optional keyword
                    print(
                        f"Warning: Could not parse optional dependency keyword for {dep}. Skipping."
                    )
            else:
                print("Optional removal not enabled. Skipping.")
        else:
            print(f"Successfully removed {dep}.")

    print("Finished removing unused dependencies.")


if __name__ == "__main__":
    print("Script execution started.")

    print(f"Reading configuration file: {CONFIG_PATH}")
    with CONFIG_PATH.open() as f:
        config = yaml.safe_load(f)
    print(f"Configuration loaded: {config}")

    comps_to_remove = config.get("components_to_remove", [])
    print(f"Components to remove: {comps_to_remove}")

    remove_component_dirs(comps_to_remove)

    print("Running `deptry` analysis...")
    deptry_output = run_deptry()

    print("Removing unused dependencies...")
    remove_unused_dependencies(deptry_output)

    print("Script execution completed.")
