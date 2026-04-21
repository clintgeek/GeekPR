"""
Top-level security scanner — dispatches by language to the appropriate
analyzer's run_security_scan implementation.

Renamed-in-spirit from the original run_bandit_scan; Bandit remains the
tool for Python but is now an implementation detail of PythonAnalyzer.
"""

from app.services.analyzers import SecurityIssue, get_analyzer_by_language

__all__ = ["SecurityIssue", "run_security_scan", "run_bandit_scan"]


def run_security_scan(source_code: str, language: str) -> list[SecurityIssue]:
    """
    Run the language's security scanner on source_code.

    Args:
        source_code: Function source as a string.
        language: Canonical language name from ChangedFunction.language.

    Returns:
        A list of SecurityIssue. Empty when the language has no registered
        analyzer or the scanner is unavailable (fail-open).
    """
    analyzer = get_analyzer_by_language(language)
    if analyzer is None:
        return []
    return analyzer.run_security_scan(source_code)


# Backwards-compatible alias — Python-only pre-refactor callers still work.
def run_bandit_scan(source_code: str) -> list[SecurityIssue]:
    """Deprecated: use run_security_scan(source_code, 'python')."""
    return run_security_scan(source_code, "python")
