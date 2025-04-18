from __future__ import annotations

import asyncio
from inspect import Signature, getdoc, getsourcefile, iscoroutine, signature
from typing import Callable, ClassVar, TypeVar

from flowdapt.compute.domain.models.workflow import WorkflowStage
from flowdapt.compute.executor.base import Executor
from flowdapt.compute.resources.workflow.context import (
    WorkflowRunContext,
    reset_run_context,
    set_run_context,
)
from flowdapt.lib.config import config_from_env, get_configuration, set_configuration
from flowdapt.lib.logger import setup_logging
from flowdapt.lib.utils.asynctools import is_async_callable, to_sync
from flowdapt.lib.utils.misc import (
    filter_args,
    hash_file,
    import_from_string,
    parse_bytes,
    remove_signature_parameter,
    update_signature,
    validate_function_input,
)
from flowdapt.lib.utils.model import (
    BaseModel,
    CallableOrImportString,
    after_validator,
    get_model_extras,
    model_dump,
    pre_validator,
)


R = TypeVar("R")


class StageResources(BaseModel, extra="allow"):
    cpus: float | None = None
    gpus: float | None = None
    memory: float | None = None

    @pre_validator()
    @classmethod
    def _validate(cls, values: dict):
        if "memory" in values and values["memory"] is not None:
            values["memory"] = parse_bytes(values["memory"])

        for key in ["cpus", "gpus"]:
            if key in values:
                if values[key] is not None:
                    values[key] = float(values.get(key, 0))

        # Parse extras as floats
        values.update(
            {k: float(v) for k, v in values.items() if k not in cls.model_fields and v is not None}
        )

        return values

    def extras(self):
        """
        Get the extra set fields that are not defined in the model.
        """
        return {k: float(v) for k, v in get_model_extras(self).items()}


# The base parameters that all stages require
class BaseStage(BaseModel, arbitrary_types_allowed=True):
    target: CallableOrImportString
    fn: Callable[..., R]
    type: ClassVar[str] = "base"
    name: str
    signature: Signature
    depends_on: list[str] = []
    description: str = ""
    version: str = ""
    resources: StageResources = StageResources()
    priority: int | None = None

    @property
    def is_async(self):
        return is_async_callable(self.fn)

    def get_stage_fn(self):
        stage_dict = model_dump(self, exclude={"fn", "signature"}, exclude_none=True)
        return stage_wrapper(stage_dict)

    def get_required_resources(self) -> dict[str, float]:
        return model_dump(self.resources, exclude_none=True)

    @pre_validator()
    @classmethod
    def _validate(cls, values):
        fn = values.get("fn", None)
        target = values["target"]

        if not fn and callable(target):
            _fn = target
        else:
            assert isinstance(target, str), "`target` must be an import path or callable"
            _fn = import_from_string(target)

        values["fn"] = _fn

        if not values["description"]:
            if desc := getdoc(_fn):
                values["description"] = desc

        if not values["version"]:
            values["version"] = hash_file(getsourcefile(_fn))

        values["signature"] = signature(_fn)
        values["name"] = _fn.__name__ if not values["name"] else values["name"]

        _internal_params = ["context"]
        if any([True for param in _internal_params if param in values["signature"].parameters]):
            raise ValueError(
                f"Stage `{values['name']}` cannot have the following parameters: {_internal_params}"
            )

        return values

    @classmethod
    def from_definition(cls, definition: WorkflowStage | dict) -> BaseStage:
        """
        Convert to the corresponding BaseStage given the
        type field.
        """
        if isinstance(definition, dict):
            definition = WorkflowStage(**definition)

        return get_available_stage_types()[definition.type](
            # Merge together the base information and the options
            **{**model_dump(definition, exclude={"options"}), **definition.options}
        )

    def create_lazy(
        self, executor: Executor, context: WorkflowRunContext, args: list, kwargs: dict
    ):
        raise NotImplementedError()

    def get_partial(
        self, executor: Executor, context: WorkflowRunContext, args: list, kwargs: dict
    ):
        # Pre-add any optional internal arguments to kwargs if the stage needs them,
        # if not they will get filtered out.
        # kwargs.update({})

        # First, filter and validate the arguments
        filtered_args, filtered_kwargs = filter_args(self.signature, args, kwargs, coerce=False)

        # Validate the arguments
        valid_input = validate_function_input(
            self.signature, filtered_args, filtered_kwargs, validate_type=False
        )

        # Input doesn't match the signature
        if not valid_input:
            raise ValueError(
                f"Invalid arguments provided: {filtered_args}, {filtered_kwargs}"
                f" for signature: {self.signature}"
            )
        # Input matches, args are empty, and stage depends on a previous stage
        elif (
            valid_input and self.depends_on and len(filtered_args) < 1 and len(filtered_kwargs) < 1
        ):
            raise ValueError(
                f"Stage `{self.name}` takes no arguments but depends on previous stage."
            )

        # Add the internal arguments
        filtered_kwargs.update(
            {
                # This is always used in the stage_wrapper
                "context": context
            }
        )

        # Return the wrapped stage function
        return self.create_lazy(
            executor=executor, context=context, args=filtered_args, kwargs=filtered_kwargs
        )


class SimpleStage(BaseStage):
    type: ClassVar[str] = "simple"

    def create_lazy(
        self, executor: Executor, context: WorkflowRunContext, args: list, kwargs: dict
    ):
        # Nothing special here, just decorate the function with the lazy_func
        return executor.lazy(self)(*args, **kwargs)


class ParameterizedStage(BaseStage):
    type: ClassVar[str] = "parameterized"
    map_on: str | None = None

    @after_validator()
    def _update_signature(cls, value: ParameterizedStage):
        # Update the signature to reflect this stage actually returns a list
        # of the original return type
        if (map_on := value.map_on) and map_on in value.signature.parameters:
            value.signature = remove_signature_parameter(value.signature, map_on)

        # Change the output value to reflect the change in behavior for this stage
        value.signature = update_signature(
            value.signature,
            {
                "return": list[value.signature.return_annotation],
            },
        )
        return value

    def create_lazy(
        self, executor: Executor, context: WorkflowRunContext, args: list, kwargs: dict
    ):
        if self.map_on:
            # If we have a map_on, prioritize the iterable from the payload
            args = [context.input[self.map_on], *args]

            # Handle the case where the stage is the first one in the workflow and also
            # got passed the payload
            if self.map_on in kwargs:
                kwargs.pop(self.map_on)

        # Wrap the executor specific map_inner with lazy_func and use the first
        # item in the args as the iterable. If the parameterized stage maps on an
        # input, the stage must still accept any args from the previous stage if there
        # are any.
        iterable = args.pop(0)

        return executor.mapped_lazy(self)(iterable, *args, **kwargs)


def get_available_stage_types() -> dict:
    return {type_.type: type_ for type_ in [SimpleStage, ParameterizedStage]}


def stage_wrapper(stage_definition: dict):
    """
    A wrapper around the stage execution function that handles
    the execution context and the stage execution itself.
    """
    # We import the executor code when inside the stage to ensure any
    # executor specific code is imported in the worker in case it
    # has any import level code to run
    __executor_imports = {
        "dask": "flowdapt.compute.executor.dask",
        "ray": "flowdapt.compute.executor.ray",
        "local": "flowdapt.compute.executor.local",
    }

    def wrapper(*args, context: WorkflowRunContext, **kwargs):
        # Set the configuration for this stage
        if not get_configuration(use_temp=False):
            set_configuration(to_sync(config_from_env)())

        stage = BaseStage.from_definition(stage_definition)

        # Import the executor code
        import_from_string(__executor_imports[context.executor], is_module=True, use_cache=True)

        # Call setup logging to configure the logger in the worker
        setup_logging()

        # Set the WorkflowRunContext ContextVar for this stage
        token = set_run_context(context)
        try:
            # Execute the stage
            result = stage.fn(*args, **kwargs)

            # If the result is a coroutine, run it. We could just let
            # the coroutine bubble up and have the executor's thread pool or
            # Ray just handle running it but the context will be lost.
            if iscoroutine(result):
                return asyncio.run(result)
            else:
                return result
        finally:
            # Reset the WorkflowRunContext ContextVar
            reset_run_context(token)

    return wrapper
