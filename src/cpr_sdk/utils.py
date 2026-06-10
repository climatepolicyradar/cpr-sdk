from typing import Any, Generator, Union, TypeVar

T = TypeVar("T")


def dig(obj: Union[list, dict], *fields: Any, default: Any = None) -> Any:
    """
    An interface for retrieving data from complicated objects

    Behaviour is to return the default if the path is invalid thereby avoiding errors
    Example: `dig(nested_dict, "parent", "child", "child_items", 1)`
    """
    for field in fields:
        if isinstance(obj, list):
            if isinstance(field, int) and len(obj) > field:
                obj = obj[field]
            else:
                return default
        elif isinstance(obj, dict):
            obj = obj.get(field, default)
        elif not obj:
            return default
    return obj


def unflatten_json(data: dict) -> dict:
    """
    Unflatten a dictionary with keys that are dot-separated strings.

    I.e. metadata.data respresents {"metadata": {"data": {}}}
    """
    unflattened = {}
    for key, value in data.items():
        parts = key.split(".")
        current = unflattened
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
    return unflattened


def remove_key_if_all_nested_vals_none(data: dict, key: str) -> dict:
    """
    Remove the value for a given key if it's a dict with all None values.

    E.g. {"key": {"a": None, "b": None}} -> {}
    """
    if key not in data:
        return data
    if isinstance(data[key], dict):
        if all(value is None for value in data[key].values()):
            data.pop(key)
    return data


def iterate_batch(
    data: list[T] | Generator[T, None, None],
    batch_size: int,
) -> Generator[list[T], None, None]:
    """Generate batches from a list or generator with a specified size."""
    if isinstance(data, list):
        for i in range(0, len(data), batch_size):
            yield data[i : i + batch_size]
    else:
        batch: list[T] = []
        for item in data:
            batch.append(item)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
