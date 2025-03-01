from contextlib import AsyncExitStack
from typing import Any, Callable, ParamSpec, TypeVar

from flowdapt.lib.utils.asynctools import is_async_callable, is_async_context_manager
from flowdapt.lib.utils.di import inject


P = ParamSpec("P")
R = TypeVar("R")


class ApplicationContext:
    """
    Object for holding stateful objects and data,
    while allowing to automatically enter async
    contexts held in the state
    """

    _state: dict[Any, Any]
    _stack: AsyncExitStack

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        state = {} if state is None else state
        super().__setattr__("_state", state)

    @property
    def state(self):
        return self._state

    def __getitem__(self, key: Any):
        try:
            return self._state[key]
        except KeyError:
            return None

    def __setitem__(self, key: Any, value: Any) -> None:
        self._state[key] = value

    def __delitem__(self, key: Any):
        del self._state[key]

    def __setattr__(self, key: Any, value: Any) -> None:
        self[key] = value

    def __getattr__(self, key: Any) -> Any:
        return self[key]

    def __delattr__(self, key: Any):
        del self[key]

    def __repr__(self):
        return f"ApplicationContext{self._state}"

    async def __aenter__(self):
        async with AsyncExitStack() as stack:
            for state, val in self._state.items():
                if is_async_context_manager(val):
                    self._state[state] = await stack.enter_async_context(val)

            self._stack = stack.pop_all()

            return self

    async def __aexit__(self, *args):
        return await self._stack.__aexit__(*args)


_context = ApplicationContext()


def get_context() -> ApplicationContext:
    """
    Get the ApplicationContext if it exists.
    """
    global _context
    return _context


def create_context(state: dict[Any, Any]):
    global _context

    for k, v in state.items():
        _context[k] = v

    return _context


def inject_context(func: Callable[P, R], container: dict = {}) -> Callable[P, Any]:
    """
    Inject the ApplicationContext into the function
    """

    # We use a decorator to ensure the func is injected at
    # runtime instead of when imported
    def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        nonlocal container
        # Grab state when called and append the passed container
        container = {**get_context().state, **container}
        # Inject the full container and call the injected func
        return inject(func, container)(*args, **kwargs)

    async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        nonlocal container
        # Grab state when called and append the passed container
        container = {**get_context().state, **container}
        # Inject the full container and call the injected func
        return await inject(func, container)(*args, **kwargs)

    if is_async_callable(func):
        return _async_wrapper

    return _wrapper
