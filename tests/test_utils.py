import pytest
from cpr_sdk.utils import (
    dig,
    iterate_batch,
    remove_key_if_all_nested_vals_none,
    unflatten_json,
)


@pytest.mark.parametrize(
    "fields, default, expected",
    [
        (["field"], None, "parent"),
        (["children", 0, "name"], None, "child_one"),
        (["children", 1, "items", 2], None, "two"),
        (["children", 2, "sub", "sub_sub", "sub_sub_sub", 2], None, "c"),
        (["children", 5], "default_1", "default_1"),
        (["children", 2, "sub", "sub_sub", "NO"], "default_2", "default_2"),
    ],
)
def test_dig(fields, default, expected):
    obj = {
        "field": "parent",
        "children": [
            {"name": "child_one"},
            {"name": "child_two", "items": ["zero", "one", "two"]},
            {
                "name": "child_three",
                "sub": {"sub_sub": {"sub_sub_sub": ["a", "b", "c"]}},
            },
        ],
    }

    assert dig(obj, *fields, default=default) == expected


def test_unflatten_json() -> None:
    """Test unflatten_json function."""
    data = {
        "a.b.c": 1,
        "a.b.d": 2,
        "a.e": 3,
        "f": 4,
    }

    expected = {
        "a": {
            "b": {"c": 1, "d": 2},
            "e": 3,
        },
        "f": 4,
    }

    assert unflatten_json(data) == expected


def test_remove_key_if_all_nested_vals_none() -> None:
    """Test remove_key_if_all_nested_vals_none function."""
    assert remove_key_if_all_nested_vals_none({}, "key") == {}
    assert remove_key_if_all_nested_vals_none({"key": None}, "key") == {"key": None}
    assert remove_key_if_all_nested_vals_none({"key": {"nested": None}}, "key") == {}
    assert remove_key_if_all_nested_vals_none({"key": {"nested": None}}, "no_key") == {
        "key": {"nested": None}
    }
    assert remove_key_if_all_nested_vals_none(
        {
            "key": {"nested": None},
            "key2": {"nested": "value"},
        },
        "key",
    ) == {"key2": {"nested": "value"}}


@pytest.mark.parametrize(
    "data, expected_lengths",
    [
        # Lists
        (list(range(50)), [50]),
        (list(range(850)), [400, 400, 50]),
        ([], [0]),
        # Generators
        ((x for x in range(50)), [50]),
        ((x for x in range(850)), [400, 400, 50]),
        ((x for x in []), [0]),
    ],
)
def test_iterate_batch(data, expected_lengths):
    batch_size = 400
    for batch, expected in zip(list(iterate_batch(data, batch_size)), expected_lengths):
        assert len(batch) == expected
