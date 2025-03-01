import typer

from flowdapt.cli.config import config_cli
from flowdapt.cli.db import db_cli
from flowdapt.cli.dev import dev_cli
from flowdapt.cli.main import cli
from flowdapt.cli.run import run_cli


# Get command reference object for docs
main_ref = typer.main.get_command(cli)


__all__ = (
    "cli",
    "main_ref",
    "run_cli",
    "db_cli",
    "config_cli",
    "dev_cli",
)
