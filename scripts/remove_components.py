import logging
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
CONFIG_PATH: Path = PROJECT_ROOT / "scripts" / "component_config.yml"
COMPONENTS_DIR: Path = (
    PROJECT_ROOT / "src" / "backend" / "base" / "langflow" / "components"
)


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def confirm_deletion(directory: str, files: list[str]) -> bool:
    """Ask the user for confirmation to delete specified files or an entire directory.

    Args:
        directory: The name of the directory from which files will be deleted.
        files: A list of files that are about to be deleted. If empty, the entire directory will be deleted.

    Returns:
        bool: True if the user confirms the deletion, False otherwise.
    """
    if files:
        msg = (
            f"You are about to delete the following files from '{directory}':\n"
            + "\n".join(files)
            + "\nProceed? (y/n): "
        )
    else:
        msg = (
            f"You are about to delete the entire directory '{directory}' and its contents.\n"
            "Proceed? (y/n): "
        )
    confirmation = input(msg)
    return confirmation.lower() == "y"


def remove_component_dirs(components: str | dict[str, Any]) -> None:
    """Remove specified components (directories or files).

    Args:
        components: Either strings (directories to remove) or dicts specifying directories and files to remove.
    """
    logger.info("Starting to remove specified components...")
    for comp in components:
        if isinstance(comp, str):
            dir_name = comp
            files_to_remove = []
        elif isinstance(comp, dict):
            dir_name = next(iter(comp.keys()))
            files_to_remove = comp[dir_name].get("files", [])
        else:
            logger.warning(f"Unsupported component format: {str(comp)}")
            continue

        comp_path = COMPONENTS_DIR / dir_name
        if not comp_path.is_dir():
            logger.info(f"Directory does not exist: {comp_path}")
            continue

        confirmation = confirm_deletion(dir_name, files_to_remove)
        if not confirmation:
            logger.info("Skipped deletion.")
            continue

        if files_to_remove:
            for file_name in files_to_remove:
                file_path = comp_path / file_name
                if file_path.is_file():
                    logger.info(f"Removing file: {file_path}")
                    file_path.unlink()
                else:
                    logger.info(f"File not found or not a file: {file_path}")
        else:
            logger.info(f"Removing entire directory: {comp_path}")
            for file_path in comp_path.glob("**/*"):
                if file_path.is_file():
                    logger.info(f"Removing file: {file_path}")
                    file_path.unlink()
            comp_path.rmdir()

    logger.info("Finished removing specified components.")


def run_deptry(verbose: bool) -> str:  # noqa: FBT001
    """Run deptry to identify unused dependencies.

    Args:
        verbose: If True, print the output of the deptry command.

    Returns:
        The output of the deptry command.
    """
    logger.info("Running `deptry` to identify unused dependencies...")
    result = subprocess.run(  # noqa: S603
        ["uv", "run", "deptry", "."],  # noqa: S607
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=PROJECT_ROOT,
        check=False,
    )
    if verbose:
        logger.info("Deptry output:")
        logger.info(result.stdout)
    return result.stdout


def parse_unused_dependencies(deptry_output: str) -> list[str]:
    """Parse deptry output to find unused dependencies."""
    unused_deps: list[str] = []
    for line in deptry_output.splitlines():
        if "DEP002" in line:
            dep_match = re.search(r"'([^']+)'", line)
            if dep_match:
                dep = dep_match.group(1)
                unused_deps.append(dep)
    return unused_deps


def remove_unused_dependencies(
    deptry_output: str, remove_optional: bool
) -> None:  # noqa: FBT001
    """Remove unused dependencies by running `uv remove` commands.

    Args:
        deptry_output: The output from deptry containing unused dependencies.
        remove_optional: If True, try removing dependencies as optional if normal removal fails.
    """
    logger.info("Starting to remove unused dependencies...")
    unused_deps = parse_unused_dependencies(deptry_output)

    if not unused_deps:
        logger.info("No unused dependencies found.")
        return

    for dep in unused_deps:
        logger.info(f"Removing unused dependency: {dep}")  # noqa: G004
        result = subprocess.run(  # noqa: S603
            ["uv", "remove", dep],  # noqa: S607
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                f"Failed to remove {dep}. Output:\n{result.stdout}\n{result.stderr}"
            )  # noqa: G004

            if remove_optional:
                match = re.search(
                    r"try calling `uv remove --optional (\S+)`", result.stderr
                )
                if match:
                    optional_keyword = match.group(1)
                    logger.info(
                        f"Attempting optional removal of {dep} with keyword '{optional_keyword}'..."
                    )  # noqa: G004
                    opt_result = subprocess.run(  # noqa: S603
                        [
                            "uv",
                            "remove",
                            dep,
                            "--optional",
                            optional_keyword,
                        ],  # noqa: S607
                        capture_output=True,
                        text=True,
                        cwd=PROJECT_ROOT,
                        check=False,
                    )
                    if opt_result.returncode != 0:
                        logger.warning(
                            f"Failed to remove {dep} as optional. Output:\n{opt_result.stdout}\n{opt_result.stderr}"  # noqa: G004
                        )
                    else:
                        logger.info(
                            f"Successfully removed optional dependency {dep}."
                        )  # noqa: G004
                else:
                    logger.warning(
                        f"No optional keyword found for {dep}. Skipping."
                    )  # noqa: G004
            else:
                logger.info("Optional removal not enabled. Skipping.")
        else:
            logger.info(f"Successfully removed {dep}.")  # noqa: G004

    logger.info("Finished removing unused dependencies.")


def main() -> None:
    logger.info("Script execution started.")
    config = load_config(CONFIG_PATH)
    comps_to_remove = config.get("components_to_remove", [])
    remove_component_dirs(comps_to_remove)
    deptry_output = run_deptry(verbose=False)
    remove_unused_dependencies(deptry_output, remove_optional=True)
    logger.info("Script execution completed.")


if __name__ == "__main__":
    main()
