from functools import reduce
from uuid import UUID

from flowdapt.compute.domain.models.config import ConfigResource
from flowdapt.lib.context import inject_context
from flowdapt.lib.database.base import BaseStorage
from flowdapt.lib.domain.models.base import Resource
from flowdapt.lib.errors import ResourceNotFoundError
from flowdapt.lib.telemetry import get_tracer
from flowdapt.lib.utils.model import model_dump


tracer = get_tracer(__name__)


async def _get_config(identifier: str | UUID, database: BaseStorage) -> ConfigResource:
    config = await ConfigResource.get(database, identifier)

    if not config:
        raise ResourceNotFoundError

    return config


async def _get_configs(resource: Resource, database: BaseStorage) -> list[ConfigResource]:
    return await ConfigResource.get_configs(database, resource)


@tracer.start_as_current_span("list_configs")
@inject_context
async def list_configs(database: BaseStorage) -> list[ConfigResource]:
    """
    List all ConfigResources.

    :param database: BaseStorage
    :return: list[ConfigResource]
    """
    async with database.transaction():
        return await ConfigResource.get_all(database)


@tracer.start_as_current_span("get_config")
@inject_context
async def get_config(identifier: str | UUID, database: BaseStorage) -> ConfigResource:
    """
    Get a ConfigResource with the given identifier.

    :param identifier: str | UUID
    :param database: BaseStorage
    :return: ConfigResource
    """
    async with database.transaction():
        return await _get_config(identifier, database)


@tracer.start_as_current_span("create_config")
@inject_context
async def create_config(payload: ConfigResource, database: BaseStorage) -> ConfigResource:
    """
    Create a ConfigResource with the given payload.

    :param payload: ConfigResource
    :param database: BaseStorage
    :return: ConfigResource
    """
    async with database.transaction():
        await payload.insert(database)
        return payload


@tracer.start_as_current_span("delete_config")
@inject_context
async def delete_config(identifier: str | UUID, database: BaseStorage) -> ConfigResource:
    """
    Delete a ConfigResource with the given identifier.

    :param identifier: str | UUID
    :param database: BaseStorage
    :return: ConfigResource
    """
    async with database.transaction():
        config = await _get_config(identifier, database)
        await config.delete(database)
        return config


@tracer.start_as_current_span("update_config")
@inject_context
async def update_config(
    identifier: str | UUID, payload: ConfigResource, database: BaseStorage
) -> ConfigResource:
    """
    Update a ConfigResource with the given payload.

    :param identifier: str | UUID
    :param payload: ConfigResource
    :param database: BaseStorage
    :return: ConfigResource
    """
    async with database.transaction():
        config = await _get_config(identifier, database)
        await config.update(database, model_dump(payload))
        return config


@tracer.start_as_current_span("get_configs")
@inject_context
async def get_configs(resource: Resource, database: BaseStorage) -> list[ConfigResource]:
    """
    Given a Resource, return a list of ConfigResources associated with it.

    :param resource: Resource
    :param database: BaseStorage
    :return: list[ConfigResource]
    """
    async with database.transaction():
        return await _get_configs(resource, database)


def get_merged_config_data(configs: list[ConfigResource]) -> dict:
    """
    Given a list of ConfigResources, return a dict of the merged data
    to be used.

    :param configs: list[ConfigResource]
    :return: dict
    """
    return reduce(lambda a, b: a | b, map(lambda c: c.spec.data, configs), {})
