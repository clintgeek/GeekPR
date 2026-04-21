"""
Analyzer protocol + shared result dataclasses.

The protocol is language-agnostic so that adding Rust, Go, or JavaScript
doesn't require touching the pipeline in analyze_pr.py — the registry
looks up the right analyzer by file extension and the pipeline calls
the same three methods regardless of language.
"""

from dataclasses import dataclass
from typing import ClassVar, Protocol, runtime_checkable


@dataclass
class ChangedFunction:
    """Represents a function that was added or modified in a diff."""
    file_path: str
    function_name: str
    source_code: str
    start_line: int
    end_line: int
    language: str


@dataclass
class ComplexityResult:
    """Result of analyzing a function's complexity.

    `rank` is analyzer-defined: Radon uses A-F for Python; other analyzers
    may use numeric buckets or their own scheme. `score` is the raw
    cyclomatic-complexity number (comparable across languages when the
    tool reports CC; approximated otherwise).
    """
    function_name: str
    score: int
    rank: str
    is_flagged: bool


@dataclass
class SecurityIssue:
    """A security issue found by a language-specific scanner.

    `test_id` is the scanner's rule identifier (B101 for Bandit,
    eslint rule name for eslint-plugin-security, clippy lint name, etc.).
    """
    test_id: str
    description: str
    severity: str  # "LOW" | "MEDIUM" | "HIGH"
    confidence: str  # "LOW" | "MEDIUM" | "HIGH"
    line_number: int


@runtime_checkable
class Analyzer(Protocol):
    """Language-specific analyzer contract.

    Implementations live in sibling modules (python.py, javascript.py,
    rust.py, go.py) and are registered in registry.py.
    """

    # Canonical language name ("python", "javascript", "rust", "go").
    # Stored on ChangedFunction and used for language-keyed lookups.
    language: ClassVar[str]

    # File extensions this analyzer handles, with leading dot
    # (".py", ".js", ".rs", ".go"). Used by the registry to pick
    # an analyzer per file in a diff.
    file_extensions: ClassVar[tuple[str, ...]]

    def extract_changed_functions(self, patched_file) -> list[ChangedFunction]:
        """Parse added/modified lines in a single unidiff PatchedFile
        into ChangedFunction records. Empty list if nothing of interest."""
        ...

    def analyze_complexity(self, source_code: str, threshold: int) -> list[ComplexityResult]:
        """Return complexity metrics for every function in source_code.
        Functions with score > threshold must have is_flagged=True."""
        ...

    def run_security_scan(self, source_code: str) -> list[SecurityIssue]:
        """Run the language's security scanner on source_code. Empty list
        if no issues or the scanner is unavailable (fail-open)."""
        ...
