from typing import Any
from uuid import UUID

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
from flowdapt.lib.database.utils import get_nested_field


class InMemoryExpressionVisitor(ExpressionVisitor):
    def visit_unary(self, expression: UnaryExpression) -> Any:
        operand = expression.operand.accept(self)
        if expression.operator == Operator.NOT:
            return lambda doc: not operand(doc)
        elif expression.operator == Operator.EXISTS:
            return lambda doc: self._evaluate_condition(operand(doc), expression.operator, None)
        else:
            raise ValueError(f"Unsupported unary operator: {expression.operator}")

    def visit_binary(self, expression: BinaryExpression) -> Any:
        left = expression.left.accept(self)
        right = expression.right.accept(self)

        match expression.operator:
            case (
                Operator.EQ
                | Operator.NE
                | Operator.GT
                | Operator.LT
                | Operator.GE
                | Operator.LE
                | Operator.IN
                | Operator.MATCHES
                | Operator.EXISTS
            ):
                return lambda doc: self._evaluate_condition(left(doc), expression.operator, right)
            case Operator.AND:
                return lambda doc: left(doc) and right(doc)
            case Operator.OR:
                return lambda doc: left(doc) or right(doc)
            case _:
                raise ValueError(f"Unsupported binary operator: {expression.operator}")

    def visit_variadic(self, expression: VariadicExpression) -> Any:
        operands = [operand.accept(self) for operand in expression.operands]
        field_getter = operands[0]
        subqueries = operands[1:]

        if expression.operator == Operator.ANY:
            # If any of the subqueries match all of the items in the field return True
            return lambda doc: any(
                any(subquery(item) for item in field_getter(doc)) for subquery in subqueries
            )
        elif expression.operator == Operator.ALL:
            # If all of the subqueries match all of the items in the field return True
            return lambda doc: all(
                any(subquery(item) for item in field_getter(doc)) for subquery in subqueries
            )
        else:
            raise ValueError(f"Unsupported variadic operator: {expression.operator}")

    def visit_field(self, expression: FieldExpression) -> Any:
        return lambda doc: get_nested_field(doc, expression.__fields__)

    def visit_literal(self, expression: LiteralExpression) -> Any:
        return expression.value

    @staticmethod
    def _evaluate_condition(actual_value: Any, operator: Operator, value: Any) -> bool:
        match operator:
            case Operator.EQ:
                # print(actual_value == value, actual_value, value)
                return actual_value == value
            case Operator.NE:
                return actual_value != value
            case Operator.GT:
                return actual_value > value
            case Operator.LT:
                return actual_value < value
            case Operator.GE:
                return actual_value >= value
            case Operator.LE:
                return actual_value <= value
            case Operator.IN:
                return actual_value in value
            case Operator.NOT_IN:
                return actual_value not in value
            case Operator.MATCHES:
                return value.match(actual_value) is not None
            case Operator.EXISTS:
                return actual_value is not None
            case _:
                return False


class InMemoryStorage(BaseStorage):
    """
    In-memory storage implementation for testing purposes.
    Must not be used unless you know what you are doing. Data
    is not persisted between sessions.
    """

    def __init__(self):
        super().__init__()

        self._migrate_revision_id = None
        self._storage = {}  # format: {'collection': {'uid': Document}}

    def _get_visitor(self) -> ExpressionVisitor:
        return InMemoryExpressionVisitor()

    async def start(self):
        pass

    async def stop(self):
        pass

    async def current_revision_id(self) -> str | None:
        return self._migrate_revision_id

    async def set_revision_id(self, revision_id: str) -> None:
        self._migrate_revision_id = revision_id

    def _serialize_document(self, document: Document) -> dict:
        return document.dump(exclude_id=False)

    def _deserialize_document(self, document_type: type[Document], source: dict) -> Document:
        return document_type.load(source)

    async def _insert(self, documents: list[Document]) -> None:
        for doc in documents:
            collection_name = self._get_collection_name(doc)

            if collection_name not in self._storage:
                self._storage[collection_name] = {}

            self._storage[collection_name][doc._doc_id_] = self._serialize_document(doc)

    async def _delete(self, documents: list[Document]) -> None:
        for doc in documents:
            collection_name = self._get_collection_name(doc)

            if collection_name in self._storage:
                self._storage[collection_name].pop(doc._doc_id_, None)

    async def _update(self, documents: list[Document]) -> None:
        await self._insert(documents)

    async def _find(
        self,
        document_type: type[Document],
        query: Query,
        project: list[str] | None = None,
        limit: int = -1,
        skip: int = 0,
        sort: tuple[str, SortDirection] | None = None,
    ) -> list[Document]:
        collection_name = self._get_collection_name(document_type)
        documents = self._storage.get(collection_name, {})

        query_evaluator = query.accept(self._visitor)
        documents = [(doc_id, doc) for doc_id, doc in documents.items() if query_evaluator(doc)]

        if sort:
            field, direction = sort
            documents = sorted(
                documents,
                key=lambda item: get_nested_field(item[1], field),
                reverse=(direction == SortDirection.DESC),
            )

        documents = documents[skip : skip + limit if limit > 0 else None]

        if project:
            documents = [
                (doc_id, {field: get_nested_field(doc, field) for field in project})
                for doc_id, doc in documents
            ]

        return [
            self._deserialize_document(document_type, {"_doc_id_": doc_id, **doc})
            for doc_id, doc in documents
        ]

    async def _get(self, document_type: type[Document], document_uid: UUID) -> Document | None:
        collection = self._storage.get(self._get_collection_name(document_type), {})
        result = collection.get(document_uid, None)

        if not result:
            return None

        return self._deserialize_document(document_type, {"_doc_id_": document_uid, **result})

    async def _get_all(self, document_type: type[Document]) -> list[Document]:
        collection = self._storage.get(self._get_collection_name(document_type), {})
        return [
            self._deserialize_document(document_type, {"_doc_id_": k, **doc})
            for k, doc in collection.items()
        ]

    async def list_collections(self) -> list[str]:
        return list(self._storage.keys())

    async def create_collection(self, name: str):
        if name not in self._storage:
            self._storage[name] = {}

    async def drop_collection(self, name: str):
        self._storage.pop(name, None)

    async def add_field(self, collection: str, field: str, default: Any = None):
        for doc in self._storage.get(collection, {}).values():
            doc[field] = default

    async def drop_field(self, collection: str, field: str):
        for doc in self._storage.get(collection, {}).values():
            doc.pop(field, None)

    async def rename_field(self, collection: str, field: str, new_name: str):
        for doc in self._storage.get(collection, {}).values():
            doc[new_name] = doc.pop(field, None)

    async def add_index(self, collection: str, field: str, unique: bool = False):
        pass

    async def drop_index(self, collection: str, field: str):
        pass
