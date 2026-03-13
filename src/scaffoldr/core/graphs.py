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
    "generate_test_boundary_analysis",
    "build_facade_exports",
    "detect_cycles",
    "generate_init_hygiene",
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
            # ``__all__ = [...]`` (plain assignment)
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
            # ``__all__: list[str] = [...]`` (annotated assignment)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == "__all__":
                    has_all = True
                    if node.value is not None and isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(
                                elt.value, str
                            ):
                                all_names.add(elt.value)

        if has_all:
            # __all__ is the authoritative facade — nothing else matters.
            # An empty __all__ explicitly declares "no public exports" — this
            # is a namespace-only package, not a facade boundary.
            if all_names:
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

        # Only register as a facade if there are actual exports
        # (an __init__.py with only a docstring is just a namespace marker,
        # not a facade boundary)
        if exports:
            facade_exports[mod_name] = exports

    return facade_exports


def generate_facade_leaks(
    all_analysis: dict[str, dict[str, Any]],
    all_trees: dict[str, ast.Module],
    facade_exports: dict[str, set[str]],
    test_modules: set[str] | None = None,
) -> dict[str, Any]:
    """Detect facade bypasses at any depth (unified leak detection).

    Scans import statements (not calls) to find modules that import from a
    package's internals instead of through its __init__.py facade.  Covers
    both inter-package and intra-package leaks in a single pass.

    When *test_modules* is provided, modules whose name is in the set are
    skipped — test-file leaks are reported separately by
    ``generate_test_boundary_analysis()``.

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
        # Skip test modules — their leaks are handled by test boundary analysis
        if test_modules and mod_name in test_modules:
            continue
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


def generate_test_boundary_analysis(
    all_analysis: dict[str, dict[str, Any]],
    all_trees: dict[str, ast.Module],
    facade_exports: dict[str, set[str]],
    test_modules: set[str],
) -> dict[str, Any]:
    """Analyse test files for facade boundary violations and facade coverage.

    Two outputs:

    1. **Boundary violations** — test modules that import from a package's
       internal modules instead of through its ``__init__.py`` facade.
       Sub-classified as:
       - *path violation*: the imported name IS in ``__all__`` but the import
         path bypasses the facade (less severe — fix the import path).
       - *internal test*: the imported name is NOT in ``__all__`` (the test
         exercises an internal that the facade does not expose).

    2. **Facade coverage** — for each facade with ``__all__``, which exports
       are imported by at least one test module (directly through the facade).

    Returns a dict matching the documented output schema.
    """
    all_mod_names = set(all_analysis.keys())

    # ---- Part 1: boundary violations ------------------------------------
    violations: list[dict[str, Any]] = []

    for mod_name in sorted(test_modules):
        tree = all_trees.get(mod_name)
        if tree is None:
            continue

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

            # Find the common parent between test module and target
            imp_parts = mod_name.split(".")
            tgt_parts = resolved.split(".")

            common_len = 0
            for i in range(min(len(imp_parts), len(tgt_parts))):
                if imp_parts[i] == tgt_parts[i]:
                    common_len = i + 1
                else:
                    break

            if common_len == 0:
                continue

            if len(tgt_parts) <= common_len:
                continue  # Target IS the common parent — not a sub-package import

            sibling_pkg = ".".join(tgt_parts[: common_len + 1])

            # Skip if the test IS inside the sibling package
            if mod_name == sibling_pkg or mod_name.startswith(sibling_pkg + "."):
                continue

            # Skip if importing directly from the sibling facade
            if resolved == sibling_pkg:
                continue

            # Target is an internal module of sibling_pkg — check facade
            if sibling_pkg not in facade_exports:
                continue

            facade_names = facade_exports[sibling_pkg]
            imported_names = []
            available: list[str] = []
            missing: list[str] = []
            for alias in node.names or []:
                name = alias.name
                imported_names.append(name)
                if name in facade_names:
                    available.append(name)
                else:
                    missing.append(name)

            if not imported_names:
                continue

            violations.append(
                {
                    "test_module": mod_name,
                    "imported_from": resolved,
                    "facade": sibling_pkg,
                    "names": imported_names,
                    "available_in_facade": available,
                    "missing_from_facade": missing,
                }
            )

    # ---- Part 2: facade coverage -----------------------------------------
    # For each facade, check which __all__ exports are imported by test modules
    # via "from <facade> import X" statements.
    facade_coverage: list[dict[str, Any]] = []

    for facade_mod, exports in sorted(facade_exports.items()):
        if not exports:
            continue

        # Collect names that tests import from this facade
        covered_names: set[str] = set()
        for test_mod in sorted(test_modules):
            tree = all_trees.get(test_mod)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                # Resolve module path
                src_mod = node.module or ""
                level = node.level or 0
                if level > 0:
                    parts = test_mod.split(".")
                    if level <= len(parts):
                        base = ".".join(parts[: len(parts) - level])
                        src_mod = f"{base}.{src_mod}" if src_mod else base
                if src_mod != facade_mod:
                    continue
                # This test imports from the facade directly
                for alias in node.names or []:
                    name = alias.name
                    if name in exports:
                        covered_names.add(name)

        covered = sorted(covered_names)
        uncovered = sorted(exports - covered_names)
        total = len(exports)
        pct = (len(covered) / total * 100.0) if total > 0 else 0.0

        facade_coverage.append(
            {
                "facade": facade_mod,
                "total_exports": total,
                "covered": covered,
                "uncovered": uncovered,
                "coverage_pct": round(pct, 1),
            }
        )

    total_facades = len(facade_coverage)
    avg_pct = (
        sum(fc["coverage_pct"] for fc in facade_coverage) / total_facades
        if total_facades > 0
        else 0.0
    )

    return {
        "boundary_violations": violations,
        "facade_coverage": facade_coverage,
        "total_violations": len(violations),
        "total_facades": total_facades,
        "average_coverage_pct": round(avg_pct, 1),
    }


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


def detect_cycles(dep_graph: dict[str, Any]) -> dict[str, Any]:
    """Detect circular dependencies in the package-level dependency graph.

    Uses Tarjan's algorithm (iterative) to find strongly connected components
    (SCCs).  An SCC with more than one node is a cycle.

    Parameters:
        dep_graph: Output from generate_dependency_graph() — must have
                   "package_level" key with {node: [deps]} adjacency list.

    Returns:
        {"cycles": [{"nodes": [str], "edges": [{"from": str, "to": str}]}],
         "total_cycles": int,
         "total_nodes_in_cycles": int}
    """
    pkg_level: dict[str, list[str]] = dep_graph.get("package_level", {})

    # Collect all nodes (sources and targets)
    all_nodes: set[str] = set(pkg_level.keys())
    for dsts in pkg_level.values():
        all_nodes.update(dsts)

    # Adjacency list (default to empty for sink nodes)
    adj: dict[str, list[str]] = {n: list(pkg_level.get(n, [])) for n in all_nodes}

    # --- Iterative Tarjan's algorithm ---
    index_counter = 0
    node_index: dict[str, int] = {}
    node_lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    sccs: list[list[str]] = []

    # Each frame: (node, neighbor_list, neighbor_index, phase)
    # phase 0 = initial visit, phase 1 = returning from recursive call
    INITIAL = 0
    RESUME = 1

    for start in sorted(all_nodes):
        if start in node_index:
            continue

        call_stack: list[tuple[str, list[str], int, int]] = [
            (start, adj[start], 0, INITIAL)
        ]

        while call_stack:
            node, neighbors, ni, phase = call_stack.pop()

            if phase == INITIAL:
                node_index[node] = index_counter
                node_lowlink[node] = index_counter
                index_counter += 1
                stack.append(node)
                on_stack.add(node)

            if phase == RESUME:
                # Returning from visiting neighbors[ni-1]
                child = neighbors[ni - 1]
                if node_lowlink[child] < node_lowlink[node]:
                    node_lowlink[node] = node_lowlink[child]

            # Continue iterating through neighbors
            pushed = False
            while ni < len(neighbors):
                w = neighbors[ni]
                ni += 1
                if w not in node_index:
                    # Push current frame (to resume after w is processed)
                    call_stack.append((node, neighbors, ni, RESUME))
                    # Push new frame for w
                    call_stack.append((w, adj[w], 0, INITIAL))
                    pushed = True
                    break
                elif w in on_stack:
                    if node_index[w] < node_lowlink[node]:
                        node_lowlink[node] = node_index[w]

            if pushed:
                continue

            # All neighbors processed — check if node is an SCC root
            if node_lowlink[node] == node_index[node]:
                scc: list[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    scc.append(w)
                    if w == node:
                        break
                if len(scc) > 1:
                    sccs.append(scc)

    # --- Build result ---
    cycles: list[dict[str, Any]] = []
    for scc in sccs:
        scc_set = set(scc)
        nodes_sorted = sorted(scc)
        # Collect internal edges (both endpoints in the SCC)
        edges: list[dict[str, str]] = []
        for src in nodes_sorted:
            for dst in sorted(adj.get(src, [])):
                if dst in scc_set:
                    edges.append({"from": src, "to": dst})
        cycles.append({"nodes": nodes_sorted, "edges": edges})

    # Sort cycles by size (largest first)
    cycles.sort(key=lambda c: len(c["nodes"]), reverse=True)

    total_nodes = sum(len(c["nodes"]) for c in cycles)

    return {
        "cycles": cycles,
        "total_cycles": len(cycles),
        "total_nodes_in_cycles": total_nodes,
    }


# Stdlib modules commonly used as infrastructure in __init__.py files.
# ``import importlib`` (or ``import importlib as _importlib``) is lazy-loading
# plumbing, not a structural coupling issue.  Suppress NON_FROM_IMPORT for these.
_STDLIB_INFRA_MODULES = frozenset({
    "importlib", "sys", "types", "os", "warnings", "functools",
    "typing", "collections", "abc", "enum", "pathlib",
})

# Imports that are language features or stdlib utilities, not package exports.
# Suppress ORPHAN_IMPORT for these when they appear as from-imports in __init__.py.
_INFRA_IMPORT_NAMES = frozenset({
    "annotations",   # from __future__ import annotations — language feature
    "ModuleType",    # from types import ModuleType — lazy-loading utility
    "TYPE_CHECKING", # from typing import TYPE_CHECKING — type-checking guard
})


def generate_init_hygiene(
    all_analysis: dict[str, dict[str, Any]],
    all_trees: dict[str, ast.Module],
) -> dict[str, Any]:
    """Check ``__init__.py`` files for hygiene violations.

    Inspects every package ``__init__.py`` AST for structural rules:

    - ``NO_ALL``: missing ``__all__``
    - ``BARE_CODE``: statements beyond imports / ``__all__`` / ``__version__`` /
      ``__getattr__`` / ``__dir__`` / docstrings / lazy-map dicts used by
      ``__getattr__``
    - ``PRIVATE_EXPORT``: ``__all__`` exports names starting with ``_``
      (excluding dunder names like ``__version__``)
    - ``ALL_MISMATCH``: name in ``__all__`` not importable (not from-imported,
      not defined, not in a ``__getattr__`` lazy map, and not resolved by
      ``__getattr__`` via ``if name == "X"`` / ``if name in __all__``)
    - ``NON_FROM_IMPORT``: uses ``import X`` instead of ``from X import ...``
      (suppressed for stdlib infrastructure modules like ``importlib``, ``sys``)
    - ``ORPHAN_IMPORT``: ``from`` import not listed in ``__all__``
      (suppressed for ``from __future__ import annotations`` and stdlib
      type imports like ``ModuleType``)

    Returns:
        {"issues": [{"module": str, "check": str, "severity": str,
                      "message": str, "line": int | None}],
         "packages_checked": int,
         "clean_packages": int,
         "total_issues": int}
    """
    all_mod_names = set(all_analysis.keys())
    issues: list[dict[str, Any]] = []
    packages_checked = 0
    clean_packages = 0

    for mod_name in sorted(all_mod_names):
        # Only package __init__.py files
        prefix = mod_name + "."
        has_children = any(m.startswith(prefix) for m in all_mod_names)
        if not has_children:
            continue

        tree = all_trees.get(mod_name)
        if tree is None:
            continue

        packages_checked += 1
        mod_issues: list[dict[str, Any]] = []

        # --- Extract __all__, __getattr__, from-imports, etc. from AST ---
        has_all = False
        all_names: set[str] = set()
        all_line: int | None = None
        has_getattr = False
        getattr_dict_names: set[str] = set()  # dicts referenced in __getattr__
        lazy_map_keys: set[str] = set()  # keys from those dicts
        from_imported_names: set[str] = set()  # names brought in by `from ... import`
        defined_names: set[str] = set()  # classes/functions defined in __init__
        non_from_imports: list[tuple[str, int]] = []  # (module, line)
        bare_code_lines: list[tuple[str, int]] = []  # (description, line)

        # Track whether __getattr__ uses ``if name in __all__`` to resolve
        # all names in __all__ lazily.
        getattr_resolves_all: bool = False
        # String literals from ``if name == "X"`` in __getattr__
        getattr_literal_names: set[str] = set()

        # First pass: identify __getattr__ and which dict names it references
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "__getattr__":
                    has_getattr = True
                    # Find dict names referenced via .get(name) or [name] patterns
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call):
                            func = sub.func
                            if (
                                isinstance(func, ast.Attribute)
                                and func.attr == "get"
                                and isinstance(func.value, ast.Name)
                            ):
                                getattr_dict_names.add(func.value.id)
                        if isinstance(sub, ast.Subscript):
                            if isinstance(sub.value, ast.Name):
                                getattr_dict_names.add(sub.value.id)
                        # ``if name in some_dict`` — membership test on a variable
                        if isinstance(sub, ast.Compare):
                            if (
                                len(sub.ops) == 1
                                and isinstance(sub.ops[0], ast.In)
                                and len(sub.comparators) == 1
                            ):
                                comp = sub.comparators[0]
                                if isinstance(comp, ast.Name):
                                    if comp.id == "__all__":
                                        # ``if name in __all__`` — all names in __all__ are resolved
                                        getattr_resolves_all = True
                                    else:
                                        # ``if name in _ROUTE`` — treat as dict lookup
                                        getattr_dict_names.add(comp.id)
                        # ``if name == "literal"`` — direct string comparison
                        if isinstance(sub, ast.Compare):
                            if (
                                len(sub.ops) == 1
                                and isinstance(sub.ops[0], ast.Eq)
                                and len(sub.comparators) == 1
                            ):
                                comp = sub.comparators[0]
                                if isinstance(comp, ast.Constant) and isinstance(
                                    comp.value, str
                                ):
                                    getattr_literal_names.add(comp.value)

        # Second pass: collect all names from lazy-load dicts
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id in getattr_dict_names
                        and isinstance(node.value, ast.Dict)
                    ):
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant) and isinstance(
                                key.value, str
                            ):
                                lazy_map_keys.add(key.value)

        # Third pass: full analysis
        for node in ast.iter_child_nodes(tree):
            # __all__ assignment (plain: ``__all__ = [...]``)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        has_all = True
                        all_line = node.lineno
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(
                                    elt.value, str
                                ):
                                    all_names.add(elt.value)

            # __all__ annotated assignment (``__all__: list[str] = [...]``)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == "__all__":
                    has_all = True
                    all_line = node.lineno
                    if node.value is not None and isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(
                                elt.value, str
                            ):
                                all_names.add(elt.value)

            # from ... import ...
            if isinstance(node, ast.ImportFrom):
                for alias in node.names or []:
                    local_name = alias.asname if alias.asname else alias.name
                    from_imported_names.add(local_name)

            # import X (non-from)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local_name = alias.asname if alias.asname else alias.name
                    non_from_imports.append((local_name, node.lineno))

            # Class/function definitions
            if isinstance(node, ast.ClassDef):
                defined_names.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defined_names.add(node.name)

            # Top-level assignments (e.g., ``__version__ = "1.0"``)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id != "__all__":
                        defined_names.add(target.id)

            # Bare code detection — check for statements that aren't allowed
            if _is_bare_code(node, getattr_dict_names):
                desc = _describe_node(node)
                bare_code_lines.append((desc, node.lineno))

        # --- Generate issues ---

        # NO_ALL
        if not has_all:
            mod_issues.append({
                "module": mod_name,
                "check": "NO_ALL",
                "severity": "error",
                "message": "__init__.py has no __all__",
                "line": None,
            })

        # BARE_CODE
        for desc, line in bare_code_lines:
            mod_issues.append({
                "module": mod_name,
                "check": "BARE_CODE",
                "severity": "warning",
                "message": f"bare code: {desc}",
                "line": line,
            })

        # NON_FROM_IMPORT — suppress for stdlib modules (infrastructure, not coupling)
        for imp_name, line in non_from_imports:
            # Strip leading underscores (alias convention: ``import importlib as _importlib``)
            bare_name = imp_name.lstrip("_")
            if bare_name in _STDLIB_INFRA_MODULES:
                continue
            mod_issues.append({
                "module": mod_name,
                "check": "NON_FROM_IMPORT",
                "severity": "warning",
                "message": f"non-from import: import {imp_name}",
                "line": line,
            })

        # PRIVATE_EXPORT
        if has_all:
            for name in sorted(all_names):
                if name.startswith("_") and not (
                    name.startswith("__") and name.endswith("__")
                ):
                    mod_issues.append({
                        "module": mod_name,
                        "check": "PRIVATE_EXPORT",
                        "severity": "warning",
                        "message": f"__all__ exports private name: {name}",
                        "line": all_line,
                    })

        # ALL_MISMATCH — names in __all__ not found in any source
        if has_all:
            known_names = from_imported_names | defined_names | lazy_map_keys | getattr_literal_names
            for name in sorted(all_names):
                if name not in known_names:
                    # If __getattr__ uses ``if name in __all__``, all names
                    # in __all__ are resolved lazily — not a mismatch.
                    if getattr_resolves_all:
                        continue
                    mod_issues.append({
                        "module": mod_name,
                        "check": "ALL_MISMATCH",
                        "severity": "error",
                        "message": f"__all__ lists '{name}' but it is not imported or defined",
                        "line": all_line,
                    })

        # ORPHAN_IMPORT — from-imported but not in __all__
        if has_all:
            for name in sorted(from_imported_names):
                if name not in all_names:
                    # Suppress infrastructure imports that are never package exports
                    if name in _INFRA_IMPORT_NAMES:
                        continue
                    mod_issues.append({
                        "module": mod_name,
                        "check": "ORPHAN_IMPORT",
                        "severity": "info",
                        "message": f"from-import '{name}' not listed in __all__",
                        "line": None,
                    })

        if not mod_issues:
            clean_packages += 1
        issues.extend(mod_issues)

    return {
        "issues": issues,
        "packages_checked": packages_checked,
        "clean_packages": clean_packages,
        "total_issues": len(issues),
    }


def _is_bare_code(node: ast.AST, getattr_dict_names: set[str]) -> bool:
    """Return True if *node* is a bare-code statement in ``__init__.py``.

    Allowed top-level statements:
    - ``from X import Y`` (ImportFrom)
    - ``import X`` (Import — flagged separately as NON_FROM_IMPORT but not bare code)
    - ``__all__ = [...]`` (Assign to __all__)
    - ``def __getattr__`` / ``def __dir__`` (FunctionDef)
    - Module docstring (Expr with Constant string as first statement)
    - Dict assignment where the name is referenced by __getattr__ (lazy map infra)
    - Comments (not in AST)
    """
    # Imports — always allowed
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return False

    # Function defs: __getattr__, __dir__ allowed; others are bare code
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name in ("__getattr__", "__dir__"):
            return False
        return True

    # Class defs — bare code in __init__
    if isinstance(node, ast.ClassDef):
        return True

    # Assignments
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                # __all__ is allowed
                if target.id == "__all__":
                    return False
                # __version__ is standard package metadata
                if target.id == "__version__":
                    return False
                # Dict assignments used by __getattr__ are allowed
                if target.id in getattr_dict_names and isinstance(
                    node.value, ast.Dict
                ):
                    return False
        # Any other assignment is bare code
        return True

    # Expression statements — only module docstring allowed
    if isinstance(node, ast.Expr):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return False  # docstring
        return True

    # If/Try/With etc. — bare code
    if isinstance(node, (ast.If, ast.Try, ast.With, ast.For, ast.While)):
        return True

    return False


def _describe_node(node: ast.AST) -> str:
    """Return a short description of an AST node for diagnostic messages."""
    if isinstance(node, ast.ClassDef):
        return f"class {node.name}"
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return f"def {node.name}()"
    if isinstance(node, ast.Assign):
        targets = []
        for t in node.targets:
            if isinstance(t, ast.Name):
                targets.append(t.id)
            else:
                targets.append(ast.unparse(t))
        return f"assignment: {', '.join(targets)} = ..."
    if isinstance(node, ast.Expr):
        return "expression statement"
    if isinstance(node, ast.If):
        return "if statement"
    if isinstance(node, ast.Try):
        return "try/except block"
    return type(node).__name__
