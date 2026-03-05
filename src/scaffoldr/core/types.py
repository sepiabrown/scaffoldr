"""Plugin contract types for structural analysis."""

from typing import Any, TypedDict

__all__ = ["ModuleAnalysis", "AnalysisResult"]


class ModuleAnalysis(TypedDict):
    imports: list[str]
    classes: list[dict[str, Any]]
    functions: list[dict[str, Any]]


class AnalysisResult(TypedDict):
    workspace_name: str
    packages: dict[str, str]
    entry_points: dict[str, str]
    modules: dict[str, Any]
    all_analysis: dict[str, ModuleAnalysis]
    all_trees: dict[str, Any]
    parse_errors: int
