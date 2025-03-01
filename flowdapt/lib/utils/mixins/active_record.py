from typing import TypeVar
from uuid import UUID

from flowdapt.lib.database.base import BaseStorage


T = TypeVar("T")


class ActiveRecordMixin:
    async def _insert_before(cls, database: BaseStorage):
        pass

    async def _insert_after(cls, database: BaseStorage):
        pass

    @classmethod
    async def _get(cls, database: BaseStorage, identifier: str | UUID):
        pass

    async def _delete_before(self, database: BaseStorage):
        pass

    async def _delete_after(self, database: BaseStorage):
        pass

    async def _update_before(self, database: BaseStorage, source: dict | None = None):
        pass

    async def _update_after(self, database: BaseStorage):
        pass

    async def insert(self, database: BaseStorage) -> None:
        await self._insert_before(database)
        await database.insert([self])
        await self._insert_after(database)

    @classmethod
    async def create(cls: type[T], database: BaseStorage, source: dict) -> T:
        model = cls(**source)
        await model.insert(database)
        return model

    @classmethod
    async def get(cls: type[T], database: BaseStorage, identifier: str | UUID) -> T:
        return await cls._get(database, identifier)

    @classmethod
    async def get_all(cls: type[T], database: BaseStorage) -> list[T]:
        return await database.get_all(cls)

    async def delete(self, database: BaseStorage) -> None:
        await self._delete_before(database)
        await database.delete([self])
        await self._delete_after(database)

    async def update(self, database: BaseStorage, source: dict | None = None) -> None:
        await self._update_before(database, source)

        if source:
            self.merge(source)

        await database.update([self])
        await self._update_after(database)
