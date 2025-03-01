"""
Utility commands for the database
"""

import typer

from flowdapt import __version__
from flowdapt.cli._internal import AsyncTyper
from flowdapt.cli.main import cli
from flowdapt.lib.logger import disable_logging, get_logger


logger = get_logger(__name__, version=__version__)
db_cli = AsyncTyper(name="db", short_help="Commands for the database.", help=__doc__)
cli.add_typer(db_cli)


@db_cli.command()
async def upgrade(
    typer_context: typer.Context,
    revision: str = typer.Option("head", "--rev", "-r", help="The revision ID to upgrade to."),
) -> None:
    """
    Upgrade the database to the specified revision.
    """
    from flowdapt.cli.utils import render_error_panel, render_result_panel
    from flowdapt.lib.database import create_database_from_config
    from flowdapt.lib.database.migrate import run_upgrade_from_dir

    with disable_logging():
        config = typer_context.obj
        database = await create_database_from_config(config, run_migrations=False)

        async with database:
            try:
                await run_upgrade_from_dir(database, revision)
                render_result_panel("Upgrade successful :rocket:")
            except BaseException as e:
                render_error_panel(f"Could not upgrade database: {e}")


@db_cli.command()
async def downgrade(
    typer_context: typer.Context,
    revision: str = typer.Option(..., "--rev", "-r", help="The revision ID to downgrade to."),
) -> None:
    """
    Downgrade the database to the specified revision.
    """
    from flowdapt.cli.utils import render_error_panel, render_result_panel
    from flowdapt.lib.database import create_database_from_config
    from flowdapt.lib.database.migrate import run_downgrade_from_dir

    with disable_logging():
        config = typer_context.obj
        database = await create_database_from_config(config, run_migrations=False)

        async with database:
            try:
                await run_downgrade_from_dir(database, revision)
                render_result_panel("Downgrade successful :rocket:")
            except BaseException as e:
                render_error_panel(f"Could not downgrade database: {e}")


@db_cli.command()
async def generate(
    typer_context: typer.Context,
    title: str = typer.Option(..., "--title", "-t", help="The revision title."),
) -> None:
    """
    Generate a database revision
    """
    from flowdapt.cli.utils import render_error_panel
    from flowdapt.lib.database.migrate import generate_next_script

    try:
        generate_next_script(revision_title=title)
    except BaseException as e:
        render_error_panel(f"Could not generate revision: {e}")


@db_cli.command()
async def current(
    typer_context: typer.Context,
) -> None:
    """
    Get the current database revision ID
    """
    from flowdapt.cli.utils import render_error_panel
    from flowdapt.lib.database import create_database_from_config

    with disable_logging():
        config = typer_context.obj
        database = await create_database_from_config(config, run_migrations=False)

        async with database:
            try:
                print(await database.current_revision_id())
            except BaseException as e:
                render_error_panel(f"Could not get current database revision: {e}")
