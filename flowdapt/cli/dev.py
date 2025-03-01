"""
Commands useful for development.
"""

from pathlib import Path
from typing import Type

import typer

from flowdapt import __version__
from flowdapt.cli._internal import AsyncTyper
from flowdapt.cli.main import cli
from flowdapt.lib.context import create_context
from flowdapt.lib.logger import get_logger


logger = get_logger(__name__, version=__version__)
dev_cli = AsyncTyper(name="dev", short_help="Commands for development.", help=__doc__, hidden=True)
cli.add_typer(dev_cli)


@dev_cli.command()
async def spec(
    typer_context: typer.Context,
    services: list[str] = typer.Option(
        ["all"], "-s", "--service", help="The Service API specifications to generate."
    ),
    version: str = typer.Option(
        "latest", "-v", "--version", help="The specification version to generate."
    ),
    openapi_version: str = typer.Option(
        "3.0.2", "--openapi-version", help="The OpenAPI specificationv version to use."
    ),
    output_path: Path = typer.Option(
        "openapi.json", "-o", "--output", help="The path to write the specification file."
    ),
    json: bool = typer.Option(
        True, "--json/--yaml", help="The format to write the specification file."
    ),
):
    """
    Generate the API specification.
    """
    from flowdapt.compute.service import ComputeService
    from flowdapt.core.service import CoreService
    from flowdapt.lib.rpc import RPC
    from flowdapt.lib.rpc.api import APIServer, create_api_server
    from flowdapt.lib.rpc.eventbus import create_event_bus
    from flowdapt.lib.serializers import JSONSerializer, YAMLSerializer
    from flowdapt.lib.service import Service
    from flowdapt.triggers.service import TriggerService

    context = create_context(
        {
            "config": typer_context.obj,
            "rpc": RPC(await create_api_server(), await create_event_bus()),
        }
    )

    _available_services: dict[str, list[Type[Service]]] = {
        "compute": [ComputeService],
        "trigger": [TriggerService],
        "core": [CoreService],
        "all": [ComputeService, TriggerService, CoreService],
    }

    to_generate = [
        service
        for name in services
        if name in _available_services
        for service in _available_services[name]
    ]

    for service in to_generate:
        instance = service(context)
        instance.__initialize__()

    api_server: APIServer = context["rpc"]._api_server
    spec = api_server.generate_spec()

    content = JSONSerializer.dumps(spec) if json else YAMLSerializer.dumps(spec)
    output_path.write_bytes(content)
