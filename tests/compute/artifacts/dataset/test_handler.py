import pytest

from flowdapt.compute.artifacts.dataset.handler import get_handler_func, register_handler


def test_get_registered_handler():
    # Define a dummy handler function for testing
    def handler_func():
        return "Handled"

    # Register the handler for a specific executor, data type, and operation
    register_handler("executor1", "type1", "operation1", handler_func)

    # Attempt to get the handler we just registered
    handler = get_handler_func("executor1", "type1", "operation1")

    # The function should return the handler we registered
    assert handler == handler_func

def test_get_unregistered_handler():
    # If we try to get a handler for an executor, data type, and operation
    # that we haven't registered a handler for, it should raise a ValueError
    with pytest.raises(ValueError):
        get_handler_func("executor2", "type1", "operation1")

def test_get_generic_handler():
    # Define a dummy handler function for testing
    def handler_func():
        return "Handled"

    # Register a generic handler for a specific data type and operation,
    # indicated by using "*" as the executor
    register_handler("*", "type1", "operation1", handler_func)

    # Attempt to get the handler for a different executor, same data type, and operation
    handler = get_handler_func("executor2", "type1", "operation1")

    # The function should return the generic handler we registered,
    # since there's no executor-specific handler
    assert handler == handler_func

def test_get_no_handler():
    # If we try to get a handler for a combination of executor, data type,
    # and operation for which we haven't registered a handler and also
    # no generic handler exists, it should raise a ValueError
    with pytest.raises(ValueError):
        get_handler_func("executor2", "type2", "operation1")