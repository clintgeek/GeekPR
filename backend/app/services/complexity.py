from dataclasses import dataclass

from radon.complexity import cc_visit


@dataclass
class ComplexityResult:
    """Result of analyzing a function's cyclomatic complexity."""
    function_name: str
    score: int
    rank: str
    is_flagged: bool


def analyze_complexity(source_code: str, threshold: int = 10) -> list[ComplexityResult]:
    """
    Calculate the Cyclomatic Complexity of all functions in the given source code.

    Args:
        source_code: A string of Python source code.
        threshold: Functions with CC above this are flagged.

    Returns:
        A list of ComplexityResult for every function found.
    """
    try:
        blocks = cc_visit(source_code)
    except SyntaxError:
        return []

    results = []
    for block in blocks:
        results.append(ComplexityResult(
            function_name=block.name,
            score=block.complexity,
            rank=block.letter,
            is_flagged=block.complexity > threshold,
        ))

    return results
