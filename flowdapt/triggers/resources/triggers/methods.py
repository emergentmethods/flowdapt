import asyncio
from datetime import datetime
from typing import AsyncIterator
from uuid import UUID

from flowdapt.lib.context import inject_context
from flowdapt.lib.database.base import BaseStorage
from flowdapt.lib.errors import ResourceNotFoundError
from flowdapt.lib.logger import get_logger
from flowdapt.lib.telemetry import get_tracer
from flowdapt.lib.utils.model import model_dump
from flowdapt.triggers.domain.models.triggerrule import TriggerRuleResource, TriggerRuleType
from flowdapt.triggers.resources.triggers.cron import get_next_run_datetime, is_ready_to_run


tracer = get_tracer(__name__)
logger = get_logger("flowdapt.triggers.service")


async def _get_trigger(identifier: str | UUID, database: BaseStorage) -> TriggerRuleResource:
    trigger = await TriggerRuleResource.get(database, identifier)

    if not trigger:
        raise ResourceNotFoundError

    return trigger


@tracer.start_as_current_span("list_triggers")
@inject_context
async def list_triggers(
    database: BaseStorage, type: TriggerRuleType | None = None
) -> list[TriggerRuleResource]:
    """
    List all TriggerRuleResources.

    :param database: BaseStorage
    :param type: TriggerRuleType | None
    :return: list[TriggerRuleResource]
    """
    async with database.transaction():
        if not type:
            return await TriggerRuleResource.get_all(database)
        elif type == TriggerRuleType.condition:
            return await TriggerRuleResource.get_conditional(database)
        elif type == TriggerRuleType.schedule:
            return await TriggerRuleResource.get_scheduled(database)


@tracer.start_as_current_span("get_trigger")
@inject_context
async def get_trigger(identifier: str | UUID, database: BaseStorage) -> TriggerRuleResource:
    """
    Get a TriggerRuleResource by identifier.

    :param identifier: str | UUID
    :param database: BaseStorage
    :return: TriggerRuleResource
    """
    async with database.transaction():
        return await _get_trigger(identifier, database)


@tracer.start_as_current_span("create_trigger")
@inject_context
async def create_trigger(
    payload: TriggerRuleResource, database: BaseStorage
) -> TriggerRuleResource:
    """
    Create a TriggerRuleResource given a payload.

    :param payload: TriggerRuleResource
    :param database: BaseStorage
    :return: TriggerRuleResource
    """
    async with database.transaction():
        await payload.insert(database)
        return payload


@tracer.start_as_current_span("delete_trigger")
@inject_context
async def delete_trigger(identifier: str | UUID, database: BaseStorage) -> TriggerRuleResource:
    """
    Delete a TriggerRuleResource by identifier.

    :param identifier: str | UUID
    :param database: BaseStorage
    :return: TriggerRuleResource
    """
    async with database.transaction():
        trigger = await _get_trigger(identifier, database)
        await trigger.delete(database)
        return trigger


@tracer.start_as_current_span("update_trigger")
@inject_context
async def update_trigger(
    identifier: str | UUID,
    payload: TriggerRuleResource,
    database: BaseStorage,
) -> TriggerRuleResource:
    """
    Update a TriggerRuleResource by identifier.

    :param identifier: str | UUID
    :param payload: TriggerRuleResource
    :param database: BaseStorage
    :return: TriggerRuleResource
    """
    async with database.transaction():
        trigger = await _get_trigger(identifier, database)
        await trigger.update(
            database, model_dump(payload, exclude={"metadata": {"uid", "created_at", "updated_at"}})
        )
        return trigger


@inject_context
async def set_last_run(
    resource: TriggerRuleResource, database: BaseStorage, last_run: datetime | None = None
):
    """
    Set the last_run annotation on a TriggerRuleResource.

    :param resource: TriggerRuleResource
    :param last_run: datetime
    :param database: BaseStorage
    :return: None
    """
    last_run = last_run or datetime.utcnow()

    async with database.transaction():
        resource.metadata.annotations["flowdapt.ai/last_run"] = last_run.isoformat()
        await resource.update(database)


@inject_context
async def _get_next_scheduled_triggers(
    database: BaseStorage, last_checked: datetime | None
) -> list[TriggerRuleResource]:
    to_run = []
    triggers: list[TriggerRuleResource] = await list_triggers(
        database, type=TriggerRuleType.schedule
    )

    for trigger in triggers:
        last_run = trigger.metadata.annotations.get("flowdapt.ai/last_run", None)

        if not last_run:
            last_run = datetime(1970, 1, 1, 0, 0, 0, 0)
        else:
            last_run = datetime.fromisoformat(last_run)

        for schedule in trigger.spec.rule:
            next_run = get_next_run_datetime(schedule, last_checked)

            await logger.adebug(
                "NextRun",
                trigger=trigger.metadata.name,
                next_run=next_run,
                last_run=last_run,
                schedule=schedule,
            )

            if is_ready_to_run(next_run, last_run, now=datetime.utcnow()):
                to_run.append(trigger)
                break

    return to_run


async def get_next_scheduled_triggers(check_delay: int = 5) -> AsyncIterator[TriggerRuleResource]:
    """
    Get the next scheduled triggers to run.

    :param check_delay: int
    :return: AsyncIterator[TriggerRuleResource]
    """
    last_checked = datetime.utcnow()

    while True:
        to_run = await _get_next_scheduled_triggers(last_checked=last_checked)

        if to_run:
            last_checked = datetime.utcnow()

            for trigger in to_run:
                yield trigger

        await asyncio.sleep(check_delay)
