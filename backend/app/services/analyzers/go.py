"""
Go analyzer.

Mirrors the Python analyzer's shape but shells out to Go-ecosystem tools:
  - regex + brace-counting for function extraction from added diff lines
  - gocyclo for cyclomatic complexity
  - gosec for security scanning

Both external tools are invoked via subprocess with fail-open behavior:
when a tool isn't installed, times out, or returns unparseable output,
the analyzer returns an empty list rather than raising.
"""

import json
import re
import subprocess
import tempfile
from typing import ClassVar

from app.services.analyzers.base import (
    ChangedFunction,
    ComplexityResult,
    SecurityIssue,
)


# Matches top-level funcs and methods: `func name(` or `func (r *T) name(`.
_FUNC_PATTERN = re.compile(
    r"^func\s+(?:\(\s*\w+\s+\*?\w+\s*\)\s+)?(\w+)\s*\(",
    re.MULTILINE,
)

# gocyclo output: `<score> <package> <function> <file>:<line>:<col>`
_GOCYCLO_LINE = re.compile(
    r"^\s*(\d+)\s+\S+\s+(\S+)\s+\S+:\d+:\d+\s*$"
)


def _rank_for(score: int) -> str:
    if score <= 5:
        return "A"
    if score <= 10:
        return "B"
    if score <= 20:
        return "C"
    if score <= 30:
        return "D"
    return "F"


def _find_body_end(text: str, start: int) -> int:
    """Given an index at/after a function signature, find the index one
    past the closing brace of the function body. Returns len(text) if the
    body is truncated (common with partial diff snippets).

    Skips content inside strings, raw strings, line comments, and block
    comments so braces in those don't throw off the count.
    """
    i = start
    n = len(text)
    # Locate the opening brace of the body.
    while i < n and text[i] != "{":
        # Bail if we hit something that clearly isn't a signature char;
        # but be lenient — multi-line signatures include newlines, commas,
        # parens, identifiers, etc.
        i += 1
    if i >= n:
        return n

    depth = 0
    while i < n:
        ch = text[i]
        # Line comment.
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            nl = text.find("\n", i)
            i = n if nl == -1 else nl + 1
            continue
        # Block comment.
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        # Raw string — no escapes.
        if ch == "`":
            end = text.find("`", i + 1)
            i = n if end == -1 else end + 1
            continue
        # Interpreted string — escape-aware.
        if ch == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            i = j + 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


class GoAnalyzer:
    language: ClassVar[str] = "go"
    file_extensions: ClassVar[tuple[str, ...]] = (".go",)

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
            func_name = match.group(1)
            func_start = match.start()

            body_end = _find_body_end(full_added_text, match.end())
            func_source = full_added_text[func_start:body_end]

            # Approximate end_line by counting newlines consumed.
            line_count = func_source.count("\n")
            # Offset from the top of the added block to this function.
            prefix_newlines = full_added_text[:func_start].count("\n")

            results.append(ChangedFunction(
                file_path=patched_file.path,
                function_name=func_name,
                source_code=func_source.strip(),
                start_line=start_line + prefix_newlines,
                end_line=start_line + prefix_newlines + line_count,
                language=self.language,
            ))

        return results

    def analyze_complexity(self, source_code: str, threshold: int) -> list[ComplexityResult]:
        # gocyclo needs a syntactically valid Go file with a package clause.
        if not re.match(r"^\s*package\s+\w+", source_code):
            source_code = "package main\n" + source_code

        with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as tmp:
            tmp.write(source_code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ["gocyclo", "-over", "1", tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

        results = []
        try:
            for raw in result.stdout.splitlines():
                m = _GOCYCLO_LINE.match(raw)
                if not m:
                    continue
                score = int(m.group(1))
                name = m.group(2)
                results.append(ComplexityResult(
                    function_name=name,
                    score=score,
                    rank=_rank_for(score),
                    is_flagged=score > threshold,
                ))
        except (ValueError, AttributeError):
            return []

        return results

    def run_security_scan(self, source_code: str) -> list[SecurityIssue]:
        if not re.match(r"^\s*package\s+\w+", source_code):
            source_code = "package main\n" + source_code

        with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as tmp:
            tmp.write(source_code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ["gosec", "-fmt", "json", "-quiet", tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = json.loads(result.stdout) if result.stdout else {"Issues": []}
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            # FileNotFoundError = gosec not installed; fail-open.
            return []

        issues = []
        for item in output.get("Issues", []):
            try:
                line_number = int(item.get("line", "0"))
            except ValueError:
                # gosec sometimes reports ranges like "42-45".
                line_number = 0
            issues.append(SecurityIssue(
                test_id=item.get("rule_id", ""),
                description=item.get("details", ""),
                severity=item.get("severity", "LOW"),
                confidence=item.get("confidence", "LOW"),
                line_number=line_number,
            ))
        return issues
