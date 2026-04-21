import pytest
from app.services.diff_analyzer import extract_changed_functions

SAMPLE_DIFF = """diff --git a/utils.py b/utils.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/utils.py
@@ -0,0 +1,10 @@
+def calculate_total(items):
+    total = 0
+    for item in items:
+        if item.is_active:
+            if item.discount:
+                total += item.price * (1 - item.discount)
+            else:
+                total += item.price
+    return total
+
"""


def test_extracts_new_function():
    """Should extract newly added functions from diff."""
    functions = extract_changed_functions(SAMPLE_DIFF)
    assert len(functions) >= 1
    assert functions[0].function_name == "calculate_total"
    assert "calculate_total" in functions[0].source_code
    assert functions[0].file_path == "utils.py"


def test_ignores_non_python_files():
    """Should skip non-Python files."""
    diff = """diff --git a/README.md b/README.md
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/README.md
@@ -0,0 +1,3 @@
+# My Project
+This is a test.
+
"""
    functions = extract_changed_functions(diff)
    assert len(functions) == 0


def test_empty_diff():
    """Should handle empty diffs gracefully."""
    functions = extract_changed_functions("")
    assert functions == []


def test_multiple_functions_in_diff():
    """Should extract multiple functions from same file."""
    diff = """diff --git a/helpers.py b/helpers.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/helpers.py
@@ -0,0 +1,5 @@
+def func_a():
+    return 1
+
+def func_b():
+    return 2
"""
    functions = extract_changed_functions(diff)
    assert len(functions) >= 2
    names = [f.function_name for f in functions]
    assert "func_a" in names
    assert "func_b" in names
