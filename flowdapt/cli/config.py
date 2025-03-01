"""
Commands to manage the Configuration
"""

import typer

from flowdapt.cli._internal import AsyncTyper
from flowdapt.cli.main import cli
from flowdapt.lib.config import Configuration
from flowdapt.lib.logger import get_logger
from flowdapt.lib.serializers import JSONSerializer, YAMLSerializer
from flowdapt.lib.utils.model import model_dump


logger = get_logger(__name__)
config_cli = AsyncTyper(
    name="config", short_help="Commands for managing the Configuration.", help=__doc__
)
cli.add_typer(config_cli)


@config_cli.command()
async def show(
    typer_context: typer.Context,
    json: bool = typer.Option(False, "--json/--yaml"),
    raw: bool = typer.Option(False, "--raw"),
):
    """
    Show the resolved Configuration

    Use `--json` to render the configuration as JSON. Defaults to `--yaml`.
    """
    from flowdapt.cli.utils import render_syntax

    config: Configuration = typer_context.obj

    to_func = JSONSerializer.dumps if json else YAMLSerializer.dumps
    output = str(to_func(model_dump(config)), "utf-8")

    if raw:
        print(output)
    else:
        render_syntax(output, "json" if json else "yaml")


@config_cli.command()
async def set(
    typer_context: typer.Context,
    key: str = typer.Argument(..., help="The key to set."),
    value: str = typer.Argument(..., help="The value to set."),
):
    """
    Set the specified key to the specified value in the configuration file.
    """
    config: Configuration = typer_context.obj
    assert config.app_dir and config.config_file, "A config file must be specified to set a value."

    config = config.set_by_key(key, value)
    await config.to_file(config.config_file)  # type: ignore


@config_cli.command()
async def unset(
    typer_context: typer.Context,
    key: str = typer.Argument(..., help="The key to unset."),
):
    """
    Unset the specified key from the configuration file.
    """
    config: Configuration = typer_context.obj
    assert config.config_file, "A config file must be specified to set a value."

    config = config.unset_by_key(key)
    await config.to_file(config.config_file)  # type: ignore


@config_cli.command()
async def get(
    typer_context: typer.Context,
    key: str = typer.Argument(..., help="The key to get."),
):
    """
    Get the specified key from the configuration file.
    """
    config: Configuration = typer_context.obj

    value = config.get_by_key(key)
    print(value)
