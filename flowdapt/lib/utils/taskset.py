import asyncio
from contextlib import suppress
from typing import Coroutine

from flowdapt.lib.logger import LoggerType


class TaskSet:
    """
    Manages the set of tasks and faciliates cancelling them
    """

    def __init__(
        self,
        tasks: set[Coroutine] | None = None,
        return_exceptions: bool = False,
        logger: LoggerType | None = None,
    ):
        self._set: set[asyncio.Task] = set()
        self._return_exceptions = return_exceptions
        self._logger = logger

        self.loop = asyncio.get_running_loop()

        if tasks:
            for task in tasks:
                self.add(task)

    def add(self, coroutine: Coroutine) -> asyncio.Task:
        """
        Add a coroutine to be run in this `TaskSet`
        """
        task = self.loop.create_task(coroutine)

        task.add_done_callback(lambda _: self.remove(task))
        self._set.add(task)

        return task

    def remove(self, task: asyncio.Task):
        try:
            with suppress(asyncio.CancelledError):
                task.result()
        except BaseException as e:
            if not self._return_exceptions:
                raise e
            else:
                if self._logger:
                    self._logger.error(f"Exception in task: {e}", exc_info=e)

        self._set.remove(task)

    def cancel(self):
        """
        Cancel all registered tasks in this `TaskSet`
        """
        for task in self._set:
            task.cancel()

    def __await__(self):
        """
        Run and gather all tasks in this `TaskSet`
        """
        return asyncio.gather(*self._set, return_exceptions=self._return_exceptions).__await__()
