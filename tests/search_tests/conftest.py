import pytest


def pytest_assertrepr_compare(op, left, right):
    if op == "==":
        return [
            "Equality assertion failed:",
            f"    left:  {left!r}",
            f"    right: {right!r}",
        ]


pytest.register_assert_rewrite("src.search_testing.executors")
