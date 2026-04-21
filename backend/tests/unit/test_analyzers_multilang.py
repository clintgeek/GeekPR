"""
Multi-language analyzer tests.

Exercises the four registered analyzers (python, javascript, rust, go)
across three surfaces:
  1. Registry dispatch — file extension + language name lookups.
  2. Function extraction from unified diffs (pure regex — no external
     tools required).
  3. Complexity + security fail-open behavior — when the external tool
     is absent in the test environment, analyzers must return [] rather
     than raising.

Python function extraction is already covered by test_diff_analyzer.py,
so this file focuses on the new languages and cross-cutting behavior.
"""

from __future__ import annotations

import pytest

from app.services.analyzers import (
    get_analyzer_by_language,
    get_analyzer_for_file,
    supported_languages,
)
from app.services.diff_analyzer import extract_changed_functions


# ──────────────────────────────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_all_four_languages_registered(self):
        langs = supported_languages()
        assert set(langs) >= {"python", "javascript", "rust", "go"}

    @pytest.mark.parametrize(
        "path,expected_language",
        [
            ("src/module.py", "python"),
            ("app/main.js", "javascript"),
            ("components/Button.jsx", "javascript"),
            ("types/api.ts", "javascript"),
            ("components/Button.tsx", "javascript"),
            ("lib/helpers.mjs", "javascript"),
            ("scripts/tool.cjs", "javascript"),
            ("src/main.rs", "rust"),
            ("cmd/server/main.go", "go"),
        ],
    )
    def test_extension_dispatch(self, path, expected_language):
        analyzer = get_analyzer_for_file(path)
        assert analyzer is not None
        assert analyzer.language == expected_language

    def test_unknown_extension_returns_none(self):
        assert get_analyzer_for_file("README.md") is None
        assert get_analyzer_for_file("config.yaml") is None

    def test_language_lookup(self):
        assert get_analyzer_by_language("python") is not None
        assert get_analyzer_by_language("javascript") is not None
        assert get_analyzer_by_language("rust") is not None
        assert get_analyzer_by_language("go") is not None
        assert get_analyzer_by_language("haskell") is None


# ──────────────────────────────────────────────────────────────────────
# Function extraction — JavaScript / TypeScript
# ──────────────────────────────────────────────────────────────────────

JS_DIFF_FUNCTION_DECL = """diff --git a/app.js b/app.js
new file mode 100644
--- /dev/null
+++ b/app.js
@@ -0,0 +1,9 @@
+function computeTotal(items) {
+  let total = 0;
+  for (const item of items) {
+    if (item.active) {
+      total += item.price;
+    }
+  }
+  return total;
+}
"""

JS_DIFF_ARROW = """diff --git a/util.js b/util.js
new file mode 100644
--- /dev/null
+++ b/util.js
@@ -0,0 +1,6 @@
+const isEven = (n) => {
+  if (n % 2 === 0) {
+    return true;
+  }
+  return false;
+};
"""

TS_DIFF_WITH_TYPES = """diff --git a/service.ts b/service.ts
new file mode 100644
--- /dev/null
+++ b/service.ts
@@ -0,0 +1,4 @@
+async function fetchUser(id: number): Promise<User> {
+  const response = await api.get(`/users/${id}`);
+  return response.data;
+}
"""


class TestJavaScriptExtraction:
    def test_function_declaration(self):
        funcs = extract_changed_functions(JS_DIFF_FUNCTION_DECL)
        names = [f.function_name for f in funcs]
        assert "computeTotal" in names
        assert all(f.language == "javascript" for f in funcs)

    def test_arrow_function_assignment(self):
        funcs = extract_changed_functions(JS_DIFF_ARROW)
        names = [f.function_name for f in funcs]
        assert "isEven" in names

    def test_typescript_with_annotations(self):
        funcs = extract_changed_functions(TS_DIFF_WITH_TYPES)
        names = [f.function_name for f in funcs]
        assert "fetchUser" in names
        # TypeScript dispatches through the JS analyzer
        assert funcs[0].language == "javascript"


# ──────────────────────────────────────────────────────────────────────
# Function extraction — Rust
# ──────────────────────────────────────────────────────────────────────

RUST_DIFF_BASIC = """diff --git a/src/lib.rs b/src/lib.rs
new file mode 100644
--- /dev/null
+++ b/src/lib.rs
@@ -0,0 +1,6 @@
+pub fn add(a: i32, b: i32) -> i32 {
+    if a > 0 {
+        return a + b;
+    }
+    a - b
+}
"""

RUST_DIFF_ASYNC_GENERIC = """diff --git a/src/main.rs b/src/main.rs
new file mode 100644
--- /dev/null
+++ b/src/main.rs
@@ -0,0 +1,4 @@
+pub async fn fetch<T: DeserializeOwned>(url: &str) -> Result<T, Error> {
+    let resp = reqwest::get(url).await?;
+    resp.json().await
+}
"""


class TestRustExtraction:
    def test_basic_fn(self):
        funcs = extract_changed_functions(RUST_DIFF_BASIC)
        names = [f.function_name for f in funcs]
        assert "add" in names
        assert all(f.language == "rust" for f in funcs)

    def test_async_generic_fn(self):
        funcs = extract_changed_functions(RUST_DIFF_ASYNC_GENERIC)
        names = [f.function_name for f in funcs]
        assert "fetch" in names


# ──────────────────────────────────────────────────────────────────────
# Function extraction — Go
# ──────────────────────────────────────────────────────────────────────

GO_DIFF_TOPLEVEL = """diff --git a/main.go b/main.go
new file mode 100644
--- /dev/null
+++ b/main.go
@@ -0,0 +1,6 @@
+func processRequest(r *Request) (*Response, error) {
+    if r == nil {
+        return nil, errors.New("nil request")
+    }
+    return &Response{OK: true}, nil
+}
"""

GO_DIFF_METHOD = """diff --git a/server.go b/server.go
new file mode 100644
--- /dev/null
+++ b/server.go
@@ -0,0 +1,4 @@
+func (s *Server) Handle(req *Request) error {
+    s.count++
+    return nil
+}
"""


class TestGoExtraction:
    def test_top_level_func(self):
        funcs = extract_changed_functions(GO_DIFF_TOPLEVEL)
        names = [f.function_name for f in funcs]
        assert "processRequest" in names
        assert all(f.language == "go" for f in funcs)

    def test_method_with_receiver(self):
        funcs = extract_changed_functions(GO_DIFF_METHOD)
        names = [f.function_name for f in funcs]
        assert "Handle" in names


# ──────────────────────────────────────────────────────────────────────
# Fail-open behavior when external tools are missing
# ──────────────────────────────────────────────────────────────────────

class TestFailOpen:
    """All non-Python analyzers shell out to external tools (eslint,
    cargo clippy, gocyclo, gosec). Those are not required to be installed
    to run the test suite — the analyzers must return [] instead of
    raising when a tool is missing.
    """

    @pytest.mark.parametrize("language,sample", [
        ("javascript", "function x() { return 1; }"),
        ("rust", "pub fn x() -> i32 { 1 }"),
        ("go", "package main\nfunc x() int { return 1 }"),
    ])
    def test_complexity_fail_open(self, language, sample):
        analyzer = get_analyzer_by_language(language)
        # Result is [] when the tool is missing or the sample has no
        # flaggable functions; both are acceptable "didn't raise" cases.
        result = analyzer.analyze_complexity(sample, threshold=10)
        assert isinstance(result, list)

    @pytest.mark.parametrize("language,sample", [
        ("javascript", "function x() { return eval('1+1'); }"),
        ("rust", "pub fn x() -> i32 { 1 }"),
        ("go", "package main\nfunc x() int { return 1 }"),
    ])
    def test_security_scan_fail_open(self, language, sample):
        analyzer = get_analyzer_by_language(language)
        result = analyzer.run_security_scan(sample)
        assert isinstance(result, list)


# ──────────────────────────────────────────────────────────────────────
# Unknown-file-extension short-circuit — regression guard on
# diff_analyzer's dispatch logic.
# ──────────────────────────────────────────────────────────────────────

class TestUnknownExtensionSkip:
    def test_markdown_diff_returns_empty(self):
        diff = (
            "diff --git a/README.md b/README.md\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/README.md\n"
            "@@ -0,0 +1,1 @@\n"
            "+# Hi\n"
        )
        assert extract_changed_functions(diff) == []

    def test_mixed_diff_only_returns_known(self):
        """A single diff containing both a .md change and a .py function
        should only yield the .py function."""
        diff = (
            "diff --git a/README.md b/README.md\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/README.md\n"
            "@@ -0,0 +1,1 @@\n"
            "+# Hi\n"
            "diff --git a/util.py b/util.py\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/util.py\n"
            "@@ -0,0 +1,2 @@\n"
            "+def f():\n"
            "+    return 1\n"
        )
        funcs = extract_changed_functions(diff)
        assert len(funcs) == 1
        assert funcs[0].function_name == "f"
        assert funcs[0].language == "python"
