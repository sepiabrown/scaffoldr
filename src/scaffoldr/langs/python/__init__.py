"""Python/uv workspace analyzer."""

import sys
import tomllib
from pathlib import Path

from scaffoldr.core.types import AnalysisResult
from .discovery import discover_workspace, discover_modules
from .parsing import parse_file, analyze_module

__all__ = ["analyze"]


def analyze(workspace_root: Path) -> AnalysisResult:
    """Analyze a Python/uv workspace.

    Discovers packages, parses all modules, and returns a structured result
    that the core graph generators and formatters can consume.
    """
    # Read workspace name
    with open(workspace_root / "pyproject.toml", "rb") as f:
        ws_config = tomllib.load(f)
    workspace_name = ws_config.get("project", {}).get("name", "") or workspace_root.name

    # Discover
    packages, entry_points = discover_workspace(workspace_root)
    if not packages:
        print(
            f"Error: No packages found in '{workspace_root}'.\n"
            f"\n"
            f"The pyproject.toml must define [tool.uv.workspace] with member directories,\n"
            f"or have subdirectories containing their own pyproject.toml files.\n"
            f"\n"
            f"Expected structure:\n"
            f"  {workspace_root}/\n"
            f"    pyproject.toml          # with [tool.uv.workspace] members = [...]\n"
            f"    my-package/\n"
            f'      pyproject.toml        # with [project] name = "my-package"\n'
            f"      src/my_package/       # source directory",
            file=sys.stderr,
        )
        sys.exit(1)

    project_packages = set(packages.keys())
    modules = discover_modules(workspace_root, packages)

    # Parse
    all_trees = {}
    all_analysis = {}
    parse_errors = 0
    for mod_name, filepath in sorted(modules.items()):
        tree = parse_file(filepath)
        if tree:
            all_trees[mod_name] = tree
            all_analysis[mod_name] = analyze_module(mod_name, tree, project_packages)
        else:
            parse_errors += 1

    return AnalysisResult(
        workspace_name=workspace_name,
        packages=packages,
        entry_points=entry_points,
        modules=modules,
        all_analysis=all_analysis,
        all_trees=all_trees,
        parse_errors=parse_errors,
    )
