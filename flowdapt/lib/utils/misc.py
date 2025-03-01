import asyncio
import inspect
import os
import site
import sys
import uuid
from collections.abc import Sequence
from contextlib import contextmanager
from datetime import datetime
from functools import cache, wraps
from hashlib import blake2b, sha256
from inspect import (
    Parameter,
    Signature,
    _ParameterKind,
)
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Generic, Iterable, Iterator, Mapping, Tuple, Type, TypeVar, cast
from urllib.parse import urlparse
from uuid import uuid4

import coolname
import typer
from crontab import CronTab
from pydantic import BaseConfig, ValidationError, create_model


_import_cache: dict = {}

F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")

UNDEFINED = object()


def timer(iterations: int = 10, precision: int = 6, prefix: str | None = None) -> Callable[[F], F]:
    """
    Use as a decorator to time the execution of any function or coroutine.

    Examples:
        >>> @timer()
        ... async def foo(x):
        ...     return x
        >>> await foo(123)
        foo: 0.000...s

        >>> @timer(10, 2)
        ... async def foo(x):
        ...     return x
        >>> await foo(123)
        Time taken: 0.00s

    :param prefix: The prefix to print before the time taken.
    :type prefix: str
    :param precision: The number of decimal places to print.
    :type precision: int
    """

    def decorator(func: F) -> F:
        is_coroutine = asyncio.iscoroutinefunction(func)
        prefix_str = prefix if prefix is not None else f"{func.__name__}: "

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            total_time = 0.0
            for _ in range(iterations):
                start = perf_counter()
                result = await func(*args, **kwargs) if is_coroutine else func(*args, **kwargs)
                end = perf_counter()
                total_time += end - start

            average_time = total_time / iterations
            print(f"{prefix_str} avg time for {iterations} runs: {average_time:.{precision}f}s")
            return result

        return cast(F, wrapper)

    return decorator


def import_from_string(path: str, is_module: bool = False, use_cache: bool = False) -> Any:
    from importlib import import_module, reload

    if use_cache and path in _import_cache:
        return _import_cache[path]

    if is_module:
        module_path = path
    else:
        try:
            module_path, class_name = path.strip(" ").rsplit(".", 1)
        except ValueError:
            raise ImportError(f"{path} isn't a valid module path.")

    # Import the module and reload
    module = import_module(module_path)
    module = reload(module)

    if is_module:
        if use_cache:
            _import_cache[path] = module
        return module

    try:
        klass = getattr(module, class_name)

        if use_cache:
            _import_cache[path] = klass

        return klass
    except AttributeError:
        raise ImportError(f"Module {module} does not have a `{class_name}` attribute")  # noqa:E501


def import_from_script(path: Path) -> Any:
    from importlib.util import module_from_spec, spec_from_file_location

    module_name = path.stem
    spec = spec_from_file_location(module_name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


@cache
def get_env_var(names: str | list[str], default: Any = None) -> Any:
    """
    Get an environment variable.

    :param names: The names of the environment variable.
    :type names: str | list[str]
    :param default: The default value to return if the environment variable is not set.
    :type default: Any
    :return: The value of the environment variable if it is set, otherwise the default value.
    :rtype: Any
    """
    if isinstance(names, str):
        names = [names]

    for name in names:
        if val := os.environ.get(name):
            return val

    return default


def hash_file(file_path: str | None, hash_func=blake2b) -> str | None:
    if not file_path:
        return None

    _file = Path(file_path)

    if not _file.exists():
        raise FileNotFoundError(f"{file_path} does not exist.")

    with _file.open("rb") as f:
        file_hash = hash_func()
        while chunk := f.read(8192):  # Only read 2**13 bytes at a time
            file_hash.update(chunk)

    return file_hash.hexdigest()


def compute_hash(*args, hash_func: Callable = sha256) -> str:
    """
    Compute a hash for the given arguments.

    :param args: Items to be hashed. Can be str, bytes, int, float, and Path.
    :param hash_func: The hash function to use, default is sha256.
    :return: A hexadecimal hash string.
    """
    hasher = hash_func()

    for item in args:
        if isinstance(item, Path):
            hasher.update(item.read_bytes())
        elif isinstance(item, (str, bytes, int, float)):
            hasher.update(str(item).encode("utf-8"))
        else:
            raise TypeError(f"Unsupported type {type(item)} for hashing")

    return hasher.hexdigest()


def generate_uuid():
    return uuid4()


def is_valid_uuid(uuid_string):
    """
    Check if a given string is a valid UUID.

    :param uuid_string: The string to check.
    :type uuid_string: str
    :return: A boolean indicating if the string is a valid UUID.
    :rtype: bool
    """
    try:
        uuid_obj = uuid.UUID(uuid_string)
    except ValueError:
        return False

    return str(uuid_obj) == uuid_string


def generate_name(size: int = 2):
    BAD_LIST = {
        "sexy",
        "demonic",
        "kickass",
        "heretic",
        "godlike",
        "booby",
        "chubby",
        "gay",
        "sloppy",
        "funky",
        "juicy",
        "beaver",
        "curvy",
        "fat",
        "flashy",
        "flat",
        "thick",
        "nippy",
    }
    words = coolname.generate(size)

    while BAD_LIST.intersection(words):
        words = coolname.generate(size)

    return "-".join(words)


def dict_to_list_string(d: dict) -> Tuple[list, str]:
    """
    Given a dictionary of metdata, create a
    list and string to be used for file naming purposes.
    :param d: dictionary of metadata
    :return:
    d_list = list of dict values
    d_str = string of dict values joined by "_"
    """
    d_list = [str(d[key]) for key in d.keys() if d[key]]
    d_str = "_".join(d_list)
    return d_list, d_str


def has_parameter_of_type(func, name, param_type):
    """
    Returns True if `func` has a parameter of type `param_type`.
    """
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if (
            param.name == name
            and isinstance(param.annotation, type)
            and issubclass(param.annotation, param_type)
        ):
            return True
    return False


def get_time_to_next(schedule: str, since: datetime = datetime.now()):
    return CronTab(schedule).next(since, default_utc=True)


@contextmanager
def current_directory(directory: Path):
    """
    Context manager that changes the current working directory to the specified `directory`.
    Upon completion, the current working directory is restored to its original value.

    :param directory: A `Path` object representing the directory to change to.
    :type directory: Path

    :raises ValueError: If the specified path does not exist or is not a directory.

    :yields: None
    """
    import os

    # Check if the specified path exists and is a directory.
    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"`{directory}` must be a directory")

    # Save the current working directory before changing it.
    old = os.getcwd()

    try:
        # Change the current working directory to the specified directory.
        os.chdir(directory)
        # Yield control back
        yield
    finally:
        # Restore the original working directory.
        os.chdir(old)


def get_default_app_dir(name: str = "flowdapt") -> Path:
    """
    Get the default application directory.

    :param name: The name of the application.
    :type name: str
    :returns: The application directory.
    :rtype: Path
    """
    app_dir = Path(typer.get_app_dir(name, force_posix=True))
    return app_dir


def flatten_list(lst: list) -> list:
    if not any(isinstance(item, Sequence) and not isinstance(item, (str, bytes)) for item in lst):
        return lst

    return [
        item
        for sublist in lst
        for item in (sublist if isinstance(sublist, Sequence) else [sublist])
    ]


def check_type(t: Type, value: Any) -> Any:
    """
    Validate a value against a type.

    :param t: The type to validate against.
    :type t: Type
    :param value: The value to validate.
    :type value: Any
    :return: The coerced value if it's valid, otherwise False.
    """

    class ValueModelConfig(BaseConfig):
        smart_union = True

    ValueModel = create_model("ValueModel", __config__=ValueModelConfig, value=(t, ...))

    try:
        return ValueModel(value=value).value  # type: ignore[attr-defined]
    except ValidationError:
        return False


def combine_args_kwargs(
    signature: Signature, args: list[Any], kwargs: dict[str, Any]
) -> dict[str, Any]:
    """
    Combine input positional and keyword arguments into a single dictionary.

    :param signature: The signature of the function to combine the arguments for.
    :param args: List of input positional arguments.
    :param kwargs: Dictionary of input keyword arguments.
    :return: A dictionary containing the combined positional and keyword arguments.
    """
    combined = dict(zip(signature.parameters.keys(), args, strict=False))
    combined.update(kwargs)
    return combined


def filter_args(
    signature: Signature,
    args: list[Any],
    kwargs: dict[str, Any],
    coerce: bool = True,
) -> tuple[list, dict]:
    """
    Filter and coerce input arguments based on the stage signature.

    :param args: List of input positional arguments.
    :param kwargs: Dictionary of input keyword arguments.
    :param coerce: Whether to coerce the input arguments to their
    specified types (if they are basic types).
    :return: A dictionary containing the filtered and coerced positional and keyword arguments.
    """
    # Get the list of parameter names that are not *args or **kwargs
    positional_input_keys = [
        k
        for k, v in signature.parameters.items()
        if v.kind not in {Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD}
    ]

    # Filter the input arguments based on the parameter names
    filtered_args = [arg for i, arg in enumerate(args) if i < len(positional_input_keys)]

    # Get any extra positional arguments that are not in the stage signature
    extra_args = args[len(positional_input_keys) :] if "args" in signature.parameters else []

    # Filter the input keyword arguments based on the parameter names
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in signature.parameters}

    # Get any extra keyword arguments that are not in the stage signature
    extra_kwargs = {
        k: v
        for k, v in kwargs.items()
        if k not in signature.parameters and "kwargs" in signature.parameters
    }

    if coerce:
        # Coerce the filtered positional arguments to their specified types
        coerced_args = [
            (signature.parameters[positional_input_keys[i]].annotation)(arg)
            if isinstance(arg, (int, float, str, bool))
            else arg
            for i, arg in enumerate(filtered_args)
        ]

        # Coerce the filtered keyword arguments to their specified types
        coerced_kwargs = {}
        for k, v in filtered_kwargs.items():
            param_annotation = signature.parameters[k].annotation
            # Only coerce the argument if it is a primitive type
            if isinstance(v, (int, float, str, bool)):
                try:
                    coerced_kwargs[k] = param_annotation(v)
                except (TypeError, ValueError):
                    # If the argument cannot be coerced, use the original value
                    coerced_kwargs[k] = v
            else:
                coerced_kwargs[k] = v
    else:
        # Coercion is disabled, so just use the filtered arguments
        coerced_args = filtered_args
        coerced_kwargs = filtered_kwargs

    return coerced_args + extra_args, {**coerced_kwargs, **extra_kwargs}


def validate_function_input(
    signature: Signature, args: list, kwargs: dict[str, Any], validate_type: bool = True
) -> bool:
    """
    Validate input arguments against the stage signature.

    :param args: List of input positional arguments.
    :param kwargs: Dictionary of input keyword arguments.
    :return: True if all input arguments are valid according to the stage signature,
    False otherwise.
    """
    # combine args and kwargs into a dictionary
    combined = combine_args_kwargs(signature, args, kwargs)
    # get the parameters from the stage signature
    params = signature.parameters

    # check that all required arguments are present and have valid types
    for k, param in params.items():
        if param.kind in {Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD}:
            continue
        if param.default == Parameter.empty and k not in combined:
            return False

        if validate_type and not (coerced_val := check_type(param.annotation, combined[k])):
            return False
        elif validate_type and coerced_val:
            combined[k] = coerced_val

    # check that there are no extra arguments
    excess_args = len(args) - len(
        [p for p in params.values() if p.kind == Parameter.POSITIONAL_OR_KEYWORD]
    )
    if excess_args > 0 and not any(p.kind == Parameter.VAR_POSITIONAL for p in params.values()):
        return False

    # check that there are no extra keyword arguments
    excess_kwargs = set(kwargs.keys()) - set(params.keys())
    if excess_kwargs and not any(p.kind == Parameter.VAR_KEYWORD for p in params.values()):
        return False

    return True


def update_signature(signature: Signature, parameters: dict[str, dict[str, Any]]) -> Signature:
    """
    Update the stage signature with new parameter information.
    :param signature: The signature to update.
    :type signature: Signature
    :param parameters: A dictionary of new parameter information in the
    form of {name: {"type": type, "default": default}}. Default is optional and
    will not be set if not provided.
    :type parameters: dict[str, dict[str, Any]]
    :return: The updated signature.
    """
    existing_params = signature.parameters
    new_params = []
    return_annotation = parameters.pop("return", None) or signature.return_annotation  # noqa: E501

    # Iterate over the existing parameters and update them as necessary
    var_keyword_index = -1
    for i, (name, param) in enumerate(existing_params.items()):
        if name in parameters:
            # Replace the annotation and default value of the existing parameter
            param_info = parameters[name]
            type_ = param_info["type"]

            # If no default is provided, use the existing default
            default = param_info.get("default", Parameter.empty)
            if default is Parameter.empty:
                default = param.default

            # Coerce the old default into the new type if it changed
            if (
                (not param.annotation == type_)
                and (default is param.default)
                and (default is not Parameter.empty)
            ):
                try:
                    default = type_(param.default)
                except (TypeError, ValueError):
                    raise ValueError(
                        "Could not coerce old default into new type. Please provide a new default."
                    )

            param = param.replace(annotation=type_, default=default)

        if param.kind == Parameter.VAR_KEYWORD:
            var_keyword_index = i

        new_params.append(param)

    # Add any new parameters that were not in the existing parameters
    for name, param_info in parameters.items():
        if name not in existing_params:
            type_ = param_info["type"]
            default = param_info.get("default", Parameter.empty)
            param = Parameter(
                name=name, kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=type_, default=default
            )
            if var_keyword_index != -1:
                # Insert the new parameter before the VAR_KEYWORD parameter
                new_params.insert(var_keyword_index, param)
                var_keyword_index += 1
            else:
                new_params.append(param)

    # Create a new signature with the updated parameters
    return Signature(new_params, return_annotation=return_annotation)


def remove_signature_parameter(signature: Signature, parameter_name: str) -> Signature:
    """
    Remove a parameter from the stage signature.

    :param signature: The signature to update.
    :type signature: Signature
    :param name: The name of the parameter to remove.
    :type name: str
    :return: The updated signature.
    """
    existing_params = signature.parameters
    new_params = []

    # Iterate over the existing parameters and exclude the specified parameter
    for name, param in existing_params.items():
        if name != parameter_name:
            new_params.append(param)

    # Create a new signature with the updated parameters
    return Signature(new_params, return_annotation=signature.return_annotation)


def add_signature_parameter(
    signature: Signature,
    name: str,
    type_: Type,
    default: Any = Parameter.empty,
    kind: _ParameterKind = Parameter.POSITIONAL_OR_KEYWORD,
) -> Signature:
    """
    Add a new parameter to the stage signature.

    :param signature: The signature to update.
    :type signature: Signature
    :param name: The name of the parameter.
    :type name: str
    :param type_: The type annotation of the parameter.
    :type type_: Type
    :param default: The default value of the parameter.
    :type default: Any
    :param kind: The kind of parameter (positional, keyword, var-positional, or var-keyword).
    :type kind: _ParameterKind
    :return: The updated signature.
    """
    if kind in {Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD}:
        if kind == Parameter.VAR_POSITIONAL:
            name = "args"
        else:
            name = "kwargs"

    if default != Parameter.empty and not isinstance(default, type_):
        try:
            default = type_(default)
        except (TypeError, ValueError):
            raise ValueError("Could not coerce default into type. Please provide a new default.")

    existing_params = list(signature.parameters.values())
    positional_params = [p for p in existing_params if p.kind == Parameter.POSITIONAL_OR_KEYWORD]

    if kind == Parameter.VAR_POSITIONAL:
        var_positional_index = len(positional_params)
        new_params = (
            existing_params[:var_positional_index]
            + [Parameter(name=name, kind=kind, annotation=type_, default=default)]
            + existing_params[var_positional_index:]
        )
    else:
        new_params = existing_params + [
            Parameter(name=name, kind=kind, annotation=type_, default=default)
        ]

    return Signature(new_params, return_annotation=signature.return_annotation)


def get_signature_parameter(
    signature: Signature,
    value: Any,
    by: str = "name",
) -> Parameter:
    """
    Get a parameter object from the stage signature.

    :param signature: The stage signature.
    :type signature: Signature
    :param value: The value to search for.
    :type value: Any
    :param by: The type of search to perform. Can be "name" or "idx".
    :type by: str
    :return: The corresponding parameter object.
    """
    match by.lower():
        case "idx":
            return list(signature.parameters.values())[value]
        case "name" | _:
            return signature.parameters[value]


def in_virtualenv() -> bool:
    """
    Determine if the current Python interpreter is running in a virtual env.
    """
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        return True
    return False


def get_python_executable() -> Path:
    # See the big red warning box on
    # https://docs.python.org/3/library/subprocess.html#subprocess.Popen
    # for best practices when calling python interpreter
    # Get the path to the current Python interpreter
    python_executable = Path(sys.executable)

    # Check if a virtual environment is active
    if in_virtualenv():
        # If a virtual environment is active, use its Python interpreter
        python_executable = Path(sys.prefix) / "bin" / "python"

    return python_executable


def get_filename_from_url(url: str) -> str:
    """
    Get the filename from a URL.

    :param url: The URL to parse.
    :type url: str
    :return: The filename.
    """
    path = urlparse(url).path
    return os.path.basename(path)


def parse_bytes(s: float | str) -> int:
    """Parse byte string to numbers

    >>> from flowdapt.lib.utils.misc import parse_bytes
    >>> parse_bytes('100')
    100
    >>> parse_bytes('100 MB')
    100000000
    >>> parse_bytes('100M')
    100000000
    >>> parse_bytes('5kB')
    5000
    >>> parse_bytes('5.4 kB')
    5400
    >>> parse_bytes('1kiB')
    1024
    >>> parse_bytes('1e6')
    1000000
    >>> parse_bytes('1e6 kB')
    1000000000
    >>> parse_bytes('MB')
    1000000
    >>> parse_bytes(123)
    123
    >>> parse_bytes('5 foos')
    Traceback (most recent call last):
        ...
    ValueError: Could not interpret 'foos' as a byte unit
    """
    byte_sizes = {
        "kB": 10**3,
        "MB": 10**6,
        "GB": 10**9,
        "TB": 10**12,
        "PB": 10**15,
        "KiB": 2**10,
        "MiB": 2**20,
        "GiB": 2**30,
        "TiB": 2**40,
        "PiB": 2**50,
        "B": 1,
        "": 1,
    }
    byte_sizes = {k.lower(): v for k, v in byte_sizes.items()}
    byte_sizes.update({k[0]: v for k, v in byte_sizes.items() if k and "i" not in k})
    byte_sizes.update({k[:-1]: v for k, v in byte_sizes.items() if k and "i" in k})

    if isinstance(s, (int, float)):
        return int(s)
    s = s.replace(" ", "")
    if not any(char.isdigit() for char in s):
        s = "1" + s

    for i in range(len(s) - 1, -1, -1):
        if not s[i].isalpha():
            break
    index = i + 1

    prefix = s[:index]
    suffix = s[index:]

    try:
        n = float(prefix)
    except ValueError as e:
        raise ValueError("Could not interpret '%s' as a number" % prefix) from e

    try:
        multiplier = byte_sizes[suffix.lower()]
    except KeyError as e:
        raise ValueError("Could not interpret '%s' as a byte unit" % suffix) from e

    result = n * multiplier
    return int(result)


def get_full_path_type(obj: Any) -> str:
    """
    Get the full path to an object's type.

    :param obj: The object to get the type of.
    :type obj: Any
    :return: The full path to the object's type.
    :rtype: str
    """
    return f"{type(obj).__module__}.{type(obj).__name__}"


def in_path(path: Path, words: list[str]) -> bool:
    """
    Determine if a sequence of words exists in a Path.
    """
    if any(word in str(path) for word in words):
        return True
    return False


def hash_map(map: Mapping):
    return hash(tuple(sorted(map.items())))


def recursive_rmdir(path: Path) -> None:
    """
    Recursively remove a directory and its contents.
    """
    if path.exists() and path.is_dir():
        for child in path.iterdir():
            if child.is_file():
                child.unlink()
            else:
                recursive_rmdir(child)
        path.rmdir()


def get_site_packages_dir() -> Path:
    return Path(site.getsitepackages()[0])


def dict_to_env_vars(obj: dict, prefix: str = "FLOWDAPT", path: str = ""):
    """
    Converts a nested dictionary to a map of environment variables.

    :param d: The dictionary to convert.
    :param prefix: The prefix for the environment variables.
    :param path: The current path in the dictionary (used for recursion).
    :return: A dictionary where keys are the env var names and
    values are their corresponding values.
    """
    env_vars = {}

    for key, value in obj.items():
        # Build the new path
        new_path = f"{path.upper()}__{key}" if path else key

        if isinstance(value, dict):
            # Merge with recursive call for nested dictionaries
            env_vars.update(dict_to_env_vars(value, prefix, new_path))
        else:
            # Construct the environment variable
            env_vars[f"{prefix}__{new_path}".upper()] = str(value)

    return env_vars


def normalize_env_vars(env_vars: dict[str, Any]) -> dict[str, str]:
    """
    Normalize environment variables to strings.

    :param env_vars: The environment variables to normalize.
    :type env_vars: dict[str, Any]
    :return: The normalized environment variables.
    """
    return {str(k): str(v) for k, v in env_vars.items()}


class OrderedSet(Generic[T]):
    def __init__(self, iterable: Iterable[T] | None = None):
        self._data = dict()
        if iterable is not None:
            self.update(iterable)

    def add(self, item: T) -> None:
        self._data[item] = None

    def discard(self, item: T) -> None:
        self._data.pop(item, None)

    def update(self, iterable: Iterable[T]) -> None:
        for item in iterable:
            self.add(item)

    def __contains__(self, item: T) -> bool:
        return item in self._data

    def __iter__(self) -> Iterator[T]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __sub__(self, other: "OrderedSet[T]") -> "OrderedSet[T]":
        return OrderedSet(item for item in self if item not in other)

    def __repr__(self) -> str:
        return f"OrderedSet({list(self._data.keys())})"
