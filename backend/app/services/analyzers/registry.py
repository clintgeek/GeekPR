"""
Analyzer registry — lookup by file extension or language name.

To add a new language: import the analyzer class here and append an
instance to _ANALYZERS. The registry derives both indexes automatically.
"""

from app.services.analyzers.base import Analyzer
from app.services.analyzers.javascript import JavaScriptAnalyzer
from app.services.analyzers.python import PythonAnalyzer
from app.services.analyzers.rust import RustAnalyzer

# Single source of truth for registered analyzers.
_ANALYZERS: list[Analyzer] = [
    PythonAnalyzer(),
    JavaScriptAnalyzer(),
    RustAnalyzer(),
]

# Derived indexes.
_BY_EXTENSION: dict[str, Analyzer] = {
    ext: analyzer
    for analyzer in _ANALYZERS
    for ext in analyzer.file_extensions
}
_BY_LANGUAGE: dict[str, Analyzer] = {
    analyzer.language: analyzer for analyzer in _ANALYZERS
}


def get_analyzer_for_file(file_path: str) -> Analyzer | None:
    """Look up analyzer by file path. Returns None when no analyzer
    handles the file's extension — the caller should skip the file."""
    for ext, analyzer in _BY_EXTENSION.items():
        if file_path.endswith(ext):
            return analyzer
    return None


def get_analyzer_by_language(language: str) -> Analyzer | None:
    """Look up analyzer by canonical language name
    ('python', 'javascript', 'rust', 'go')."""
    return _BY_LANGUAGE.get(language)


def supported_languages() -> list[str]:
    """List of currently-registered language names, for introspection
    and API responses."""
    return list(_BY_LANGUAGE.keys())
