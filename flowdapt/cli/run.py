import typer

from flowdapt import __version__
from flowdapt.cli._internal import AsyncTyper
from flowdapt.cli.main import cli
from flowdapt.lib.config import Configuration
from flowdapt.lib.database import create_database_from_config
from flowdapt.lib.logger import get_logger
from flowdapt.lib.rpc import RPC
from flowdapt.lib.rpc.api import create_api_server
from flowdapt.lib.rpc.eventbus import create_event_bus
from flowdapt.lib.service import run_services
from flowdapt.lib.telemetry import setup_telemetry, shutdown_telemetry


logger = get_logger(__name__)
run_cli = AsyncTyper(name="run")
cli.add_typer(run_cli)


@run_cli.callback(invoke_without_command=True, subcommand_metavar="")
async def run(
    typer_context: typer.Context,
    run_migrations: bool = typer.Option(
        True,
        "--run-migrations/--no-migrations",
        help="Run database migrations when starting the server.",
    ),
) -> None:
    """
    Run the flowdapt server
    """
    from flowdapt.compute.service import ComputeService
    from flowdapt.triggers.service import TriggerService

    config: Configuration = typer_context.obj

    await logger.ainfo("ConfigurationLoaded", path=config.config_file)
    await logger.ainfo("FlowdaptStarting", version=__version__)

    # Start the telemetry
    setup_telemetry(config)

    # Run the Services until they exit
    await run_services(
        services=[ComputeService, TriggerService],
        context={
            "config": config,
            "database": await create_database_from_config(config, run_migrations=run_migrations),
            "rpc": RPC(
                await create_api_server(config.rpc.api.host, config.rpc.api.port),
                await create_event_bus(
                    config.rpc.event_bus.url,
                ),
            ),
        },
    )

    # Close the telemetry
    shutdown_telemetry()
