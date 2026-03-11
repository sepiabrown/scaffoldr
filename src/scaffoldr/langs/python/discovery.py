"""Workspace and package discovery for Python/uv projects."""

import sys
import tomllib
from pathlib import Path

__all__ = ["_discover_workspace", "_discover_modules"]


def _discover_workspace(workspace_root: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Discover packages and entry points from pyproject.toml files.

    Returns:
        (packages, entry_points) where:
        - packages: {"myapp": "myapp-py/src/myapp", ...}
        - entry_points: {"myapp-train": "myapp.cli.train:main", ...}
    """
    packages: dict[str, str] = {}
    entry_points: dict[str, str] = {}

    # Read workspace pyproject.toml for member list
    ws_toml = workspace_root / "pyproject.toml"
    if not ws_toml.exists():
        print(f"  [WARN] No workspace pyproject.toml at {ws_toml}", file=sys.stderr)
        return packages, entry_points

    with open(ws_toml, "rb") as f:
        ws_config = tomllib.load(f)

    members = (
        ws_config.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
    )

    if not members:
        # Fallback: scan for subdirs containing pyproject.toml
        members = [
            d.name
            for d in workspace_root.iterdir()
            if d.is_dir() and (d / "pyproject.toml").exists()
        ]

    if not members:
        # Single-package project: the root pyproject.toml IS the package
        pkg_name = ws_config.get("project", {}).get("name", "")
        if pkg_name:
            pkg_name_underscored = pkg_name.replace("-", "_")
            src_dir = None
            for candidate in [
                workspace_root / "src" / pkg_name_underscored,
                workspace_root / "src" / pkg_name,
                workspace_root / pkg_name_underscored,
                workspace_root / pkg_name,
            ]:
                if candidate.is_dir():
                    src_dir = candidate
                    break

            if src_dir:
                packages[pkg_name_underscored] = str(
                    src_dir.relative_to(workspace_root)
                )
                scripts = ws_config.get("project", {}).get("scripts", {})
                entry_points.update(scripts)
                return packages, entry_points

    for member_dir_name in members:
        member_toml = workspace_root / member_dir_name / "pyproject.toml"
        if not member_toml.exists():
            print(
                f"  [WARN] No pyproject.toml in member {member_dir_name}",
                file=sys.stderr,
            )
            continue

        with open(member_toml, "rb") as f:
            member_config = tomllib.load(f)

        pkg_name = member_config.get("project", {}).get("name", "")
        if not pkg_name:
            continue

        # Discover the source directory (try common layouts)
        src_dir = None
        for candidate in [
            workspace_root / member_dir_name / "src" / pkg_name,
            workspace_root / member_dir_name / pkg_name,
            workspace_root / member_dir_name / "src",
        ]:
            if candidate.is_dir():
                src_dir = candidate
                break

        if src_dir:
            packages[pkg_name] = str(src_dir.relative_to(workspace_root))
        else:
            print(
                f"  [WARN] Could not find source dir for {pkg_name} in {member_dir_name}",
                file=sys.stderr,
            )

        # Collect entry points from [project.scripts]
        scripts = member_config.get("project", {}).get("scripts", {})
        entry_points.update(scripts)

    return packages, entry_points


def _discover_modules(workspace_root: Path, packages: dict[str, str]) -> dict[str, Path]:
    """Discover all Python modules in the project packages."""
    modules: dict[str, Path] = {}
    for pkg_name, pkg_rel_path in packages.items():
        pkg_dir = workspace_root / pkg_rel_path
        if not pkg_dir.is_dir():
            print(f"  [WARN] Package dir not found: {pkg_dir}", file=sys.stderr)
            continue
        for py_file in sorted(pkg_dir.rglob("*.py")):
            # Convert path to module name
            parts = py_file.relative_to(pkg_dir.parent).with_suffix("").parts
            mod_name = ".".join(parts)
            if mod_name.endswith(".__init__"):
                mod_name = mod_name[: -len(".__init__")]
            modules[mod_name] = py_file
    return modules
