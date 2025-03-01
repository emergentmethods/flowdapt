from flowdapt.core.rpc import register_rpc
from flowdapt.lib.config import Configuration
from flowdapt.lib.logger import get_logger
from flowdapt.lib.rpc import RPC
from flowdapt.lib.service import Service


logger = get_logger(__name__, service="core")


class CoreService(Service):
    """
    Core Service responsible for managing any RPC and mechanisms
    that are required for every server process.
    """

    def __initialize__(self, **kwargs) -> None:
        self._config: Configuration = self._context.config
        self._rpc: RPC = self._context.rpc

        register_rpc(self._rpc)

    async def __startup__(self):
        await logger.ainfo("ServiceStarting")
        await logger.ainfo("ServiceStarted")

    async def __shutdown__(self):
        await logger.ainfo("ServiceStopping")
        await logger.ainfo("ServiceStopped")

    async def __run__(self):
        await self._rpc.wait_until_finished()
