"""Argument parsing for scaffoldr CLI.

Knows about arguments and paths. Does NOT know about languages, graphs,
or formatters.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TypedDict


class AnalyzeCommand(TypedDict):
    """Parsed result of ``scaffoldr analyze <path> [options]``."""

    command: str  # "analyze"
    workspace: Path  # resolved absolute path
    output_dir: Path  # resolved absolute path
    formats: set[str]  # subset of {"text", "json", "toon"}
    verbose: bool  # print progress and summary to stdout
    top_coupling: (
        int | None
    )  # limit coupling density to top N boundary pairs (None = all)
    top_n: int | None  # truncate coupling density to top N pairs (None = all)


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="scaffoldr",
        description="Structural analysis for workspaces (AST-only, stdlib-only)",
    )
    subparsers = parser.add_subparsers(dest="command")

    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze workspace structure",
        description="Analyze the structure of a workspace directory.",
    )
    analyze.add_argument(
        "workspace",
        help="Path to workspace root directory",
    )
    analyze.add_argument(
        "--full",
        action="store_true",
        help="Output all formats: text, JSON, and TOON",
    )
    analyze.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON",
    )
    analyze.add_argument(
        "--toon",
        action="store_true",
        help="Output TOON format alongside text",
    )
    analyze.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: <workspace>/.scaffoldr)",
    )
    analyze.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print progress and summary to stdout (default: quiet)",
    )
    analyze.add_argument(
        "--top-coupling",
        type=int,
        default=None,
        metavar="N",
        help="Show only top N most-coupled boundary pairs (default: all)",
    )

    return parser


def _resolve_formats(*, full: bool, json: bool, toon: bool) -> set[str]:
    """Convert CLI flags to a set of output format names.

    --full        -> {"text", "json", "toon"}
    --json        -> {"json"}
    --toon        -> {"text", "toon"}
    default       -> set()  (facade_leaks.txt only)
    """
    if full:
        return {"text", "json", "toon"}
    if json:
        return {"json"}
    if toon:
        return {"text", "toon"}
    # Default: no format flags → only facade_leaks.txt is written
    return set()


def parse_args(argv: list[str] | None = None) -> AnalyzeCommand:
    """Parse CLI arguments and return a validated :class:`AnalyzeCommand`.

    Parameters
    ----------
    argv:
        Argument list (defaults to ``sys.argv[1:]``).

    Returns
    -------
    AnalyzeCommand
        Fully resolved command with absolute paths and format set.

    Raises
    ------
    SystemExit
        If no subcommand is given, the subcommand is unknown, or the
        workspace path is invalid.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # No subcommand → print help and exit
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Currently only "analyze" is supported; argparse handles unknown
    # subcommands via the subparsers mechanism already.

    # Resolve workspace path (expanduser handles ~ on all OS)
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        print(f"Error: {workspace} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Resolve output directory
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
    else:
        output_dir = workspace / ".scaffoldr"

    # Convert flags to format set
    formats = _resolve_formats(
        full=args.full,
        json=args.json,
        toon=args.toon,
    )

    return AnalyzeCommand(
        command=args.command,
        workspace=workspace,
        output_dir=output_dir,
        formats=formats,
        verbose=args.verbose,
        top_coupling=args.top_coupling,
    )
