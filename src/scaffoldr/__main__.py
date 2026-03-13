#!/usr/bin/env python3
"""scaffoldr entry point.  Wires cli → langs → core → output.

This module contains NO argparse, NO file writing, NO print statements
(except error exits).  It is purely wiring between the four layers.
"""

from __future__ import annotations

import sys

from .cli import AnalyzeCommand, parse_args, print_analysis_progress, print_graph_progress, write_outputs
from .core import (
    generate_dependency_graph,
    generate_class_hierarchy,
    generate_entry_point_map,
    generate_coupling_density,
    generate_facade_leaks,
    generate_test_boundary_analysis,
    generate_init_hygiene,
    build_facade_exports,
    detect_cycles,
)
from .langs import detect_language, get_analyzer


def main() -> None:
    cmd = parse_args()

    if cmd["command"] == "analyze":
        _analyze(cmd)
    else:
        print(f"Unknown command: {cmd['command']}", file=sys.stderr)
        sys.exit(1)


def _analyze(cmd: AnalyzeCommand) -> None:
    workspace_root = cmd["workspace"]
    output_dir = cmd["output_dir"]
    formats = cmd["formats"]
    verbose = cmd["verbose"]
    top_coupling = cmd["top_coupling"]

    # Detect language and run language-specific analysis
    lang = detect_language(workspace_root)

    analyze_fn = get_analyzer(lang)
    result = analyze_fn(workspace_root)

    workspace_name = result["workspace_name"]
    package_names = set(result["packages"].keys())

    # Progress: discovery and parsing
    if verbose:
        print_analysis_progress(workspace_name, result)

    facade_exports = build_facade_exports(result["all_analysis"], result["all_trees"])
    facade_set = set(facade_exports.keys())
    test_modules = result["test_modules"]

    # Generate graph artifacts
    dep_graph = generate_dependency_graph(
        result["all_analysis"], package_names, facade_set=facade_set
    )
    class_hier = generate_class_hierarchy(result["all_analysis"], package_names)
    ep_map = generate_entry_point_map(
        result["all_analysis"],
        result["all_trees"],
        result["entry_points"],
        package_names,
    )
    coupling = generate_coupling_density(
        result["all_analysis"], result["all_trees"], facade_set=facade_set
    )
    facade_leaks = generate_facade_leaks(
        result["all_analysis"], result["all_trees"], facade_exports,
        test_modules=test_modules,
    )
    test_boundary = generate_test_boundary_analysis(
        result["all_analysis"], result["all_trees"], facade_exports, test_modules
    )
    init_hygiene = generate_init_hygiene(result["all_analysis"], result["all_trees"])
    cycles = detect_cycles(dep_graph)

    # Progress: artifact generation
    if verbose:
        print_graph_progress(
            dep_graph, class_hier, ep_map, coupling, facade_leaks,
            cycles=cycles, init_hygiene=init_hygiene, test_boundary=test_boundary,
        )

    # Write outputs
    metadata = {
        "total_modules": len(result["modules"]),
        "parsed_modules": len(result["all_trees"]),
        "parse_errors": result["parse_errors"],
    }

    write_outputs(
        output_dir=output_dir,
        formats=formats,
        workspace_name=workspace_name,
        dep_graph=dep_graph,
        class_hier=class_hier,
        ep_map=ep_map,
        coupling=coupling,
        facade_leaks=facade_leaks,
        cycles=cycles,
        init_hygiene=init_hygiene,
        test_boundary=test_boundary,
        metadata=metadata,
        package_names=package_names,
        verbose=verbose,
        top_coupling=top_coupling,
    )


if __name__ == "__main__":
    main()
