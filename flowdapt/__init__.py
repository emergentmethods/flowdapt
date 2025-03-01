import asyncio
import sys
from importlib import metadata


__version__ = metadata.version(__package__)
del metadata

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    if sys.version_info >= (3, 8) and sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # noqa
