from datetime import datetime
from functools import reduce
from pathlib import Path
from typing import Any
from uuid import UUID

from aiotinydb import AIOJSONStorage, AIOTinyDB
from tinydb import Query as TDBQuery
from tinydb import where
from tinydb.operations import delete
from tinydb.table import Document as TinyDBDocument
from tinydb.table import Table
from tinydb_serialization import SerializationMiddleware, Serializer

from flowdapt.lib.database.base import (
    BaseStorage,
    BinaryExpression,
    Document,
    Expression,
    ExpressionVisitor,
    FieldExpression,
    LiteralExpression,
    Operator,
    Query,
    SortDirection,
    UnaryExpression,
    VariadicExpression,
)
from flowdapt.lib.database.utils import get_nested_field
from flowdapt.lib.utils.misc import UNDEFINED


class DatetimeSerializer(Serializer):
    OBJ_CLASS = datetime

    def encode(self, obj: datetime) -> str:
        return obj.isoformat()

    def decode(self, s: str) -> datetime:
        return datetime.fromisoformat(s)


class UUIDSerializer(Serializer):
    OBJ_CLASS = UUID

    def encode(self, obj: UUID) -> str:
        return str(obj)

    def decode(self, s: str) -> UUID:
        return UUID(s)


def _make_binary_handler(operator: Operator):
    def _handler(self, expression: Expression):
        return self.apply_operator(
            expression.left.accept(self),
            self.binary_operator_mappings[operator],
            self.get_right_operand(expression.right),
        )

    return _handler


def _not_in_binary_handler(self, expression: Expression):
    return ~self.apply_operator(
        expression.left.accept(self),
        "__contains__",
        self.get_right_operand(expression.right),
    )


class TinyDBExpressionVisitor(ExpressionVisitor):
    binary_operator_mappings = {
        Operator.EQ: "__eq__",
        Operator.NE: "__ne__",
        Operator.GT: "__gt__",
        Operator.LT: "__lt__",
        Operator.GE: "__ge__",
        Operator.LE: "__le__",
        Operator.IN: "__contains__",
        Operator.AND: "__and__",
        Operator.OR: "__or__",
    }

    binary_operator_handlers = {
        op: _make_binary_handler(op) for op in binary_operator_mappings.keys()
    }
    binary_operator_handlers[Operator.NOT_IN] = _not_in_binary_handler

    variadic_operator_mappings = {
        Operator.ANY: "any",
        Operator.ALL: "any",
    }

    join_operator_mappings = {
        Operator.ANY: "__or__",
        Operator.ALL: "__and__",
    }

    def visit_unary(self, expression: UnaryExpression) -> Any:
        match expression.operator:
            case Operator.NOT:
                return ~expression.operand.accept(self)
            case Operator.EXISTS:
                return expression.operand.accept(self).exists()
            case _:
                raise ValueError(f"Unsupported operator: {expression.operator}")

    def visit_binary(self, expression: BinaryExpression) -> Any:
        return self.binary_operator_handlers[expression.operator](self, expression)

    def visit_variadic(self, expression: VariadicExpression) -> Any:
        operands = [operand.accept(self) for operand in expression.operands]
        left, *right = operands
        operator = self.get_mapped_operator(expression.operator, self.variadic_operator_mappings)
        join_operator = self.get_mapped_operator(expression.operator, self.join_operator_mappings)

        return reduce(
            lambda acc, operand: getattr(acc, join_operator)(
                self.apply_operator(left, operator, operand)
            ),
            right,
            self.apply_operator(left, operator, right[0]),
        )

    def visit_field(self, expression: FieldExpression) -> Any:
        return reduce(lambda query, field: query[field], expression.__fields__, TDBQuery())

    def visit_literal(self, expression: LiteralExpression) -> Any:
        return expression.value

    @staticmethod
    def get_mapped_operator(operator: str, operator_mappings: dict) -> str:
        return operator_mappings.get(operator)

    @staticmethod
    def apply_operator(left_operand: Any, operator: str, right_operand: Any) -> Any:
        return getattr(left_operand, operator)(right_operand)

    def get_right_operand(self, operand: Any) -> Any:
        return operand.accept(self) if isinstance(operand, Expression) else operand


class TinyDBStorage(BaseStorage):
    """
    TinyDB storage implementation for disk based document database.

    :param path: Path to database file. If not provided, database will be created in
    the application directory at`db.json`.
    """

    def __init__(
        self,
        path: str = UNDEFINED,
        json_encoders: dict[str, Serializer] | None = None,
    ):
        super().__init__()

        if path is not UNDEFINED:
            self._path = path
        else:
            from flowdapt.lib.config import get_app_dir

            self._path = str((get_app_dir() or Path.cwd()) / "db.json")

        self._json_encoders = json_encoders or {}

    def _build_storage(self):
        storage = SerializationMiddleware(AIOJSONStorage)

        storage.register_serializer(DatetimeSerializer(), "datetime")
        storage.register_serializer(UUIDSerializer(), "uuid")

        for key, serializer in self._json_encoders.items():
            storage.register_serializer(serializer, key)

        return storage

    def _get_visitor(self) -> ExpressionVisitor:
        return TinyDBExpressionVisitor()

    def _get_collection(self, document: Document) -> Table:
        collection_name = self._get_collection_name(document)
        return self._db.table(collection_name)

    def _serialize_document(self, document: Document) -> TinyDBDocument:
        dump = document.dump(exclude_id=False)
        doc_id = dump.pop("_doc_id_")
        return TinyDBDocument(dump, doc_id=doc_id.int)

    def _deserialize_document(
        self, document_type: type[Document], doc_id: int, data: dict
    ) -> Document:
        return document_type.load({"_doc_id_": UUID(int=doc_id), **data})

    async def current_revision_id(self) -> str | None:
        if revision_doc := self._db.table("_migrate").get(doc_id=0):
            return revision_doc["revision_id"]
        return None

    async def set_revision_id(self, revision_id: str) -> None:
        self._db.table("_migrate").upsert(TinyDBDocument({"revision_id": revision_id}, doc_id=0))

    async def start(self) -> None:
        self._db = await AIOTinyDB(self._path, storage=self._build_storage()).__aenter__()

    async def stop(self) -> None:
        await self._db.__aexit__(None, None, None)

    async def _insert(self, documents: list[Document]) -> None:
        for document in documents:
            collection = self._get_collection(document)
            doc = self._serialize_document(document)
            collection.insert(doc)

    async def _delete(self, documents: list[Document]) -> None:
        for document in documents:
            collection = self._get_collection(document)
            collection.remove(doc_ids=[document._doc_id_.int])

    async def _update(self, documents: list[Document]) -> None:
        for document in documents:
            collection = self._get_collection(document)
            collection.update(self._serialize_document(document), doc_ids=[document._doc_id_.int])

    async def _find(
        self,
        document_type: type[Document],
        query: Query,
        project: list[str] | None = None,
        limit: int = -1,
        skip: int = 0,
        sort: tuple[str, SortDirection] | None = None,
    ) -> list[Document]:
        tiny_query = query.accept(self._visitor)
        collection = self._get_collection(document_type)
        documents = collection.search(tiny_query)

        if sort:
            field, direction = sort
            documents = sorted(
                documents,
                key=lambda x: get_nested_field(x, field),
                reverse=direction == SortDirection.DESC,
            )

        documents = documents[skip : skip + limit if limit > 0 else None]

        if project:
            documents = [
                {k: v for k, v in doc.items() if k in project or k == "_doc_id_"}
                for doc in documents
            ]

        return [self._deserialize_document(document_type, doc.doc_id, doc) for doc in documents]

    async def _get(self, document_type: type[Document], document_uid: UUID) -> Document | None:
        collection = self._get_collection(document_type)
        result = collection.get(doc_id=document_uid.int)

        if not result:
            return None

        return self._deserialize_document(document_type, result.doc_id, result)

    async def _get_all(self, document_type: type[Document]) -> list[Document]:
        collection = self._get_collection(document_type)
        documents = collection.all()

        return [self._deserialize_document(document_type, doc.doc_id, doc) for doc in documents]

    async def list_collections(self) -> list[str]:
        return list(self._db.tables())

    async def create_collection(self, name: str):
        if name not in self._db.tables():
            # Insert empty doc and delete after to force creation of table
            doc_id = self._db.table(name).insert({})
            self._db.table(name).remove(doc_ids=[doc_id])

    async def drop_collection(self, name: str):
        if name in self._db.tables():
            self._db.drop_table(name)

    async def add_field(self, collection: str, field: str, default: Any = None):
        self._db.table(collection).update({field: default}, ~(where(field).exists()))

    async def drop_field(self, collection: str, field: str):
        self._db.table(collection).update(delete(field), where(field).exists())

    async def rename_field(self, collection: str, field: str, new_name: str):
        self._db.table(collection).update({new_name: TDBQuery()[field]}, where(field).exists())
        self._db.table(collection).update(delete(field), where(field).exists())

    async def add_index(self, collection: str, field: str, unique: bool = False):
        pass

    async def drop_index(self, collection: str, field: str):
        pass
