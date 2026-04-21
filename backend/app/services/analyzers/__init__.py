"""
Language-dispatched code analyzers.

Each analyzer implements the Analyzer protocol (see base.py) and is
registered in registry.py by file extension + language name. The top-level
service entry points (diff_analyzer, complexity, security_scan) dispatch
to the appropriate analyzer per file.

Adding a new language = drop a new module in this package, implement the
protocol, register it in registry.py. See python.py for the reference
implementation.
"""

from app.services.analyzers.base import (
    Analyzer,
    ChangedFunction,
    ComplexityResult,
    SecurityIssue,
)
from app.services.analyzers.registry import (
    get_analyzer_for_file,
    get_analyzer_by_language,
    supported_languages,
)

__all__ = [
    "Analyzer",
    "ChangedFunction",
    "ComplexityResult",
    "SecurityIssue",
    "get_analyzer_for_file",
    "get_analyzer_by_language",
    "supported_languages",
]
