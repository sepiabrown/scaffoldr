"""Language detection and dispatch."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ..core.types import AnalysisResult

__all__ = ["detect_language", "get_analyzer"]


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


def get_analyzer(lang: str) -> Callable[[Path], AnalysisResult]:
    """Return the analyzer function for a given language.

    Raises:
        SystemExit: If the language is not supported.
    """
    if lang == "python":
        from .python import analyze

        return analyze

    print(f"Unsupported language: {lang}", file=sys.stderr)
    sys.exit(1)
