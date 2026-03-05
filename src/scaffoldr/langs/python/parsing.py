"""AST visitors and analysis for Python modules."""

import ast
import sys
from pathlib import Path
from typing import Any

__all__ = [
    "ImportCollector",
    "ClassCollector",
    "FunctionCollector",
    "parse_file",
    "analyze_module",
]


class ImportCollector(ast.NodeVisitor):
    """Collects import statements from a module."""

    def __init__(self, module_name: str, project_packages: set[str]):
        self.module_name = module_name
        self.project_packages = project_packages
        self.imports: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            top = alias.name.split(".")[0]
            if top in self.project_packages:
                self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            top = node.module.split(".")[0]
            if top in self.project_packages:
                self.imports.add(node.module)
            # Handle relative imports
            if node.level and node.level > 0:
                parts = self.module_name.split(".")
                if node.level <= len(parts):
                    base = ".".join(parts[: len(parts) - node.level])
                    if node.module:
                        resolved = f"{base}.{node.module}"
                    else:
                        resolved = base
                    self.imports.add(resolved)
        self.generic_visit(node)


class ClassCollector(ast.NodeVisitor):
    """Collects class definitions and their bases."""

    def __init__(self):
        self.classes: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(ast.unparse(base))
            elif isinstance(base, ast.Subscript):
                # e.g. Generic[T]
                bases.append(ast.unparse(base))
        self.classes.append(
            {
                "name": node.name,
                "bases": bases,
                "line": node.lineno,
                "methods": [
                    n.name
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ],
                "decorators": [ast.unparse(d) for d in node.decorator_list],
            }
        )
        self.generic_visit(node)


class FunctionCollector(ast.NodeVisitor):
    """Collects top-level function definitions."""

    def __init__(self):
        self.functions: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Only top-level functions (not nested in class)
        self.functions.append(
            {
                "name": node.name,
                "line": node.lineno,
                "args": [arg.arg for arg in node.args.args if arg.arg != "self"],
                "decorators": [ast.unparse(d) for d in node.decorator_list],
            }
        )
        # Don't recurse into function body for top-level scan

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append(
            {
                "name": node.name,
                "line": node.lineno,
                "args": [arg.arg for arg in node.args.args if arg.arg != "self"],
                "decorators": [ast.unparse(d) for d in node.decorator_list],
            }
        )


def parse_file(filepath: Path) -> ast.Module | None:
    """Parse a Python file, returning AST or None on failure."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        return ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        print(f"  [WARN] SyntaxError in {filepath}: {e}", file=sys.stderr)
        return None


def analyze_module(
    mod_name: str, tree: ast.Module, project_packages: set[str]
) -> dict[str, Any]:
    """Analyze a single module's AST."""
    # Imports
    imp = ImportCollector(mod_name, project_packages)
    imp.visit(tree)

    # Classes
    cls = ClassCollector()
    cls.visit(tree)

    # Top-level functions
    fn = FunctionCollector()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn.visit(node)

    return {
        "imports": sorted(imp.imports),
        "classes": cls.classes,
        "functions": fn.functions,
    }
