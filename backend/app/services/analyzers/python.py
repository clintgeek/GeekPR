"""
Python analyzer.

Reference implementation for the Analyzer protocol. Uses:
  - regex for function extraction from added diff lines
  - radon for cyclomatic complexity
  - bandit for security scanning (subprocess)

Behavior matches the pre-multi-language implementation exactly so the
refactor is invariant-preserving for Python-only callers.
"""

import json
import re
import subprocess
import tempfile
from typing import ClassVar

from radon.complexity import cc_visit

from app.services.analyzers.base import (
    ChangedFunction,
    ComplexityResult,
    SecurityIssue,
)


# Module-level so it survives across calls without re-compilation.
_FUNC_PATTERN = re.compile(
    r"^([ \t]*)def\s+(\w+)\s*\(.*?\).*?:",
    re.MULTILINE,
)


class PythonAnalyzer:
    language: ClassVar[str] = "python"
    file_extensions: ClassVar[tuple[str, ...]] = (".py",)

    def extract_changed_functions(self, patched_file) -> list[ChangedFunction]:
        added_lines = []
        for hunk in patched_file:
            for line in hunk:
                if line.is_added:
                    added_lines.append((line.target_line_no, line.value))

        if not added_lines:
            return []

        full_added_text = "\n".join(line_text for _, line_text in added_lines)
        start_line = added_lines[0][0]

        results = []
        for match in _FUNC_PATTERN.finditer(full_added_text):
            indent = match.group(1)
            func_name = match.group(2)
            func_start = match.start()

            # Walk forward until we hit a line whose indent is less than
            # or equal to the def's indent — that's the end of the body.
            remaining = full_added_text[match.end():]
            func_body_lines = []
            for body_line in remaining.split("\n"):
                if body_line.strip() == "":
                    func_body_lines.append(body_line)
                    continue
                if body_line.startswith(indent + " ") or body_line.startswith(indent + "\t"):
                    func_body_lines.append(body_line)
                else:
                    break

            func_source = full_added_text[func_start:match.end()] + "\n".join(func_body_lines)

            results.append(ChangedFunction(
                file_path=patched_file.path,
                function_name=func_name,
                source_code=func_source.strip(),
                start_line=start_line,
                end_line=start_line + len(func_body_lines),
                language=self.language,
            ))

        return results

    def analyze_complexity(self, source_code: str, threshold: int) -> list[ComplexityResult]:
        try:
            blocks = cc_visit(source_code)
        except SyntaxError:
            return []

        return [
            ComplexityResult(
                function_name=block.name,
                score=block.complexity,
                rank=block.letter,
                is_flagged=block.complexity > threshold,
            )
            for block in blocks
        ]

    def run_security_scan(self, source_code: str) -> list[SecurityIssue]:
        # Bandit requires a file on disk.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(source_code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ["bandit", "-f", "json", "-q", tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = json.loads(result.stdout) if result.stdout else {"results": []}
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            # FileNotFoundError = bandit not installed; fail-open.
            return []

        return [
            SecurityIssue(
                test_id=item.get("test_id", ""),
                description=item.get("issue_text", ""),
                severity=item.get("issue_severity", "LOW"),
                confidence=item.get("issue_confidence", "LOW"),
                line_number=item.get("line_number", 0),
            )
            for item in output.get("results", [])
        ]
