"""Graph algorithms for structural analysis (language-agnostic)."""

import ast
from collections import defaultdict
from typing import Any

__all__ = [
    "shorten_module",
    "generate_dependency_graph",
    "generate_class_hierarchy",
    "generate_entry_point_map",
    "generate_coupling_density",
    "generate_facade_leaks",
    "build_facade_exports",
    "CallCollector",
    "find_function_calls",
]


class CallCollector(ast.NodeVisitor):
    """Collects function/method calls within a function body."""

    def __init__(self):
        self.calls: set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        try:
            if isinstance(node.func, ast.Name):
                self.calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                self.calls.add(ast.unparse(node.func))
        except Exception:
            pass
        self.generic_visit(node)


def shorten_module(mod: str, package_names: set[str], keep_root: bool = False) -> str:
    """Shorten module name for compressed output.

    When keep_root=False (default): myapp.trainers.base -> trainers.base
    When keep_root=True: myapp.trainers.base -> myapp.trainers.base (no change)
    """
    parts = mod.split(".")
    if keep_root:
        return mod
    if len(parts) > 1 and parts[0] in package_names:
        return ".".join(parts[1:])
    return mod


def _to_facade_zone(mod: str, facade_set: set[str] | frozenset[str]) -> str:
    """Find the deepest facade-bearing package containing *mod*.

    Walks up from the module to its ancestors, returning the deepest
    ancestor that has an ``__init__.py`` facade (i.e., is a key in
    *facade_set*).  Falls back to the top-level package if no facade
    ancestor is found.

    Examples (given facades = {"myapp", "myapp.tasks", "myapp.tasks.detection"}):
        "myapp.tasks.detection.commands" -> "myapp.tasks.detection"
        "myapp.tasks.generation.train.loss"      -> "myapp.tasks"  (if myapp.tasks.generation has no facade)
        "myapp.cli.admin"                           -> "myapp.cli"    (if myapp.cli is a facade)
    """
    parts = mod.split(".")
    # If the module itself is a facade, it IS its own zone
    if mod in facade_set:
        return mod
    # Walk from deepest to shallowest, find the deepest facade ancestor
    for depth in range(len(parts) - 1, 0, -1):
        candidate = ".".join(parts[:depth])
        if candidate in facade_set:
            return candidate
    # Fallback: top-level package name
    return parts[0]


def find_function_calls(tree: ast.Module, func_name: str) -> list[str]:
    """Find what a specific function calls (shallow, 1-level)."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name:
                cc = CallCollector()
                cc.visit(node)
                return sorted(cc.calls)
    return []


def generate_dependency_graph(
    all_analysis: dict[str, dict[str, Any]],
    package_names: set[str],
    facade_set: set[str] | frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Generate module-level dependency graph."""
    # Build adjacency list: module -> set of modules it imports
    graph: dict[str, set[str]] = defaultdict(set)
    all_mods = set(all_analysis.keys())

    for mod_name, analysis in all_analysis.items():
        for imp in analysis["imports"]:
            # Find the best matching module
            target = imp
            # Try exact match, then parent packages
            while target and target not in all_mods:
                target = ".".join(target.split(".")[:-1])
            if target and target != mod_name:
                graph[mod_name].add(target)

    # Compute package-level summary (collapse to facade-zone level)
    pkg_graph: dict[str, set[str]] = defaultdict(set)
    for mod, deps in graph.items():
        src_pkg = _to_facade_zone(mod, facade_set)
        for dep in deps:
            dst_pkg = _to_facade_zone(dep, facade_set)
            if src_pkg != dst_pkg:
                pkg_graph[src_pkg].add(dst_pkg)

    return {
        "module_level": {k: sorted(v) for k, v in sorted(graph.items())},
        "package_level": {k: sorted(v) for k, v in sorted(pkg_graph.items())},
    }


def generate_class_hierarchy(
    all_analysis: dict[str, dict[str, Any]],
    package_names: set[str],
) -> dict[str, Any]:
    """Generate class hierarchy tree."""
    # Collect all classes with their full qualified names
    all_classes: dict[str, dict[str, Any]] = {}
    class_to_module: dict[str, str] = {}

    for mod_name, analysis in all_analysis.items():
        for cls_info in analysis["classes"]:
            fqn = f"{mod_name}.{cls_info['name']}"
            all_classes[fqn] = cls_info
            class_to_module[cls_info["name"]] = mod_name

    # Build inheritance tree
    children: dict[str, list[str]] = defaultdict(list)
    roots: list[str] = []

    for fqn, cls_info in all_classes.items():
        if not cls_info["bases"]:
            roots.append(fqn)
            continue

        found_parent = False
        for base_name in cls_info["bases"]:
            # Try to resolve base to FQN
            base_short = base_name.split(".")[-1]
            for other_fqn in all_classes:
                if other_fqn.endswith(f".{base_short}"):
                    children[other_fqn].append(fqn)
                    found_parent = True
                    break

        if not found_parent:
            roots.append(fqn)

    # Build tree structure
    def build_tree(fqn: str, depth: int = 0) -> dict[str, Any]:
        cls_info = all_classes.get(fqn, {})
        result = {
            "name": fqn.split(".")[-1],
            "module": shorten_module(".".join(fqn.split(".")[:-1]), package_names),
            "bases": cls_info.get("bases", []),
            "method_count": len(cls_info.get("methods", [])),
            "key_methods": [
                m
                for m in cls_info.get("methods", [])
                if not m.startswith("_")
                or m in ("__init__", "__post_init__", "__call__")
            ][:8],  # Top 8 public methods
        }
        if fqn in children:
            result["children"] = [
                build_tree(child, depth + 1) for child in sorted(children[fqn])
            ]
        return result

    hierarchy = [build_tree(r) for r in sorted(roots)]

    return {
        "total_classes": len(all_classes),
        "hierarchy": hierarchy,
    }


def generate_entry_point_map(
    all_analysis: dict[str, dict[str, Any]],
    all_trees: dict[str, ast.Module],
    entry_points: dict[str, str],
    package_names: set[str],
) -> dict[str, Any]:
    """Generate entry point -> function call chain map."""
    ep_map: dict[str, dict[str, Any]] = {}

    for ep_name, ep_ref in entry_points.items():
        mod_path, func_name = ep_ref.split(":")
        analysis = all_analysis.get(mod_path, {})
        tree = all_trees.get(mod_path)

        if not tree:
            ep_map[ep_name] = {
                "module": mod_path,
                "function": func_name,
                "status": "not_found",
            }
            continue

        calls = find_function_calls(tree, func_name)
        # Filter to interesting calls (not builtins)
        interesting = [
            c
            for c in calls
            if not c.startswith("print")
            and c
            not in (
                "super",
                "len",
                "str",
                "int",
                "float",
                "list",
                "dict",
                "set",
                "tuple",
                "range",
                "enumerate",
                "zip",
                "map",
                "filter",
                "isinstance",
                "hasattr",
                "getattr",
                "setattr",
                "type",
                "vars",
                "dir",
            )
        ]

        ep_map[ep_name] = {
            "module": shorten_module(mod_path, package_names),
            "function": func_name,
            "calls": interesting[:15],  # Top 15 calls
            "imports": [
                shorten_module(i, package_names) for i in analysis.get("imports", [])
            ],
        }

    return ep_map


def build_facade_exports(
    all_analysis: dict[str, dict[str, Any]],
    all_trees: dict[str, ast.Module],
) -> dict[str, set[str]]:
    """Build a map of package -> set of names exported by its __init__.py facade.

    If the ``__init__.py`` defines ``__all__``, ONLY those names are the
    facade contract — everything else is private, even if imported.

    If ``__all__`` is absent, falls back to collecting:
    - Names imported in the __init__.py (from ... import X — X is exported)
    - Classes and functions defined directly in __init__.py

    Only considers modules that ARE package __init__ files (i.e., the module
    name matches a package name that also has submodules).

    Returns:
        {"myapp.dataset": {"DatasetManifest", "Dataset", "DatasetManager", ...}, ...}
    """
    facade_exports: dict[str, set[str]] = {}

    # Identify which modules are package __init__.py files
    # A module name "myapp.dataset" is a package init if:
    #   - it exists in all_analysis (parsed successfully)
    #   - there exist other modules starting with "myapp.dataset."
    all_mod_names = set(all_analysis.keys())

    for mod_name in all_mod_names:
        # Check if this module is a package (has submodules)
        prefix = mod_name + "."
        has_children = any(m.startswith(prefix) for m in all_mod_names)
        if not has_children:
            continue

        # This is a package __init__.py
        tree = all_trees.get(mod_name)
        if tree is None:
            continue

        # 1. Check for __all__ — if present, it IS the facade contract
        all_names: set[str] = set()
        has_all = False
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        has_all = True
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(
                                    elt.value, str
                                ):
                                    all_names.add(elt.value)

        if has_all:
            # __all__ is the authoritative facade — nothing else matters
            facade_exports[mod_name] = all_names
            continue

        # 2. No __all__ — fall back to all imported + defined names
        exports: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names or []:
                    local_name = alias.asname if alias.asname else alias.name
                    exports.add(local_name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    local_name = alias.asname if alias.asname else alias.name
                    exports.add(local_name)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                exports.add(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                exports.add(node.name)

        facade_exports[mod_name] = exports

    return facade_exports


def generate_facade_leaks(
    all_analysis: dict[str, dict[str, Any]],
    all_trees: dict[str, ast.Module],
    facade_exports: dict[str, set[str]],
) -> dict[str, Any]:
    """Detect facade bypasses at any depth (unified leak detection).

    Scans import statements (not calls) to find modules that import from a
    package's internals instead of through its __init__.py facade.  Covers
    both inter-package and intra-package leaks in a single pass.

    Example leak:
        myapp.dataset.dataset imports from myapp.dataset.pipeline.stages
        instead of from myapp.dataset.pipeline (the facade).

    Returns:
        {"leaks": [{"importer": str, "imported_from": str, "facade": str,
                     "names": [str], "available_in_facade": [str],
                     "missing_from_facade": [str]}],
         "total_leaks": int}
    """
    all_mod_names = set(all_analysis.keys())
    leaks: list[dict[str, Any]] = []

    for mod_name in sorted(all_mod_names):
        tree = all_trees.get(mod_name)
        if tree is None:
            continue

        # Scan all import statements in this module
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue

            # Resolve the import target module
            src_mod = node.module or ""
            level = node.level or 0
            if level > 0:
                parts = mod_name.split(".")
                if level <= len(parts):
                    base = ".".join(parts[: len(parts) - level])
                    src_mod = f"{base}.{src_mod}" if src_mod else base
            if not src_mod:
                continue

            # Resolve src_mod to a known module (best-match)
            resolved = src_mod
            while resolved and resolved not in all_mod_names:
                resolved = ".".join(resolved.split(".")[:-1])
            if not resolved:
                continue

            # Find the common parent between importer and target
            imp_parts = mod_name.split(".")
            tgt_parts = resolved.split(".")

            # Find divergence point
            common_len = 0
            for i in range(min(len(imp_parts), len(tgt_parts))):
                if imp_parts[i] == tgt_parts[i]:
                    common_len = i + 1
                else:
                    break

            if common_len == 0:
                continue  # Different top-level packages — handled by cross-boundary

            common_parent = ".".join(tgt_parts[:common_len])

            # The target's immediate child package under common parent
            # e.g., for target myapp.dataset.pipeline.stages,
            #   common_parent = myapp.dataset
            #   sibling = myapp.dataset.pipeline
            if len(tgt_parts) <= common_len:
                continue  # Target IS the common parent — not a sub-package import

            sibling_pkg = ".".join(tgt_parts[: common_len + 1])

            # Skip if the importer IS inside the sibling package
            # (internal imports within a sub-package are fine)
            if mod_name == sibling_pkg or mod_name.startswith(sibling_pkg + "."):
                continue

            # Skip if importing directly from the sibling facade (not its internals)
            if resolved == sibling_pkg:
                continue  # This IS the facade import — clean

            # The target is an internal module of sibling_pkg.
            # Check if sibling_pkg has a facade
            if sibling_pkg not in facade_exports:
                continue  # No facade — can't check (namespace package or leaf module)

            # Check which imported names are/aren't in the sibling facade
            facade_names = facade_exports[sibling_pkg]
            imported_names = []
            available = []
            missing = []
            for alias in node.names or []:
                name = alias.name
                imported_names.append(name)
                if name in facade_names:
                    available.append(name)
                else:
                    missing.append(name)

            if not imported_names:
                continue

            leaks.append(
                {
                    "importer": mod_name,
                    "imported_from": resolved,
                    "facade": sibling_pkg,
                    "names": imported_names,
                    "available_in_facade": available,
                    "missing_from_facade": missing,
                }
            )

    return {"leaks": leaks, "total_leaks": len(leaks)}


def generate_coupling_density(
    all_analysis: dict[str, dict[str, Any]],
    all_trees: dict[str, ast.Module],
    facade_set: set[str] | frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Generate cross-boundary function call coupling density (ELD).

    For each module, walks the AST to collect all calls made by each class method
    and top-level function.  Resolves those calls to their target module using
    import analysis and filters to only CROSS-BOUNDARY calls -- where the calling
    module's facade zone differs from the target module's facade zone.

    This is a **coupling density** view only — it does NOT check facade leaks.
    Use ``generate_facade_leaks()`` for leak detection.

    Returns:
        {"boundaries": [{"source": "myapp.train", "target": "myapp.algorithms",
          "calls": [{"caller": "_analyze", "callee": "generate_dependency_graph"}, ...]}, ...]}
        sorted by number of calls per boundary pair (most coupled first).
    """

    # -- helpers ---------------------------------------------------------------
    _BUILTINS = frozenset(
        {
            "super",
            "len",
            "str",
            "int",
            "float",
            "list",
            "dict",
            "set",
            "tuple",
            "range",
            "enumerate",
            "zip",
            "map",
            "filter",
            "isinstance",
            "hasattr",
            "getattr",
            "setattr",
            "type",
            "vars",
            "dir",
            "print",
            "repr",
            "sorted",
            "reversed",
            "any",
            "all",
            "min",
            "max",
            "sum",
            "abs",
            "round",
            "bool",
            "bytes",
            "id",
            "open",
            "iter",
            "next",
            "callable",
            "hash",
            "hex",
            "oct",
            "ord",
            "chr",
            "bin",
            "format",
            "input",
            "object",
            "staticmethod",
            "classmethod",
            "property",
            "NotImplementedError",
            "ValueError",
            "TypeError",
            "KeyError",
            "RuntimeError",
            "AttributeError",
            "Exception",
        }
    )

    def _build_import_map(
        tree: ast.Module, module_name: str
    ) -> dict[str, tuple[str, str]]:
        """Build a map {local_name -> (source_module, original_name)} from AST import stmts.

        For ``from X import Y as Z``: ``Z -> (X, Y)``
        For ``from X import Y``:      ``Y -> (X, Y)``
        For ``import X.Y as Z``:      ``Z -> (X.Y, X.Y)``
        """
        imap: dict[str, tuple[str, str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                src_mod = node.module or ""
                level = node.level or 0
                # resolve relative imports
                if level > 0:
                    parts = module_name.split(".")
                    if level <= len(parts):
                        base = ".".join(parts[: len(parts) - level])
                        src_mod = f"{base}.{src_mod}" if src_mod else base
                if not src_mod:
                    continue
                for alias in node.names or []:
                    local_name = alias.asname if alias.asname else alias.name
                    original_name = alias.name
                    imap[local_name] = (src_mod, original_name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    local_name = alias.asname if alias.asname else alias.name
                    imap[local_name] = (alias.name, alias.name)
        return imap

    def _resolve_call_target(
        call_expr: str, import_map: dict[str, tuple[str, str]]
    ) -> str | None:
        """Return the source module for *call_expr*, or None if unresolvable."""
        name = call_expr.split("(")[0]
        if name.startswith("self."):
            return None
        prefix = name.split(".")[0]
        entry = import_map.get(prefix)
        return entry[0] if entry is not None else None

    # -- per-module: collect calls per callable and resolve targets ---------
    boundary_calls: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    all_mods = set(all_analysis.keys())

    for mod_name, tree in all_trees.items():
        import_map = _build_import_map(tree, mod_name)
        src_subpkg = _to_facade_zone(mod_name, facade_set)

        # Walk top-level nodes for classes and functions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_name = item.name
                        caller_label = f"{class_name}.{method_name}"
                        cc = CallCollector()
                        cc.visit(item)
                        for call_expr in cc.calls:
                            raw = call_expr.split("(")[0]
                            base = raw.split(".")[0]
                            if base in _BUILTINS:
                                continue
                            target_mod = _resolve_call_target(call_expr, import_map)
                            if target_mod is None:
                                continue
                            resolved = target_mod
                            while resolved and resolved not in all_mods:
                                resolved = ".".join(resolved.split(".")[:-1])
                            if not resolved or resolved == mod_name:
                                continue
                            tgt_subpkg = _to_facade_zone(resolved, facade_set)
                            if src_subpkg == tgt_subpkg:
                                continue
                            if "." in raw:
                                callee_name = raw.split(".")[-1]
                            else:
                                _, orig = import_map.get(raw, (None, raw))
                                callee_name = orig
                            boundary_calls[(src_subpkg, tgt_subpkg)].append(
                                {
                                    "caller": caller_label,
                                    "callee": callee_name,
                                }
                            )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                caller_label = node.name
                cc = CallCollector()
                cc.visit(node)
                for call_expr in cc.calls:
                    raw = call_expr.split("(")[0]
                    base = raw.split(".")[0]
                    if base in _BUILTINS:
                        continue
                    target_mod = _resolve_call_target(call_expr, import_map)
                    if target_mod is None:
                        continue
                    resolved = target_mod
                    while resolved and resolved not in all_mods:
                        resolved = ".".join(resolved.split(".")[:-1])
                    if not resolved or resolved == mod_name:
                        continue
                    tgt_subpkg = _to_facade_zone(resolved, facade_set)
                    if src_subpkg == tgt_subpkg:
                        continue
                    if "." in raw:
                        callee_name = raw.split(".")[-1]
                    else:
                        _, orig = import_map.get(raw, (None, raw))
                        callee_name = orig
                    boundary_calls[(src_subpkg, tgt_subpkg)].append(
                        {
                            "caller": caller_label,
                            "callee": callee_name,
                        }
                    )

    # -- assemble sorted result --------------------------------------------
    boundaries = []
    for (src, tgt), calls in sorted(
        boundary_calls.items(), key=lambda kv: len(kv[1]), reverse=True
    ):
        seen: set[tuple[str, str]] = set()
        unique_calls = []
        for c in calls:
            key = (c["caller"], c["callee"])
            if key not in seen:
                seen.add(key)
                unique_calls.append(c)
        boundaries.append(
            {
                "source": src,
                "target": tgt,
                "calls": unique_calls,
            }
        )

    boundaries.sort(key=lambda b: len(b["calls"]), reverse=True)

    return {"boundaries": boundaries}
