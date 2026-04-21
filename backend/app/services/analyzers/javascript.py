"""
JavaScript / TypeScript analyzer.

Covers .js, .jsx, .ts, .tsx, .mjs, .cjs. Uses:
  - regex for function extraction from added diff lines, plus a
    brace-counter that is string- and comment-aware for body detection
  - eslint (subprocess) with the built-in `complexity` rule for CC
  - eslint-plugin-security (subprocess) for security scanning

Both eslint invocations fail-open (missing binary, timeout, or bad JSON
returns []) to match the Python/bandit behavior.
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


# Covers:
#   function foo(...)                       / async function foo(...)
#   const|let|var foo = (...) =>            / ... = async (...) =>
#   const|let|var foo = function(...)       / ... = async function(...)
#   class-method shape: `async? name(...) {` — loose; filtered by the
#     brace-counter stage (we only keep matches that have a real body).
# Anything after `)` and before `{` (TS return types, `: Promise<T>`,
# etc.) is tolerated by a non-greedy `.*?` before the optional `{`.
_FUNC_PATTERN = re.compile(
    r"""
    (?:^|\n)[ \t]*
    (?:
        (?:async\s+)?function\s*\*?\s*(?P<name1>\w+)\s*\([^)]*\)
      | (?:const|let|var)\s+(?P<name2>\w+)\s*=\s*
            (?:async\s+)?
            (?:
                \([^)]*\)\s*=>
              | \w+\s*=>
              | function\s*\*?\s*\w*\s*\([^)]*\)
            )
      | (?:async\s+)?(?P<name3>\w+)\s*\([^)]*\)\s*\{
    )
    """,
    re.VERBOSE,
)

# Reserved words that the class-method branch would otherwise swallow
# as function names. Keeps `if (x) {`, `while (x) {`, etc. out of the
# results.
_KEYWORDS = frozenset({
    "if", "for", "while", "switch", "catch", "return", "function",
    "do", "else", "try", "finally", "throw", "typeof", "new", "in",
    "of", "with", "yield", "await", "async", "const", "let", "var",
    "class", "extends", "import", "export", "default", "case", "break",
    "continue", "this", "super", "void", "delete", "instanceof",
})


def _find_body_end(src: str, open_brace_idx: int) -> int:
    """Return the index just past the matching `}` for the `{` at
    open_brace_idx, ignoring braces that appear inside string literals,
    template literals, or comments. Returns len(src) if unbalanced."""
    depth = 0
    i = open_brace_idx
    n = len(src)
    while i < n:
        c = src[i]
        # Line comment.
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            nl = src.find("\n", i)
            if nl == -1:
                return n
            i = nl + 1
            continue
        # Block comment.
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            end = src.find("*/", i + 2)
            if end == -1:
                return n
            i = end + 2
            continue
        # String / template literals.
        if c in ("'", '"', "`"):
            quote = c
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == quote:
                    i += 1
                    break
                i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


class JavaScriptAnalyzer:
    """Analyzer for JavaScript and TypeScript source."""

    language: ClassVar[str] = "javascript"
    file_extensions: ClassVar[tuple[str, ...]] = (
        ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    )

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
        seen_spans: list[tuple[int, int]] = []

        for match in _FUNC_PATTERN.finditer(full_added_text):
            func_name = match.group("name1") or match.group("name2") or match.group("name3")
            if not func_name or func_name in _KEYWORDS:
                continue

            match_start = match.start()
            # Skip if this match is nested inside a span we already captured
            # (e.g. an inner arrow function inside a function we already took).
            if any(s <= match_start < e for s, e in seen_spans):
                continue

            # Find the opening brace after the match, tolerating TS return
            # type annotations and whitespace.
            brace_idx = full_added_text.find("{", match.end() - 1)
            if brace_idx == -1:
                # Expression-bodied arrow: take to end of line / `;`.
                eol = full_added_text.find("\n", match.end())
                semi = full_added_text.find(";", match.end())
                candidates = [x for x in (eol, semi) if x != -1]
                func_end = min(candidates) if candidates else len(full_added_text)
                func_source = full_added_text[match_start:func_end]
                end_offset = func_end
            else:
                end_offset = _find_body_end(full_added_text, brace_idx)
                func_source = full_added_text[match_start:end_offset]

            seen_spans.append((match_start, end_offset))

            # Line numbers relative to full_added_text, offset by the first
            # added line in the diff.
            pre_start = full_added_text.count("\n", 0, match_start)
            pre_end = full_added_text.count("\n", 0, end_offset)

            results.append(ChangedFunction(
                file_path=patched_file.path,
                function_name=func_name,
                source_code=func_source.strip(),
                start_line=start_line + pre_start,
                end_line=start_line + pre_end,
                language=self.language,
            ))

        return results

    def analyze_complexity(self, source_code: str, threshold: int) -> list[ComplexityResult]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as tmp:
            tmp.write(source_code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [
                    "eslint",
                    "--format", "json",
                    "--no-eslintrc",
                    "--rule", json.dumps({"complexity": ["error", {"max": threshold}]}),
                    tmp_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # ESLint exits non-zero when lint rules fire — that's success
            # for us. We only care about parseable stdout.
            output = json.loads(result.stdout) if result.stdout else []
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return []

        score_re = re.compile(r"complexity of (\d+)")
        name_re = re.compile(r"Function '([^']+)'|Method '([^']+)'|Arrow function '([^']+)'")

        issues: list[ComplexityResult] = []
        for file_entry in output:
            for msg in file_entry.get("messages", []):
                if msg.get("ruleId") != "complexity":
                    continue
                text = msg.get("message", "")
                score_match = score_re.search(text)
                if not score_match:
                    continue
                score = int(score_match.group(1))
                name_match = name_re.search(text)
                if name_match:
                    func_name = next((g for g in name_match.groups() if g), "anonymous")
                else:
                    func_name = "anonymous"
                issues.append(ComplexityResult(
                    function_name=func_name,
                    score=score,
                    rank=_cc_rank(score),
                    is_flagged=score > threshold,
                ))
        return issues

    def run_security_scan(self, source_code: str) -> list[SecurityIssue]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as tmp:
            tmp.write(source_code)
            tmp_path = tmp.name

        rules = {
            "security/detect-eval-with-expression": "error",
            "security/detect-non-literal-regexp": "error",
            "security/detect-unsafe-regex": "error",
            "security/detect-pseudoRandomBytes": "error",
            "security/detect-new-buffer": "error",
            "security/detect-child-process": "error",
            "security/detect-object-injection": "warn",
        }

        try:
            result = subprocess.run(
                [
                    "eslint",
                    "--format", "json",
                    "--no-eslintrc",
                    "--plugin", "security",
                    "--rule", json.dumps(rules),
                    tmp_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = json.loads(result.stdout) if result.stdout else []
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return []

        issues: list[SecurityIssue] = []
        for file_entry in output:
            for msg in file_entry.get("messages", []):
                rule_id = msg.get("ruleId") or ""
                if not rule_id.startswith("security/"):
                    continue
                severity = "HIGH" if msg.get("severity") == 2 else "MEDIUM"
                issues.append(SecurityIssue(
                    test_id=rule_id,
                    description=msg.get("message", ""),
                    severity=severity,
                    confidence="MEDIUM",
                    line_number=msg.get("line", 0),
                ))
        return issues


def _cc_rank(score: int) -> str:
    if score <= 5:
        return "A"
    if score <= 10:
        return "B"
    if score <= 20:
        return "C"
    if score <= 30:
        return "D"
    return "F"
