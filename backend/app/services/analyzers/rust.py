"""
Rust analyzer.

Mirrors python.py's approach: regex-based function extraction from diffs,
subprocess to an external tool (cargo clippy) for security scanning, and
fail-open behavior when tools are missing or input doesn't compile.

Note: Rust has no standard cyclomatic-complexity tool comparable to radon,
so analyze_complexity uses a heuristic — it counts branch-introducing
tokens (if/else if/while/for/loop/&&/||) plus match arms in each function
body. The resulting score is approximate and should be treated as a
rough signal, not a precise CC number.
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import ClassVar

from app.services.analyzers.base import (
    ChangedFunction,
    ComplexityResult,
    SecurityIssue,
)


# Matches `fn name` with optional visibility/async/const/unsafe modifiers
# and optional generic parameters before the argument list.
_FUNC_PATTERN = re.compile(
    r"^([ \t]*)(?:pub(?:\([^)]*\))?\s+)?(?:(?:async|const|unsafe)\s+)*"
    r"fn\s+(\w+)\s*(?:<[^>]*>)?\s*\(",
    re.MULTILINE,
)


def _find_body_bounds(source: str, sig_start: int) -> tuple[int, int] | None:
    """Given an offset where a fn signature starts, return (body_start,
    body_end) offsets spanning from the opening `{` of the function body
    to the matching closing `}`. Returns None for forward declarations
    (no body) or unmatched braces."""
    i = sig_start
    n = len(source)
    # Walk past the signature to the first `{` at depth 0, skipping
    # strings, char literals, and comments. If we hit `;` first, this
    # is a forward declaration.
    while i < n:
        c = source[i]
        if c == ";":
            return None
        if c == "{":
            break
        if c == "/" and i + 1 < n and source[i + 1] == "/":
            nl = source.find("\n", i)
            i = n if nl == -1 else nl + 1
            continue
        if c == "/" and i + 1 < n and source[i + 1] == "*":
            end = source.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        if c == '"':
            i += 1
            while i < n:
                if source[i] == "\\":
                    i += 2
                    continue
                if source[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        i += 1
    if i >= n or source[i] != "{":
        return None

    body_start = i
    depth = 0
    while i < n:
        c = source[i]
        if c == "/" and i + 1 < n and source[i + 1] == "/":
            nl = source.find("\n", i)
            i = n if nl == -1 else nl + 1
            continue
        if c == "/" and i + 1 < n and source[i + 1] == "*":
            end = source.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        if c == '"':
            i += 1
            while i < n:
                if source[i] == "\\":
                    i += 2
                    continue
                if source[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return body_start, i + 1
        i += 1
    return None


def _strip_strings_and_comments(code: str) -> str:
    """Return code with string literals and comments blanked out, so
    keyword counting doesn't pick up tokens inside them."""
    out = []
    i = 0
    n = len(code)
    while i < n:
        c = code[i]
        if c == "/" and i + 1 < n and code[i + 1] == "/":
            nl = code.find("\n", i)
            if nl == -1:
                break
            out.append("\n")
            i = nl + 1
            continue
        if c == "/" and i + 1 < n and code[i + 1] == "*":
            end = code.find("*/", i + 2)
            i = n if end == -1 else end + 2
            out.append(" ")
            continue
        if c == '"':
            i += 1
            while i < n:
                if code[i] == "\\":
                    i += 2
                    continue
                if code[i] == '"':
                    i += 1
                    break
                i += 1
            out.append('""')
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _cc_score(body: str) -> int:
    """Heuristic cyclomatic complexity: 1 + branch tokens + match arms."""
    cleaned = _strip_strings_and_comments(body)
    score = 1
    score += len(re.findall(r"\belse\s+if\b", cleaned))
    # `if` includes `else if`'s own `if`, so subtract the else-if count
    # to avoid double-counting.
    ifs = len(re.findall(r"\bif\b", cleaned))
    else_ifs = len(re.findall(r"\belse\s+if\b", cleaned))
    score += ifs - else_ifs
    score += len(re.findall(r"\bwhile\b", cleaned))
    score += len(re.findall(r"\bfor\b", cleaned))
    score += len(re.findall(r"\bloop\b", cleaned))
    score += cleaned.count("&&")
    score += cleaned.count("||")
    # Count match arms: every `=>` inside a `match { ... }` block.
    for m in re.finditer(r"\bmatch\b", cleaned):
        bounds = _find_body_bounds(cleaned, m.end())
        if bounds is None:
            continue
        bs, be = bounds
        arm_region = cleaned[bs:be]
        score += arm_region.count("=>")
    return score


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


class RustAnalyzer:
    language: ClassVar[str] = "rust"
    file_extensions: ClassVar[tuple[str, ...]] = (".rs",)

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
            func_name = match.group(2)
            func_start = match.start()

            bounds = _find_body_bounds(full_added_text, match.end())
            if bounds is None:
                continue
            _, body_end = bounds

            func_source = full_added_text[func_start:body_end]
            line_count = func_source.count("\n")

            results.append(ChangedFunction(
                file_path=patched_file.path,
                function_name=func_name,
                source_code=func_source.strip(),
                start_line=start_line,
                end_line=start_line + line_count,
                language=self.language,
            ))

        return results

    def analyze_complexity(self, source_code: str, threshold: int) -> list[ComplexityResult]:
        try:
            results = []
            for match in _FUNC_PATTERN.finditer(source_code):
                func_name = match.group(2)
                bounds = _find_body_bounds(source_code, match.end())
                if bounds is None:
                    continue
                body_start, body_end = bounds
                body = source_code[body_start:body_end]
                score = _cc_score(body)
                results.append(ComplexityResult(
                    function_name=func_name,
                    score=score,
                    rank=_rank_for(score),
                    is_flagged=score > threshold,
                ))
            return results
        except Exception:
            return []

    def run_security_scan(self, source_code: str) -> list[SecurityIssue]:
        # Clippy needs a real cargo project — a Cargo.toml plus a source
        # file it can compile as a library.
        tmpdir = tempfile.mkdtemp(prefix="geekpr_rust_")
        try:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "Cargo.toml").write_text(
                "[package]\n"
                'name = "geekpr_scan"\n'
                'version = "0.0.1"\n'
                'edition = "2021"\n'
                "[lib]\n"
                'path = "src/lib.rs"\n'
            )
            (root / "src" / "lib.rs").write_text(source_code)

            try:
                result = subprocess.run(
                    [
                        "cargo", "clippy",
                        "--manifest-path", str(root / "Cargo.toml"),
                        "--message-format=json",
                        "--",
                        "-W", "clippy::all",
                        "-W", "clippy::suspicious",
                        "-W", "clippy::pedantic",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return []

            issues = []
            for raw_line in (result.stdout or "").splitlines():
                if not raw_line.strip():
                    continue
                try:
                    msg = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if msg.get("reason") != "compiler-message":
                    continue
                body = msg.get("message") or {}
                code = (body.get("code") or {}).get("code") or ""
                if not code.startswith("clippy::"):
                    continue
                level = body.get("level", "")
                spans = body.get("spans") or []
                line_number = spans[0].get("line_start", 0) if spans else 0
                issues.append(SecurityIssue(
                    test_id=code,
                    description=body.get("message", ""),
                    severity="HIGH" if level == "error" else "MEDIUM",
                    confidence="MEDIUM",
                    line_number=line_number,
                ))
            return issues
        except Exception:
            return []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
