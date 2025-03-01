import asyncio
import sys
from inspect import Parameter as InspectParameter
from inspect import signature
from typing import (
    Any,
    Awaitable,
    Callable,
    ForwardRef,
    NewType,
    ParamSpec,
    Tuple,
    TypeVar,
    Union,
)


P = ParamSpec("P")
R = TypeVar("R", Awaitable, Any)

Undefined = NewType("Undefined", int)


def _resolve_forward_reference(module: Any, ref: Union[str, ForwardRef]) -> Any:
    if isinstance(ref, str):
        name = ref
    else:
        name = ref.__forward_arg__

    if name in sys.modules[module].__dict__:
        return sys.modules[module].__dict__[name]

    return None


class Parameter:
    type: Any
    name: str
    default: Any

    def __init__(self, name: str, type: Any = Any, default: Any = Undefined):
        self.name = name
        self.type = type
        self.default = default


def _inspect_function_arguments(
    function: Callable,
) -> Tuple[Tuple[str, ...], dict[str, Parameter]]:
    parameters_name: Tuple[str, ...] = tuple(signature(function).parameters.keys())
    parameters = {}

    for name, parameter in signature(function).parameters.items():
        if isinstance(parameter.annotation, (str, ForwardRef)) and hasattr(function, "__module__"):
            annotation = _resolve_forward_reference(function.__module__, parameter.annotation)
        else:
            annotation = parameter.annotation

        parameters[name] = Parameter(
            parameter.name,
            annotation,
            parameter.default if parameter.default is not InspectParameter.empty else Undefined,
        )

    return parameters_name, parameters


def _resolve_function_kwargs(
    parameters_name: Tuple[str, ...],
    parameters: dict[str, Parameter],
    container: dict,
) -> dict:
    resolved_kwargs = {}

    for name in parameters_name:
        if name in container:
            resolved_kwargs[name] = container[name]
            continue

        if parameters[name].type in container:
            resolved_kwargs[name] = container[parameters[name].type]
            continue

        if parameters[name].default is not Undefined:
            resolved_kwargs[name] = parameters[name].default

    return resolved_kwargs


def inject(injectable: Callable[P, R], container: dict) -> Callable[P, R]:
    parameters_name, parameters = _inspect_function_arguments(injectable)

    def _resolve_kwargs(args, kwargs) -> dict:
        # attach named arguments
        passed_kwargs = {**kwargs}

        # resolve positional arguments
        if args:
            for key, value in enumerate(args):
                passed_kwargs[parameters_name[key]] = value

        # prioritise passed kwargs and args resolving
        if len(passed_kwargs) == len(parameters_name):
            return passed_kwargs

        resolved_kwargs = _resolve_function_kwargs(parameters_name, parameters, container)
        all_kwargs = {**resolved_kwargs, **passed_kwargs}

        return all_kwargs

    def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # all arguments were passed
        if len(args) == len(parameters_name):
            return injectable(*args, **kwargs)

        if parameters_name == tuple(kwargs.keys()):
            return injectable(**kwargs)

        all_kwargs = _resolve_kwargs(args, kwargs)
        return injectable(**all_kwargs)

    async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # all arguments were passed
        if len(args) == len(parameters_name):
            return await injectable(*args)

        if parameters_name == tuple(kwargs.keys()):
            return await injectable(**kwargs)

        all_kwargs = _resolve_kwargs(args, kwargs)
        return await injectable(**all_kwargs)

    _wrapper.__wrapped__ = injectable
    _async_wrapper.__wrapped__ = injectable

    if asyncio.iscoroutinefunction(injectable):
        return _async_wrapper

    return _wrapper
