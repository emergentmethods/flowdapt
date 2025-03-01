import asyncio
from typing import Any, Callable
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DocumentTooLarge, OperationFailure
from pymongo.errors import WriteError as PymongoWriteError

from flowdapt.lib.database.base import (
    BaseStorage,
    BinaryExpression,
    Document,
    ExpressionVisitor,
    FieldExpression,
    LiteralExpression,
    Operator,
    Query,
    SortDirection,
    UnaryExpression,
    VariadicExpression,
)
from flowdapt.lib.database.errors import WriteError


class SpecialCharHandler:
    def __init__(self, replacements: dict[str, str]):
        self.replacements = replacements
        self.inverse_replacements = {v: k for k, v in replacements.items()}

    def replace(self, text: str) -> str:
        for old, new in self.replacements.items():
            text = text.replace(old, new)
        return text

    def restore(self, text: str) -> str:
        for old, new in self.inverse_replacements.items():
            text = text.replace(old, new)
        return text

    def process_obj(self, obj: Any, func: Callable[[str], str]) -> Any:
        if isinstance(obj, dict):
            return {func(k): self.process_obj(v, func) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.process_obj(v, func) for v in obj]
        elif isinstance(obj, str):
            return func(obj)
        else:
            return obj

    def escape(self, obj: Any) -> Any:
        return self.process_obj(obj, self.replace)

    def unescape(self, obj: Any) -> Any:
        return self.process_obj(obj, self.restore)


SPECIAL_CHARS = SpecialCharHandler(
    {
        ".": "__dot__",
        "$": "__ds__",
    }
)


class MongoExpressionVisitor(ExpressionVisitor):
    binary_operator_mappings = {
        Operator.EQ: "$eq",
        Operator.NE: "$ne",
        Operator.LT: "$lt",
        Operator.LE: "$lte",
        Operator.GT: "$gt",
        Operator.GE: "$gte",
        Operator.IN: "$in",
        Operator.NOT_IN: "$nin",
        Operator.AND: "$and",
        Operator.OR: "$or",
    }

    variadic_operator_mappings = {
        Operator.ANY: "$or",
        Operator.ALL: "$and",
    }

    def visit_unary(self, expression: UnaryExpression) -> Any:
        if expression.operator == Operator.NOT:
            if isinstance(expression.operand, BinaryExpression):
                return {
                    expression.operand.left.accept(self): {
                        "$not": {
                            self.get_mapped_operator(
                                expression.operand.operator,
                                self.binary_operator_mappings,
                            ): expression.operand.right.accept(self)
                        }
                    }
                }
            elif isinstance(expression.operand, VariadicExpression):
                field = expression.operand.operands[0].accept(self)
                return {
                    "$nor": [
                        {f"{field}": {key: value}}
                        for operand in expression.operand.operands[1:]
                        for key, value in operand.accept(self).items()
                    ]
                }
            elif isinstance(expression.operand, FieldExpression):
                return {expression.operand.accept(self): {"$not": {"$exists": True}}}
            elif isinstance(expression.operand, LiteralExpression):
                return {"$ne": expression.operand.accept(self)}
            else:
                raise ValueError(f"Unsupported expression in unary operand: {expression.operand}")
        elif expression.operator == Operator.EXISTS:
            return {expression.operand.accept(self): {"$exists": True}}
        else:
            raise ValueError(f"Unsupported unary operator: {expression.operator}")

    def visit_binary(self, expression: BinaryExpression) -> Any:
        if expression.operator not in self.binary_operator_mappings:
            raise ValueError(f"Unsupported binary operator: {expression.operator}")

        match expression.operator:
            case Operator.AND:
                return {
                    "$and": [
                        expression.left.accept(self),
                        expression.right.accept(self),
                    ]
                }
            case Operator.OR:
                return {"$or": [expression.left.accept(self), expression.right.accept(self)]}
            case _:
                return {
                    expression.left.accept(self): {
                        self.get_mapped_operator(
                            expression.operator, self.binary_operator_mappings
                        ): expression.right.accept(self)
                    }
                }

    def visit_variadic(self, expression: VariadicExpression) -> Any:
        if expression.operator not in self.variadic_operator_mappings:
            raise ValueError(f"Unsupported variadic operator: {expression.operator}")

        operands = [operand.accept(self) for operand in expression.operands]
        conditions = [
            {f"{operands[0]}": {"$elemMatch": {key: value}}}
            for operand in operands[1:]
            for key, value in operand.items()
        ]

        return {
            self.get_mapped_operator(
                expression.operator, self.variadic_operator_mappings
            ): conditions
        }

    def visit_field(self, expression: FieldExpression) -> Any:
        return ".".join(SPECIAL_CHARS.escape(expression.__fields__))

    def visit_literal(self, expression: LiteralExpression) -> Any:
        return expression.value

    @staticmethod
    def get_mapped_operator(operator: str, operator_mappings: dict) -> str:
        return operator_mappings.get(operator)


class MongoDBStorage(BaseStorage):
    """
    MongoDB storage implementation.

    :param uri: MongoDB connection URI. Typically in the form of
        ``mongodb://<username>:<password>@<host>:<port>/<database>``.
    :param db_name: Name of the database to use.
    :param kwargs: Additional keyword arguments to pass to the
        :class:`motor.motor_asyncio.AsyncIOMotorClient` constructor.
    """

    def __init__(self, uri: str, db_name: str, **kwargs):
        super().__init__()

        self._uri = uri
        self._db_name = db_name
        self._kwargs = kwargs

        self._client: AsyncIOMotorClient
        self._db: AsyncIOMotorCollection

    def _get_visitor(self) -> ExpressionVisitor:
        return MongoExpressionVisitor()

    def _get_collection(self, document: Document) -> AsyncIOMotorCollection:
        collection_name = self._get_collection_name(document)
        return self._db[collection_name]

    async def start(self) -> None:
        self._kwargs["uuidRepresentation"] = (
            self._kwargs.pop("uuidRepresentation", None) or "standard"
        )

        self._client = AsyncIOMotorClient(self._uri, **self._kwargs)
        self._db = self._client[self._db_name]

    async def stop(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

        self._db = None

    async def current_revision_id(self) -> str | None:
        if doc := (await self._db["_migrate"].find_one({"_id": 0})):
            return doc.get("revision_id", None)
        return None

    async def set_revision_id(self, revision_id: str) -> None:
        await self._db["_migrate"].replace_one(
            {"_id": 0}, {"_id": 0, "revision_id": revision_id}, upsert=True
        )

    @staticmethod
    def _serialize_doc(document: Document) -> dict:
        dump = document.dump(exclude_id=False)
        doc_id = dump.pop("_doc_id_")
        return {"_id": doc_id, **SPECIAL_CHARS.escape(dump)}

    @staticmethod
    def _deserialize_doc(document_type: type[Document], data: dict) -> dict:
        return document_type.load({"_doc_id_": data.pop("_id"), **SPECIAL_CHARS.unescape(data)})

    async def _insert(self, documents: list[Document]) -> None:
        async def __insert(doc):
            collection = self._get_collection(doc)
            try:
                await collection.insert_one(self._serialize_doc(doc))
            except DocumentTooLarge as e:
                raise WriteError(str(e))

        await asyncio.gather(*[__insert(doc) for doc in documents])

    async def _delete(self, documents: list[Document]) -> None:
        async def __delete(doc):
            collection = self._get_collection(doc)
            await collection.delete_one({"_id": doc._doc_id_})

        await asyncio.gather(*[__delete(doc) for doc in documents])

    async def _update(self, documents: list[Document]) -> None:
        async def __update(doc):
            collection = self._get_collection(doc)
            try:
                await collection.replace_one({"_id": doc._doc_id_}, self._serialize_doc(doc))
            except PymongoWriteError as e:
                raise WriteError(str(e))

        await asyncio.gather(*[__update(doc) for doc in documents])

    async def _find(
        self,
        document_type: type[Document],
        query: Query,
        project: list[str] | None = None,
        limit: int = -1,
        skip: int = 0,
        sort: tuple[str, SortDirection] | None = None,
    ) -> list[Document]:
        filter_query = query.accept(self._visitor)
        collection = self._get_collection(document_type)

        cursor = collection.find(filter_query, projection=project)

        if sort:
            field, direction = sort
            cursor = cursor.sort(field, ASCENDING if direction == SortDirection.ASC else DESCENDING)

        if skip:
            cursor = cursor.skip(skip)

        if limit and limit > 0:
            cursor = cursor.limit(limit)

        return [self._deserialize_doc(document_type, data) async for data in cursor]

    async def _get(self, document_type: type[Document], document_uid: UUID) -> Document | None:
        collection = self._get_collection(document_type)
        result = await collection.find_one({"_id": document_uid})

        if not result:
            return None

        return self._deserialize_doc(document_type, result)

    async def _get_all(self, document_type: type[Document]) -> list[Document]:
        collection = self._get_collection(document_type)
        cursor = collection.find({})

        return [self._deserialize_doc(document_type, data) for data in (await cursor.to_list(None))]

    async def list_collections(self) -> list[str]:
        return await self._db.list_collection_names()

    async def create_collection(self, name: str):
        try:
            await self._db.validate_collection(name)
        except OperationFailure:
            await self._db.create_collection(name)

    async def drop_collection(self, name: str):
        try:
            await self._db.validate_collection(name)
            await self._db.drop_collection(name)
        except OperationFailure:
            pass

    async def add_field(self, collection: str, field: str, default: Any = None):
        await self._db[collection].update_many(
            {field: {"$exists": False}}, {"$set": {field: default}}
        )

    async def drop_field(self, collection: str, field: str):
        await self._db[collection].update_many({field: {"$exists": True}}, {"$unset": {field: 1}})

    async def rename_field(self, collection: str, field: str, new_name: str):
        await self._db[collection].update_many(
            {field: {"$exists": True}}, {"$rename": {field: new_name}}
        )

    async def add_index(self, collection: str, field: str, unique: bool = False):
        await self._db[collection].create_index([(field, ASCENDING)], unique=unique)

    async def drop_index(self, collection: str, field: str):
        await self._db[collection].drop_index(field)
