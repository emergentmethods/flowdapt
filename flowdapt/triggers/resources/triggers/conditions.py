from functools import reduce
from typing import Any, Callable


operations: dict[str, Callable[..., Any]] = {
    # Equals
    "eq": lambda a, b: a == b,
    # Not equals
    "ne": lambda a, b: a != b,
    # Greater than
    "gt": lambda a, b: a > b,
    # Less than
    "lt": lambda a, b: a < b,
    # Greater or equal
    "ge": lambda a, b: a >= b,
    # Less or equal
    "le": lambda a, b: a <= b,
    # And
    "and": lambda *args: reduce(lambda a, b: a and b, args, True),
    # Or
    "or": lambda *args: reduce(lambda a, b: a and b, args, False),
    # Not
    "not": lambda a: not a,
    # Bool
    "bool": lambda a: bool(a),
}


def _get_value(data: dict, path: str, sentinel=None):
    # Split the path by .
    keys = path.split(".")
    value = data

    try:
        # Try each k in keys
        for k in keys:
            value = value[k]
    except (KeyError, TypeError, ValueError):
        # If it's not a valid key, the wrong type, etc
        # then return the sentinel
        return sentinel
    else:
        return value


def check_condition(conditions: dict | None, data: dict):
    """
    Check if a map of conditions is valid given the data.

    :param conditions: The dictionary of conditions
    :type conditions:
    :param data: The dictionary of data
    :type data: dictionary
    """
    if conditions is None or not isinstance(conditions, dict):
        return conditions

    data = data or {}
    root = list(conditions.keys())[0]
    values = conditions[root]

    # Syntax sugar for {"x": 1} => {"x": [1]}
    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]

    values = [check_condition(value, data) for value in values]

    # Allow references to values in `data` by using {"$": "my.path.to.value"}
    if root == "var":
        return _get_value(data, *values)

    return operations[root](*values)


if __name__ == "__main__":
    test_data = {"t": {"v": 5}}

    conditions = {"==": [{"$": "t.v"}, 5]}

    print(check_condition(conditions, test_data))
