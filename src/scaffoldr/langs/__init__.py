"""Language detection and dispatch."""

from pathlib import Path

__all__ = ["detect_language"]


def detect_language(workspace_root: Path) -> str:
    """Detect the language/build system of a workspace.

    Returns:
        Language identifier string (e.g. "python").

    Raises:
        SystemExit: If no known language is detected.
    """
    if (workspace_root / "pyproject.toml").exists():
        return "python"
    # Future: (workspace_root / "package.json").exists() -> "typescript"
    # Future: (workspace_root / "Cargo.toml").exists() -> "rust"

    import sys

    markers = [
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "build.sbt",
        "*.cabal",
        "flake.nix",
    ]
    print(
        f"Error: Cannot detect language for '{workspace_root}'.\n"
        f"\n"
        f"scaffoldr looks for workspace metadata files to identify the language:\n"
        f"  {', '.join(markers)}\n"
        f"\n"
        f"Currently supported: Python (pyproject.toml with [tool.uv.workspace])\n"
        f"\n"
        f"Make sure you're pointing at a workspace root, not a source directory.\n"
        f"Example: scaffoldr analyze ~/my-project/workspaces",
        file=sys.stderr,
    )
    sys.exit(1)
