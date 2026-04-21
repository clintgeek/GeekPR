"""
Top-level diff analyzer — dispatches per-file to language-specific analyzers.

Kept as a module-level function (not a class) to preserve the existing
public API for analyze_pr.py. Language detection happens by file extension
via the analyzer registry.
"""

from unidiff import PatchSet

from app.services.analyzers import ChangedFunction, get_analyzer_for_file

__all__ = ["ChangedFunction", "extract_changed_functions"]


def extract_changed_functions(diff_text: str) -> list[ChangedFunction]:
    """
    Parse a unified diff and extract functions that were added or modified,
    dispatching per file to the analyzer registered for that extension.

    Args:
        diff_text: The raw unified diff string from GitHub.

    Returns:
        A list of ChangedFunction objects across every recognized file.
        Files whose extension has no registered analyzer are skipped.
    """
    patch = PatchSet(diff_text)
    results: list[ChangedFunction] = []

    for patched_file in patch:
        analyzer = get_analyzer_for_file(patched_file.path)
        if analyzer is None:
            continue
        results.extend(analyzer.extract_changed_functions(patched_file))

    return results
