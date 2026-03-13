"""Output handling for scaffoldr CLI.

Handles all file writing and console output. Imports formatters from
``core/`` but does NOT call ``langs/`` or ``core/graphs``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ..core import (
    AnalysisResult,
    format_coupling_density_text,
    format_class_tree_text,
    format_cycles_mermaid,
    format_cycles_text,
    format_dependency_mermaid,
    format_dependency_text,
    format_entry_points_text,
    format_facade_leaks_text,
    format_test_boundary_text,
    format_init_hygiene_text,
    format_toon,
)


def print_analysis_progress(workspace_name: str, result: AnalysisResult) -> None:
    """Print the ``[0/4] ... [2/4]`` progress lines to stdout.

    Covers workspace discovery, module discovery, and AST parsing.
    """
    packages = result["packages"]
    entry_points = result["entry_points"]
    modules = result["modules"]
    all_trees = result["all_trees"]
    parse_errors = result["parse_errors"]

    print("=" * 60)
    print(f"Structural Analysis: {workspace_name}")
    print("=" * 60)

    print(f"\n[0/4] Workspace: {', '.join(f'{k} ({v})' for k, v in packages.items())}")
    print(f"  Entry points: {', '.join(entry_points.keys())}")

    print(f"\n[1/4] Discovered {len(modules)} modules")

    print(f"\n[2/4] Parsed {len(all_trees)} modules ({parse_errors} errors)")


def print_graph_progress(
    dep_graph: dict[str, Any],
    class_hier: dict[str, Any],
    ep_map: dict[str, Any],
    coupling: dict[str, Any],
    facade_leaks: dict[str, Any] | None = None,
    cycles: dict[str, Any] | None = None,
    init_hygiene: dict[str, Any] | None = None,
    test_boundary: dict[str, Any] | None = None,
) -> None:
    """Print ``[3/4]`` artifact generation progress."""
    n_pkg_edges = len(dep_graph["package_level"])
    n_classes = class_hier["total_classes"]
    n_eps = len(ep_map)
    n_boundaries = len(coupling["boundaries"])
    n_coupling = sum(len(b["calls"]) for b in coupling["boundaries"])
    n_facade_leaks = facade_leaks.get("total_leaks", 0) if facade_leaks else 0
    n_cycles = cycles.get("total_cycles", 0) if cycles else 0

    print("\n[3/4] Generating artifacts...")
    print(f"  Dependency graph: {n_pkg_edges} package edges")
    print(f"  Class hierarchy: {n_classes} classes")
    print(f"  Entry points: {n_eps} endpoints")
    print(
        f"  Cross-boundary calls (ELD): {n_coupling} calls"
        f" across {n_boundaries} boundary pairs"
    )
    if n_facade_leaks > 0:
        print(f"  Facade leaks: {n_facade_leaks}")
    if n_cycles > 0 and cycles is not None:
        n_nodes = cycles.get("total_nodes_in_cycles", 0)
        print(f"  Circular dependencies: {n_cycles} cycles ({n_nodes} packages involved)")
    else:
        print(f"  Circular dependencies: none")
    if init_hygiene is not None:
        n_issues = init_hygiene.get("total_issues", 0)
        n_packages = init_hygiene.get("packages_checked", 0)
        n_clean = init_hygiene.get("clean_packages", 0)
        print(f"  Init hygiene: {n_issues} issues in {n_packages} packages ({n_clean} clean)")
    if test_boundary is not None:
        n_violations = test_boundary.get("total_violations", 0)
        n_facades = test_boundary.get("total_facades", 0)
        avg_cov = test_boundary.get("average_coverage_pct", 0.0)
        print(f"  Test boundary: {n_violations} violations, {n_facades} facades, {avg_cov}% avg coverage")


def _print_summary(combined: str) -> None:
    """Print the compressed summary to stdout, handling encoding.

    On consoles with non-UTF-8 encoding (e.g. cp949 on Windows), characters
    that cannot be represented are replaced with ``?`` rather than crashing.
    """
    encoding = sys.stdout.encoding or "utf-8"
    safe = combined.encode(encoding, errors="replace").decode(
        encoding, errors="replace"
    )
    print(safe)


def _build_full_data(
    dep_graph: dict[str, Any],
    class_hier: dict[str, Any],
    ep_map: dict[str, Any],
    coupling: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the full-data dict used by JSON and TOON outputs."""
    return {
        "dependency_graph": dep_graph,
        "class_hierarchy": class_hier,
        "entry_points": ep_map,
        "coupling_density": coupling,
        "metadata": metadata,
    }


def _write_facade_leaks(
    output_dir: Path,
    facade_leaks: dict[str, Any] | None,
    package_names: set[str],
    verbose: bool = False,
) -> None:
    """Write ``facade_leaks.txt`` — always produced, even with no flags."""
    if facade_leaks and facade_leaks.get("total_leaks", 0) > 0:
        content = format_facade_leaks_text(facade_leaks, package_names)
    else:
        content = "No facade leaks detected. All imports go through package facades.\n"
    (output_dir / "facade_leaks.txt").write_text(content, encoding="utf-8")
    if verbose:
        print(f"  [OK] facade_leaks.txt")


def _write_cycles(
    output_dir: Path,
    cycles: dict[str, Any] | None,
    package_names: set[str],
    verbose: bool = False,
) -> None:
    """Write ``cycles.md`` — always produced."""
    if cycles and cycles.get("total_cycles", 0) > 0:
        text = format_cycles_text(cycles, package_names)
        mermaid = format_cycles_mermaid(cycles, package_names)
        content = (
            f"# Circular Dependencies\n\n"
            f"## Cycle Diagram\n\n"
            f"```mermaid\n{mermaid}\n```\n\n"
            f"## Details\n\n{text}\n"
        )
    else:
        content = "No circular dependencies detected.\n"
    (output_dir / "cycles.md").write_text(content, encoding="utf-8")
    if verbose:
        print(f"  [OK] cycles.md")


def _write_init_hygiene(
    output_dir: Path,
    init_hygiene: dict[str, Any] | None,
    package_names: set[str],
    verbose: bool = False,
) -> None:
    """Write ``init_hygiene.txt`` — always produced."""
    if init_hygiene and init_hygiene.get("total_issues", 0) > 0:
        content = format_init_hygiene_text(init_hygiene, package_names)
    else:
        content = "All __init__.py files are clean.\n"
    (output_dir / "init_hygiene.txt").write_text(content, encoding="utf-8")
    if verbose:
        print(f"  [OK] init_hygiene.txt")


def _write_test_boundary(
    output_dir: Path,
    test_boundary: dict[str, Any] | None,
    package_names: set[str],
    verbose: bool = False,
) -> None:
    """Write ``test_boundary.txt`` — always produced."""
    if test_boundary and (
        test_boundary.get("total_violations", 0) > 0
        or test_boundary.get("total_facades", 0) > 0
    ):
        content = format_test_boundary_text(test_boundary, package_names)
    else:
        content = "No test boundary data. No test modules or facades found.\n"
    (output_dir / "test_boundary.txt").write_text(content, encoding="utf-8")
    if verbose:
        print(f"  [OK] test_boundary.txt")


def _write_json(
    output_dir: Path,
    full_data: dict[str, Any],
    verbose: bool = False,
) -> None:
    """Write ``structure_full.json``."""
    json_path = output_dir / "structure_full.json"
    json_path.write_text(json.dumps(full_data, indent=2, default=str), encoding="utf-8")
    if verbose:
        print(f"  [OK] {json_path.name}")


def _write_toon(
    output_dir: Path,
    full_data: dict[str, Any],
    verbose: bool = False,
) -> None:
    """Write ``structure_full.toon``."""
    toon_content = format_toon(full_data)
    toon_path = output_dir / "structure_full.toon"
    toon_path.write_text(toon_content, encoding="utf-8")
    if verbose:
        print(f"  [OK] {toon_path.name}")


def _write_text_files(
    output_dir: Path,
    workspace_name: str,
    dep_graph: dict[str, Any],
    class_hier: dict[str, Any],
    ep_map: dict[str, Any],
    coupling: dict[str, Any],
    metadata: dict[str, Any],
    package_names: set[str],
    verbose: bool = False,
    facade_leaks: dict[str, Any] | None = None,
    cycles: dict[str, Any] | None = None,
    top_coupling: int | None = None,
) -> None:
    """Write all text-format output files and optionally print summary to stdout."""
    dep_text = format_dependency_text(dep_graph)
    dep_mermaid = format_dependency_mermaid(dep_graph, package_names)
    class_text = format_class_tree_text(class_hier)
    ep_text = format_entry_points_text(ep_map)
    coupling_text = format_coupling_density_text(
        coupling, package_names, top_n=top_coupling
    )
    leaks_text = ""
    if facade_leaks and facade_leaks.get("total_leaks", 0) > 0:
        leaks_text = format_facade_leaks_text(facade_leaks, package_names)
    cycles_text = ""
    if cycles and cycles.get("total_cycles", 0) > 0:
        cycles_text = format_cycles_text(cycles, package_names)

    n_coupling = sum(len(b["calls"]) for b in coupling["boundaries"])
    n_facade_leaks = facade_leaks.get("total_leaks", 0) if facade_leaks else 0
    n_cycles = cycles.get("total_cycles", 0) if cycles else 0

    # Combined compressed summary
    sections = [
        "=" * 50,
        f"{workspace_name.upper()} STRUCTURAL ANALYSIS (compressed)",
        "=" * 50,
        dep_text,
        "",
        class_text,
        "",
        ep_text,
        "",
        coupling_text,
    ]
    if leaks_text:
        sections.append("")
        sections.append(leaks_text)
    if cycles_text:
        sections.append("")
        sections.append(cycles_text)
    sections.append("")
    sections.append(
        f"---\nModules: {metadata['parsed_modules']}"
        f" | Classes: {class_hier['total_classes']}"
        f" | Entry points: {len(ep_map)}"
        f" | Cross-boundary calls: {n_coupling}"
        f" | Facade leaks: {n_facade_leaks}"
        f" | Cycles: {n_cycles}"
    )
    combined = "\n\n".join(sections)

    (output_dir / "structure_summary.txt").write_text(combined, encoding="utf-8")
    if verbose:
        print(f"  [OK] structure_summary.txt")

    (output_dir / "dependencies.md").write_text(
        f"# Module Dependencies\n\n"
        f"## Package-Level Graph\n\n"
        f"```mermaid\n{dep_mermaid}\n```\n\n"
        f"## Text Summary\n\n"
        f"```\n{dep_text}\n```\n",
        encoding="utf-8",
    )
    if verbose:
        print(f"  [OK] dependencies.md")

    (output_dir / "class_hierarchy.txt").write_text(class_text, encoding="utf-8")
    if verbose:
        print(f"  [OK] class_hierarchy.txt")

    (output_dir / "entry_points.txt").write_text(ep_text, encoding="utf-8")
    if verbose:
        print(f"  [OK] entry_points.txt")

    (output_dir / "coupling_density.txt").write_text(coupling_text, encoding="utf-8")
    if verbose:
        print(f"  [OK] coupling_density.txt")

    if verbose:
        # Print summary to stdout
        print("\n" + "=" * 50)
        print("COMPRESSED SUMMARY (~450 tokens)")
        print("=" * 50)
        _print_summary(combined)


def write_outputs(
    output_dir: Path,
    formats: set[str],
    workspace_name: str,
    dep_graph: dict[str, Any],
    class_hier: dict[str, Any],
    ep_map: dict[str, Any],
    coupling: dict[str, Any],
    metadata: dict[str, Any],
    package_names: set[str],
    verbose: bool = False,
    facade_leaks: dict[str, Any] | None = None,
    cycles: dict[str, Any] | None = None,
    init_hygiene: dict[str, Any] | None = None,
    test_boundary: dict[str, Any] | None = None,
    top_coupling: int | None = None,
) -> None:
    """Write all output files based on requested formats.

    Parameters
    ----------
    output_dir:
        Directory to write files into (created if needed).
    formats:
        Subset of ``{"text", "json", "toon"}`` indicating which outputs
        to produce.
    workspace_name:
        Human-readable workspace name for headers.
    dep_graph, class_hier, ep_map, coupling:
        Analysis artifacts from ``core.graphs``.
    metadata:
        Dict with ``total_modules``, ``parsed_modules``, ``parse_errors``.
    package_names:
        Set of top-level package names for display shortening.
    verbose:
        If True, print progress and file-write confirmations to stdout.
    cycles:
        Cycle detection results from ``detect_cycles()``.
    test_boundary:
        Test boundary analysis from ``generate_test_boundary_analysis()``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    if verbose:
        print(f"\n[4/4] Writing to {output_dir}/")

    # facade_leaks.txt is always written (default output)
    _write_facade_leaks(output_dir, facade_leaks, package_names, verbose=verbose)
    # cycles.md is always written (default output)
    _write_cycles(output_dir, cycles, package_names, verbose=verbose)
    # init_hygiene.txt is always written (default output)
    _write_init_hygiene(output_dir, init_hygiene, package_names, verbose=verbose)
    # test_boundary.txt is always written (default output)
    _write_test_boundary(output_dir, test_boundary, package_names, verbose=verbose)

    full_data = _build_full_data(dep_graph, class_hier, ep_map, coupling, metadata)

    if "json" in formats:
        _write_json(output_dir, full_data, verbose=verbose)

    if "toon" in formats:
        _write_toon(output_dir, full_data, verbose=verbose)

    if "text" in formats:
        _write_text_files(
            output_dir,
            workspace_name,
            dep_graph,
            class_hier,
            ep_map,
            coupling,
            metadata,
            package_names,
            verbose=verbose,
            facade_leaks=facade_leaks,
            cycles=cycles,
            top_coupling=top_coupling,
        )

    if verbose:
        print(f"\n[DONE] Output saved to {output_dir}/")
