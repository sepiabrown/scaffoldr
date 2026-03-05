"""Output formatters for structural analysis (language-agnostic)."""

from collections import defaultdict
from typing import Any

from .graphs import shorten_module

__all__ = [
    "format_dependency_mermaid",
    "format_dependency_text",
    "format_class_tree_text",
    "format_entry_points_text",
    "format_coupling_density_text",
    "format_facade_leaks_text",
    "format_toon",
]


def format_dependency_mermaid(
    dep_graph: dict[str, Any], package_names: set[str]
) -> str:
    """Format package-level deps as Mermaid flowchart."""
    lines = ["graph LR"]
    pkg_graph = dep_graph["package_level"]

    # Create node IDs
    all_nodes = set()
    for src, dsts in pkg_graph.items():
        all_nodes.add(src)
        all_nodes.update(dsts)

    node_id = {n: n.replace(".", "_") for n in sorted(all_nodes)}

    for n in sorted(all_nodes):
        short = shorten_module(n, package_names)
        lines.append(f"    {node_id[n]}[{short}]")

    for src, dsts in sorted(pkg_graph.items()):
        for dst in sorted(dsts):
            lines.append(f"    {node_id[src]} --> {node_id[dst]}")

    return "\n".join(lines)


def format_dependency_text(dep_graph: dict[str, Any]) -> str:
    """Format package-level deps as compressed text.

    Uses full names (myapp.cli, mylib.cli) to avoid ambiguity.
    Groups by root package automatically.
    """
    lines = ["# Module Dependency Graph (package-level)", ""]
    pkg_graph = dep_graph["package_level"]

    # Group by root package for clarity
    groups: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for src, dsts in sorted(pkg_graph.items()):
        root = src.split(".")[0]
        groups[root][src] = sorted(dsts)

    for root, pkgs in sorted(groups.items()):
        lines.append(f"## {root}")
        for src, dsts in pkgs.items():
            lines.append(f"  {src} -> {', '.join(dsts)}")

    return "\n".join(lines)


def format_class_tree_text(hierarchy: dict[str, Any]) -> str:
    """Format class hierarchy as compressed indented tree."""
    lines = [
        f"# Class Hierarchy ({hierarchy['total_classes']} classes)",
        "",
    ]

    def render(node: dict, indent: int = 0) -> None:
        prefix = "  " * indent
        name = node["name"]
        mod = node["module"]
        mc = node["method_count"]
        bases_str = ""
        if node["bases"]:
            bases_str = f"({', '.join(node['bases'])})"

        # Show key methods inline for important classes
        methods_str = ""
        if node["key_methods"]:
            methods_str = f" [{', '.join(node['key_methods'][:5])}]"
            if mc > 5:
                methods_str = methods_str[:-1] + f", +{mc - 5} more]"

        lines.append(f"{prefix}+- {name}{bases_str} @ {mod} ({mc}m){methods_str}")

        for child in node.get("children", []):
            render(child, indent + 1)

    # Only show classes with >2 methods or with children (filter noise)
    for node in hierarchy["hierarchy"]:
        if node["method_count"] > 2 or node.get("children"):
            render(node)

    return "\n".join(lines)


def format_entry_points_text(ep_map: dict[str, Any]) -> str:
    """Format entry points as compressed text."""
    lines = ["# Entry Points", ""]

    for ep_name, info in sorted(ep_map.items()):
        if info.get("status") == "not_found":
            lines.append(
                f"  {ep_name}: [NOT FOUND] {info['module']}:{info['function']}"
            )
            continue

        calls = info.get("calls", [])
        imports = info.get("imports", [])
        lines.append(f"  {ep_name} -> {info['module']}:{info['function']}")
        if calls:
            lines.append(f"    calls: {', '.join(calls[:10])}")
        if imports:
            lines.append(f"    deps: {', '.join(imports[:8])}")

    return "\n".join(lines)


def _toon_escape(value: str) -> str:
    """Quote a TOON value if it contains commas."""
    if "," in value:
        return f'"{value}"'
    return value


def _flatten_class_tree(
    nodes: list[dict[str, Any]], depth: int = 0
) -> list[dict[str, Any]]:
    """DFS-flatten the class hierarchy tree, tracking depth."""
    rows: list[dict[str, Any]] = []
    for node in nodes:
        rows.append(
            {
                "depth": depth,
                "name": node["name"],
                "module": node["module"],
                "bases": node.get("bases", []),
                "method_count": node["method_count"],
                "key_methods": node.get("key_methods", []),
            }
        )
        if "children" in node:
            rows.extend(_flatten_class_tree(node["children"], depth + 1))
    return rows


def format_toon(full_data: dict[str, Any]) -> str:
    """Format full_data dict as TOON (Token-Oriented Object Notation).

    TOON combines YAML-like indentation for nested objects with CSV-style
    tabular layout for uniform arrays.
    """
    lines: list[str] = []

    # -- metadata (simple nested object) ------------------------------------
    meta = full_data.get("metadata", {})
    lines.append("metadata:")
    for k, v in meta.items():
        lines.append(f"  {k}: {v}")

    lines.append("")

    # -- dependency_graph.package_level --------------------------------------
    dep_graph = full_data.get("dependency_graph", {})
    pkg_level = dep_graph.get("package_level", {})
    lines.append("dependency_graph:")
    lines.append("  package_level:")
    for pkg, deps in sorted(pkg_level.items()):
        dep_list = deps if isinstance(deps, list) else sorted(deps)
        lines.append(f"    {pkg}[{len(dep_list)}]: {','.join(dep_list)}")

    lines.append("")

    # -- class_hierarchy ----------------------------------------------------
    class_hier = full_data.get("class_hierarchy", {})
    hierarchy = class_hier.get("hierarchy", [])
    total_classes = class_hier.get("total_classes", 0)
    flat_classes = _flatten_class_tree(hierarchy)

    lines.append("class_hierarchy:")
    lines.append(f"  total_classes: {total_classes}")
    lines.append(
        f"  classes[{len(flat_classes)}]{{depth,name,module,bases,method_count,key_methods}}:"
    )
    for row in flat_classes:
        bases_str = _toon_escape(",".join(row["bases"])) if row["bases"] else ""
        methods_str = (
            _toon_escape(",".join(row["key_methods"])) if row["key_methods"] else ""
        )
        lines.append(
            f"    {row['depth']},{row['name']},{row['module']},{bases_str},{row['method_count']},{methods_str}"
        )

    lines.append("")

    # -- entry_points -------------------------------------------------------
    ep_map = full_data.get("entry_points", {})
    ep_rows: list[tuple[str, dict[str, Any]]] = sorted(ep_map.items())

    lines.append(f"entry_points[{len(ep_rows)}]{{name,module,function,calls,imports}}:")
    for ep_name, info in ep_rows:
        module = info.get("module", "")
        function = info.get("function", "")
        calls = info.get("calls", [])
        imports = info.get("imports", [])
        calls_str = _toon_escape(",".join(calls)) if calls else ""
        imports_str = _toon_escape(",".join(imports)) if imports else ""
        lines.append(f"  {ep_name},{module},{function},{calls_str},{imports_str}")

    lines.append("")

    # -- coupling_density ---------------------------------------------------
    coupling = full_data.get("coupling_density", {})
    boundaries = coupling.get("boundaries", [])

    # Build rows: one per boundary pair with aggregated callers
    cd_rows: list[dict[str, Any]] = []
    for b in boundaries:
        source = b["source"]
        target = b["target"]
        calls = b.get("calls", [])
        callers_parts = [f"{c['caller']}->{c['callee']}" for c in calls]
        cd_rows.append(
            {
                "source": source,
                "target": target,
                "call_count": len(calls),
                "callers": ";".join(callers_parts),
            }
        )

    lines.append(
        f"coupling_density[{len(cd_rows)}]{{source,target,call_count,callers}}:"
    )
    for row in cd_rows:
        callers_str = _toon_escape(row["callers"]) if row["callers"] else ""
        lines.append(
            f"  {row['source']},{row['target']},{row['call_count']},{callers_str}"
        )

    return "\n".join(lines) + "\n"


def format_coupling_density_text(
    coupling: dict[str, Any], package_names: set[str], top_n: int = 50
) -> str:
    """Format cross-boundary calls as compressed text (ELD view).

    Shows the top *top_n* most-coupled boundary pairs with their individual
    caller->callee relationships.
    """
    boundaries = coupling.get("boundaries", [])
    if not boundaries:
        return "# Cross-Boundary Calls (ELD)\n\n(no cross-boundary calls detected)"

    total_calls = sum(len(b["calls"]) for b in boundaries)

    lines = [
        f"# Cross-Boundary Calls (ELD) — {total_calls} calls across {len(boundaries)} boundary pairs",
        "",
    ]

    for b in boundaries[:top_n]:
        src = shorten_module(b["source"], package_names, keep_root=True)
        tgt = shorten_module(b["target"], package_names, keep_root=True)
        n = len(b["calls"])
        lines.append(f"## {src} -> {tgt} ({n} call{'s' if n != 1 else ''})")
        for c in b["calls"]:
            lines.append(f"  {c['caller']} -> {c['callee']}")
        lines.append("")

    if len(boundaries) > top_n:
        remaining = len(boundaries) - top_n
        remaining_calls = sum(len(b["calls"]) for b in boundaries[top_n:])
        lines.append(
            f"... and {remaining} more boundary pairs ({remaining_calls} calls)"
        )

    return "\n".join(lines)


def format_facade_leaks_text(
    facade_leaks: dict[str, Any], package_names: set[str]
) -> str:
    """Format facade leaks (unified) as text.

    These are imports that bypass a package's __init__.py facade,
    reaching directly into its internal modules.
    """
    leaks = facade_leaks.get("leaks", [])
    if not leaks:
        return ""

    total = facade_leaks.get("total_leaks", len(leaks))
    lines = [
        "",
        "=" * 60,
        f"FACADE LEAKS — {total} imports bypass package facades",
        "=" * 60,
        "",
        "These imports reach into a sibling sub-package's internal modules",
        "instead of importing through its __init__.py facade.",
        "  Fix: import from the facade, or re-export through the facade.",
        "",
    ]

    # Group by parent package for readability
    by_parent: dict[str, list[dict[str, Any]]] = {}
    for leak in leaks:
        # Parent is the common ancestor — derive from facade
        parent = ".".join(leak["facade"].split(".")[:-1])
        by_parent.setdefault(parent, []).append(leak)

    for parent, parent_leaks in sorted(by_parent.items()):
        short_parent = shorten_module(parent, package_names)
        lines.append(f"## {short_parent}/ ({len(parent_leaks)} leaks)")
        for leak in parent_leaks:
            importer = shorten_module(leak["importer"], package_names)
            imported_from = shorten_module(leak["imported_from"], package_names)
            facade = shorten_module(leak["facade"], package_names)
            names = leak["names"]
            missing = leak.get("missing_from_facade", [])
            available = leak.get("available_in_facade", [])

            names_str = ", ".join(names)
            lines.append(f"  {importer}")
            lines.append(f"    from {imported_from} import {names_str}")
            lines.append(f"    should be: from {facade} import ...")
            if missing:
                lines.append(f"    missing from facade: {', '.join(missing)}")
            if available:
                lines.append(f"    already in facade: {', '.join(available)}")
        lines.append("")

    return "\n".join(lines)
