"""
Top-level complexity analyzer — dispatches by language to the appropriate
analyzer's analyze_complexity implementation.
"""

from app.services.analyzers import ComplexityResult, get_analyzer_by_language

__all__ = ["ComplexityResult", "analyze_complexity"]


def analyze_complexity(
    source_code: str,
    language: str = "python",
    threshold: int = 10,
) -> list[ComplexityResult]:
    """
    Calculate complexity for all functions in the given source code,
    using the analyzer registered for `language`.

    Args:
        source_code: Function source as a string.
        language: Canonical language name from ChangedFunction.language.
        threshold: Functions with score above this are flagged.

    Returns:
        A list of ComplexityResult. Empty when the language has no
        registered analyzer (unreachable under normal dispatch since
        ChangedFunction is only produced by registered analyzers).
    """
    analyzer = get_analyzer_by_language(language)
    if analyzer is None:
        return []
    return analyzer.analyze_complexity(source_code, threshold)
