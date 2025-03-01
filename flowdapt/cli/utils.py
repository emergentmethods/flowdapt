from typing import Any, Literal

from rich import box
from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Column, Table
from typer import Exit


def exit_with_error(message: str, code: int = 1):
    render_error_panel(message)
    raise Exit(code=code)


def confirm(message: str):
    return Confirm.ask(message)


# --------------- NEW ----------------------


def render_table(columns: list[str], rows: list[list[str]]):
    cols = [(col.capitalize(), {"justify": "center"}) for col in columns]

    render(build_table(columns=cols, rows=rows))


def render(renderable):
    console = Console()
    console.print(renderable)


def build_markdown(markdown: str):
    return Markdown(markdown)


def build_panel(
    content: str,
    title: str = "",
    subtitle: str = "",
    align: Literal["left", "center", "right"] = "left",
):
    return Panel(
        Align(content, align=align),
        title=title,
        subtitle=subtitle,
        box=box.ROUNDED,
    )


def build_syntax(syntax: str, language: str = "yaml", theme: str = "dracula"):
    return Syntax(syntax, language, line_numbers=True, background_color="default", theme=theme)


def build_table(
    title: str = "",
    caption: str = "",
    columns: list[tuple[str, dict[str, Any]]] = [],
    rows: list[list[str]] = [],
    padding: int = 1,
    expand: bool = True,
):
    columns_ = [Column(item[0], **item[1]) for item in columns]
    table = Table(
        *columns_,
        title=title,
        caption=caption,
        expand=expand,
        padding=padding,
        pad_edge=True,
        show_lines=True,
        show_header=True if columns else False,
        box=box.ROUNDED,
    )

    for row in rows:
        table.add_row(*row)

    return table


# ------------------- OLD --------------------


def render_syntax(syntax: str, language: str = "yaml", theme: str = "dracula"):
    console = Console()
    console.print(
        Syntax(syntax, language, line_numbers=True, background_color="default", theme=theme)
    )


def render_result_panel(content: str):
    return render_panel(content, title="[blue_violet]RESULT")


def render_error_panel(content: str):
    return render_panel(content, title="[red]ERROR")


def render_warning_panel(content: str):
    return render_panel(content, title="[yellow]WARNING")


def render_panel(content: str, title: str = "", subtitle: str = ""):
    console = Console()

    panel = Panel(
        Align(content, align="center"),
        title=title,
        subtitle=subtitle,
        box=box.ROUNDED,
    )
    console.print(panel)


def track_progress():
    return Progress(*Progress.get_default_columns(), transient=True, expand=True)


def track_progress_spinner():
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        expand=True,
    )
