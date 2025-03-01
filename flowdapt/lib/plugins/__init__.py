from pathlib import Path

from flowdapt.lib.errors import ResourceNotFoundError
from flowdapt.lib.logger import get_logger
from flowdapt.lib.plugins.interface import PLUGIN_RESOURCE_KIND, Plugin, PluginManifest
from flowdapt.lib.plugins.utils import (
    add_auth_to_url,
    call_pip,
    format_extras_for_pip,
    get_user_modules_dir,
)
from flowdapt.lib.telemetry import get_current_span, get_tracer
from flowdapt.lib.utils.asynctools import run_in_thread


logger = get_logger(__name__)
tracer = get_tracer(__name__)

_manifest = PluginManifest()


def has_plugins() -> bool:
    return len(_manifest) > 0


def list_plugins() -> list[Plugin]:
    return _manifest.list_plugins()


def get_plugin(name: str) -> Plugin:
    try:
        return _manifest.get_plugin(name)
    except KeyError:
        raise ResourceNotFoundError()


@tracer.start_as_current_span("load_plugins")
async def load_plugins():
    try:
        # Call get_user_modules_dir() to ensure the directory exists
        get_user_modules_dir()
        await _manifest.load_plugins()
    finally:
        await logger.adebug("Plugins Loaded", discovered=len(_manifest))


@tracer.start_as_current_span("install_plugin")
async def install_plugin(
    plugin: str,
    version_constraints: str = "latest",
    extras: list[str] = [],
    editable: bool = False,
    upgrade: bool = False,
    index: str = "https://pypi.org/simple",
    auth: tuple[str, str] | None = None,
    extra_args: list[str] = [],
) -> None:
    span = get_current_span()
    span.set_attributes(
        {
            "plugin": plugin,
            "version_constraints": version_constraints,
            "extras": extras,
            "editable": editable,
            "upgrade": upgrade,
            "index": "pypi" if index == "https://pypi.org/simple" else "private",
            "auth": True if auth else False,
            "extra_args": extra_args,
        }
    )
    args = ["install"]

    if upgrade:
        args.append("--upgrade")

    if editable:
        args.append("--editable")

    if auth:
        index = add_auth_to_url(index, auth)

    args.extend(["--index-url", index])

    if not (
        any(
            [
                prefix in plugin
                for prefix in ("http://", "https://", "git+", "svn+", "hg+", "file://")
            ]
        )
        or await run_in_thread(Path(plugin).exists)
    ):
        if version_constraints != "latest":
            plugin = f"{plugin}{version_constraints}"
        if extras:
            plugin = f"{plugin}{format_extras_for_pip(extras)}"
    else:
        version_constraints = None

    args.append(plugin)
    args.extend(extra_args)

    _logger = logger.bind(
        plugin=plugin,
        version_constraints=version_constraints,
        editable=editable,
        extras=extras,
    )

    await _logger.adebug("PluginInstallInitiated")
    try:
        await call_pip(args, logger=logger.bind(installer="pip"))
    except BaseException as e:
        await _logger.aexception("PluginInstallFailed", error=str(e))
    else:
        await _logger.adebug("PluginInstallFinished")


@tracer.start_as_current_span("uninstall_plugin")
async def uninstall_plugin(plugin: str) -> None:
    plugin = get_plugin(plugin)

    span = get_current_span()
    span.set_attributes({"plugin": plugin})

    await logger.adebug("PluginUninstallInitiated", plugin=plugin.name)
    try:
        await call_pip(["uninstall", "-y", plugin.name], logger=logger.bind(installer="pip"))
    except BaseException as e:
        await logger.aexception("PluginUninstallFailed", error=str(e))
    else:
        await logger.adebug("Plugin Uninstalled", plugin=plugin.name)


__all__ = (
    "Plugin",
    "PluginManifest",
    "list_plugins",
    "get_plugin",
    "load_plugins",
    "install_plugin",
    "uninstall_plugin",
    "get_user_modules_dir",
    "PLUGIN_RESOURCE_KIND",
)
