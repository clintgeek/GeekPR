import pytest
from app.services.complexity import analyze_complexity


def test_simple_function_not_flagged():
    """Simple functions should not be flagged."""
    code = "def add(a, b):\n    return a + b\n"
    results = analyze_complexity(code, threshold=10)
    assert len(results) == 1
    assert results[0].function_name == "add"
    assert results[0].is_flagged is False
    assert results[0].score <= 10


def test_complex_function_flagged():
    """Complex functions with high CC should be flagged."""
    code = """
def nightmare(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                if x > y:
                    if y > z:
                        if x > z:
                            if x + y > z:
                                if x - y < z:
                                    if x * y > z:
                                        if x / (y+1) > z:
                                            return True
    return False
"""
    results = analyze_complexity(code, threshold=5)
    assert len(results) == 1
    assert results[0].function_name == "nightmare"
    assert results[0].is_flagged is True
    assert results[0].score > 5


def test_multiple_functions():
    """Should analyze all functions in code."""
    code = """
def simple():
    return 42

def complex(a, b, c):
    if a:
        if b:
            if c:
                return True
    return False
"""
    results = analyze_complexity(code, threshold=3)
    assert len(results) == 2
    assert results[0].function_name == "simple"
    assert results[0].is_flagged is False
    assert results[1].function_name == "complex"
    assert results[1].is_flagged is True


def test_syntax_error_returns_empty():
    """Invalid Python should return empty list."""
    code = "def broken(\n    return x"
    results = analyze_complexity(code)
    assert results == []
