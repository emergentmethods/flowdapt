import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from flowdapt.lib.config import get_app_dir
from flowdapt.lib.logger import LoggerType
from flowdapt.lib.utils.asynctools import call_bash_command, run_in_thread
from flowdapt.lib.utils.misc import get_python_executable, in_path


async def parse_package_manifest(manifest_path: Path, skip_words: list[str] = []) -> list[Path]:
    """
    Parse a Python Package's MANIFEST.in file to get the included data files.
    """
    manifest_dir = manifest_path.parent

    files_included: set[Path] = set()
    files_excluded: set[Path] = set()

    content = await run_in_thread(manifest_path.read_text, "utf-8")

    # Parse each line for the directives and get the
    # files
    for line in content.splitlines():
        # Skip any comment lines or empty lines
        if line and not line.startswith("#"):
            tokens = line.split()

            directive = tokens[0]
            args = tokens[1:]

            # We do not support `graft` and `prune`
            match directive:
                case "include":
                    for pattern in args:
                        files_included.update(manifest_dir.rglob(pattern))
                case "exclude":
                    for pattern in args:
                        files_excluded.update(manifest_dir.rglob(pattern))
                case "recursive-include":
                    dir_pattern, *patterns = args

                    for path in manifest_dir.rglob(dir_pattern):
                        if path.is_dir():
                            for pattern in patterns:
                                files_included.update(path.rglob(pattern))
                case "recursive-exclude":
                    dir_pattern, *patterns = args
                    for path in manifest_dir.rglob(dir_pattern):
                        if path.is_dir():
                            for pattern in patterns:
                                files_excluded.update(path.rglob(pattern))
                case "global-include":
                    for pattern in args:
                        files_included.update(manifest_dir.rglob(pattern))
                case "global-exclude":
                    for pattern in args:
                        files_excluded.update(manifest_dir.rglob(pattern))

    # Ensure we exclude any files that have skip words in them
    files_excluded.update(
        [path for path in files_included if in_path(path, skip_words)],
        [path for path in files_included if await run_in_thread(path.is_dir)],
    )
    return list(files_included - files_excluded)


def get_user_modules_dir() -> Path | None:
    """
    Get the path to the user modules directory.
    """
    app_dir = get_app_dir()

    if app_dir is None:
        return None

    path = app_dir / "user_modules"

    if not path.exists():
        # Create the folder and add an __init__.py file so it can be imported
        path.mkdir(parents=True)
        (path / "__init__.py").touch()

    path_parent = str(path.parent)

    # Add the user modules parent directory to the path
    # to make it importable
    if "PYTHONPATH" not in os.environ or path_parent not in os.environ["PYTHONPATH"]:
        os.environ["PYTHONPATH"] = path_parent

    if path_parent not in sys.path:
        sys.path.append(path_parent)

    return path


def format_extras_for_pip(extras: list[str]) -> str:
    if not extras:
        return ""

    extras_str = "[" + ",".join(extras) + "]"
    return extras_str


async def call_pip(args: list[str], logger: LoggerType | None = None):
    """
    Call the pip command.
    """
    if logger:

        async def callback(line: str):
            line = line.strip()

            if line:
                await logger.adebug(line)
    else:
        callback = lambda x: None

    await call_bash_command(
        [str(get_python_executable()), "-m", "pip", *args], stream_callbacks=[callback]
    )


def add_auth_to_url(url: str, auth: tuple[str, str]) -> str:
    """
    Add authentication credentials to a URL.
    """
    parsed = urlparse(url)
    netloc = f"{auth[0]}:{auth[1]}@{parsed.netloc}"

    return urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )
