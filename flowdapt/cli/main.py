from pathlib import Path
from typing import Optional

import typer
from rich import print as pprint

from flowdapt import __version__
from flowdapt.cli._internal import AsyncTyper
from flowdapt.lib.config import (
    Configuration,
    config_from_env,
    set_app_dir,
    set_configuration,
)
from flowdapt.lib.logger import setup_logging
from flowdapt.lib.plugins import load_plugins
from flowdapt.lib.utils.misc import get_default_app_dir


cli = AsyncTyper(name="flowdapt")


def _show_version(show: bool):
    if show:
        pprint(__version__)
        raise typer.Exit(code=0)


@cli.callback(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
async def main(
    typer_context: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the flowdapt version and exit.",
        callback=_show_version,
        is_eager=True,
    ),
    app_dir: Optional[Path] = typer.Option(
        None,
        "--app-dir",
        "-d",
        envvar="FLOWDAPT__APP_DIR",
        help="The application directory path.",
    ),
    config_file: str = typer.Option(
        "flowdapt.yaml",
        "--config",
        "-c",
        envvar="FLOWDAPT__CONFIG_FILE",
        help="The configuration file path relative to the config directory.",
    ),
    dotenv: list[str] = typer.Option([], "--env", help="Load a .env file in the configuration."),
    dev_mode: bool = typer.Option(
        False, "--dev", envvar="FLOWDAPT_DEV_MODE", help="Use flowdapt in development mode."
    ),
    overrides: list[str] = typer.Option([], "-o", "--override", help="Configuration overrides."),
) -> None:
    app_dir = (app_dir or get_default_app_dir()).expanduser().resolve()
    set_app_dir(app_dir)

    if not config_file == "-":
        # If the user specified a config file, it should be in the
        # app_dir, so we need to make sure it exists. If it doesn't,
        # write the default configuration to that path.
        config_path = app_dir / config_file

        # If it doesn't exist, write the default values to it
        if not config_path.exists():
            await Configuration(config_file=config_file).to_file(config_path)

        # Read the configuration file and build the full
        # model from it, the environment vars, and the CLI args.
        config = typer_context.obj = await Configuration.build(
            files=[] if not config_path else [config_path],
            dotenv_files=dotenv,
            key_values=overrides,
            env_prefix="FLOWDAPT",
            config_file=config_file,
            dev_mode=dev_mode,
        )
    else:
        # If the user specified "-" then use default configuration
        config = typer_context.obj = await config_from_env(
            config_file=config_file, dev_mode=dev_mode
        )

    set_configuration(config)

    # Only show locals in exceptions when in dev mode
    # TODO: Use `flowctl` style global error handling when not in dev mode
    cli.pretty_exceptions_show_locals = config.dev_mode
    # Automatically convert logging level if dev mode is active
    config.logging.level = "DEBUG" if config.dev_mode else config.logging.level
    # Automatically set show tracebacks if dev mode is active
    if not config.logging.show_tracebacks and config.dev_mode:
        config.logging.show_tracebacks = True

    setup_logging()
    await load_plugins()
