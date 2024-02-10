from typing import Callable


_HANDLER_MAP: dict[tuple[str, str, str], Callable] = {
    # The first element of the tuple is the executor name. '*' means the handler is
    # executor-agnostic
    # The second element of the tuple is the value type's name
    # The third element of the tuple is the operation
    # ("*", "pandas.core.frame.DataFrame", "to_artifact"): pandas_dataframe_to_artifact,
    # ("*", "pandas.core.frame.DataFrame", "from_artifact"): pandas_dataframe_from_artifact,
    # Handlers are explicitly registered elsewhere
}


def get_handler_func(
    executor: str,
    data_type: str,
    operation: str
) -> Callable:
    """
    Get the handler function for a given executor, data type, and operation.

    :param executor: The executor to get the handler for.
    :param data_type: The data type to get the handler for.
    :param operation: The operation to get the handler for.
    :return: The handler function.
    """
    # Attempt to get the executor-specific handler
    handler = _HANDLER_MAP.get((executor, data_type, operation))

    # Fall back to the generic handler if an executor-specific handler doesn't exist
    if not handler:
        handler = _HANDLER_MAP.get(('*', data_type, operation))

    if not handler:
        raise ValueError(
            f"No handler found for executor '{executor}', data type '{data_type}', "
            f"and operation '{operation}'"
        )

    return handler


def register_handler(
    executor: str,
    data_type: str,
    operation: str,
    handler: Callable
):
    """
    Register a handler function for a given executor, data type, and operation.

    :param executor: The executor to register the handler for.
    :param data_type: The data type to register the handler for.
    :param operation: The operation to register the handler for.
    :param handler: The handler function to register.
    :return: None
    """
    global _HANDLER_MAP
    _HANDLER_MAP[(executor, data_type, operation)] = handler
