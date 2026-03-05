"""Core analysis primitives — language-agnostic graphs, formatters, and types."""

from .types import AnalysisResult, ModuleAnalysis
from .graphs import (
    shorten_module,
    generate_dependency_graph,
    generate_class_hierarchy,
    generate_entry_point_map,
    generate_coupling_density,
    find_function_calls,
    CallCollector,
)
from .formatters import (
    format_dependency_mermaid,
    format_dependency_text,
    format_class_tree_text,
    format_entry_points_text,
    format_coupling_density_text,
    format_toon,
)

__all__ = [
    "AnalysisResult",
    "ModuleAnalysis",
    "shorten_module",
    "generate_dependency_graph",
    "generate_class_hierarchy",
    "generate_entry_point_map",
    "generate_coupling_density",
    "find_function_calls",
    "CallCollector",
    "format_dependency_mermaid",
    "format_dependency_text",
    "format_class_tree_text",
    "format_entry_points_text",
    "format_coupling_density_text",
    "format_toon",
]
