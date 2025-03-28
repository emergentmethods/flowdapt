import asyncio

from flowdapt.lib.config import Configuration
from flowdapt.lib.logger import get_logger
from flowdapt.lib.rpc import RPC
from flowdapt.lib.service import Service
from flowdapt.triggers.resources.triggers.methods import get_next_scheduled_triggers, set_last_run
from flowdapt.triggers.rpc import register_rpc


logger = get_logger(__name__, service="trigger")


class TriggerService(Service):
    """
    Trigger Service is responsible for managing TriggerRules which
    dictate conditions and schedules for actions to be taken such as
    running a workflow.
    """

    def __initialize__(self, **kwargs) -> None:
        self._config: Configuration = self._context.config
        self._rpc: RPC = self._context.rpc

        self._schedule_task = None
        self._stopped = asyncio.Event()

        register_rpc(self._rpc)

    async def _run_scheduled_triggers(self):
        while not self._stopped.is_set():
            try:
                async for trigger in get_next_scheduled_triggers():
                    await logger.ainfo("RunningScheduledTrigger", trigger=trigger.metadata.name)
                    await set_last_run(trigger)
                    await trigger.spec.action.run()
            except asyncio.CancelledError:
                return
            except Exception as e:
                await logger.aerror("ExceptionOccurred", error=str(e))

    async def __startup__(self):
        await logger.ainfo("ServiceStarting")

        if not self._schedule_task:
            self._schedule_task = asyncio.create_task(self._run_scheduled_triggers())

        self._stopped.clear()

        await logger.ainfo("ServiceStarted")

    async def __shutdown__(self):
        await logger.ainfo("ServiceStopping")

        self._stopped.set()

        if self._schedule_task:
            self._schedule_task.cancel()

            await self._schedule_task

        await logger.ainfo("ServiceStopped")

    async def __run__(self):
        await self._rpc.wait_until_finished()
