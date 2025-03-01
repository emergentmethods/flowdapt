from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from contextvars import ContextVar
from enum import Enum
from functools import reduce
from typing import Any
from uuid import UUID, uuid4

from pydantic import PrivateAttr

from flowdapt.lib.database.utils import classproperty, find_immutable_fields, merge
from flowdapt.lib.utils.model import BaseModel


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class Operator(str, Enum):
    EQ = "=="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    IN = "in"
    NOT_IN = "not in"
    MATCHES = "matches"
    EXISTS = "exists"
    AND = "and"
    OR = "or"
    NOT = "not"
    ANY = "any_of"
    ALL = "all_of"


class ExpressionVisitor(ABC):
    @abstractmethod
    def visit_unary(self, expression: UnaryExpression) -> Any:
        """
        Visit a unary expression.

        :param expression: The unary expression to visit.
        """
        ...

    @abstractmethod
    def visit_binary(self, expression: BinaryExpression) -> Any:
        """
        Visit a binary expression.

        :param expression: The binary expression to visit.
        """
        ...

    @abstractmethod
    def visit_variadic(self, expression: VariadicExpression) -> Any:
        """
        Visit a variadic expression.

        :param expression: The variadic expression to visit.
        """
        ...

    @abstractmethod
    def visit_field(self, expression: FieldExpression) -> Any:
        """
        Visit a field expression.

        :param expression: The field expression to visit.
        """
        ...

    @abstractmethod
    def visit_literal(self, expression: LiteralExpression) -> Any:
        """
        Visit a literal expression.

        :param expression: The literal expression to visit.
        """
        ...

    def visit_query(self, query: Query) -> Any:
        """
        Visit a query.

        :param query: The query to visit.
        """
        return query.expression.accept(self)


class Expression(ABC):
    @abstractmethod
    def accept(self, visitor: ExpressionVisitor) -> Any:
        """
        Accept a visitor.

        :param visitor: The visitor to accept.
        """
        pass


class LiteralExpression(Expression):
    def __init__(self, value: Any):
        self.value = value

    def __str__(self) -> str:
        return f"{self.value}"

    def __repr__(self) -> str:
        return f"<LiteralExpression {self}>"

    def accept(self, visitor: ExpressionVisitor) -> Any:
        return visitor.visit_literal(self)


class FieldExpression(Expression):
    def __init__(self, *fields: str):
        self.__fields__ = list(fields)

    def __getattr__(self, field: str) -> FieldExpression:
        if field.startswith("__") and field.endswith("__"):
            return super().__getattr__(field)
        elif field in self.__dict__:
            return super().__getattr__(field)

        return FieldExpression(*self.__fields__, field)

    def __getitem__(self, field: str) -> FieldExpression:
        return FieldExpression(*self.__fields__, field)

    def __eq__(self, other: Expression) -> Query:
        return Query(BinaryExpression(Operator.EQ, self, other))

    def __ne__(self, other: Expression) -> Query:
        return Query(BinaryExpression(Operator.NE, self, other))

    def __lt__(self, other: Expression) -> Query:
        return Query(BinaryExpression(Operator.LT, self, other))

    def __le__(self, other: Expression) -> Query:
        return Query(BinaryExpression(Operator.LE, self, other))

    def __gt__(self, other: Expression) -> Query:
        return Query(BinaryExpression(Operator.GT, self, other))

    def __ge__(self, other: Expression) -> Query:
        return Query(BinaryExpression(Operator.GE, self, other))

    def __invert__(self) -> Query:
        return Query(UnaryExpression(Operator.NOT, self))

    def exists(self) -> Query:
        """
        Matches documents where the field exists.
        """
        return Query(UnaryExpression(Operator.EXISTS, self))

    def matches(self, other: re.Pattern | str) -> Query:
        """
        Matches documents where the field matches a regular expression.

        :param other: The regular expression to match.
        """
        if isinstance(other, str):
            other = re.compile(other)
        else:
            assert isinstance(other, re.Pattern)

        return Query(BinaryExpression(Operator.MATCHES, self, other))

    def is_any(self, other: list[Any]) -> Query:
        """
        Matches documents where the field value is any of the values.

        :param other: The list of values to match.
        """
        return reduce(lambda a, b: a | b, [self == value for value in other])

    def one_of(self, other: list[Any]) -> Query:
        """
        Matches documents where the array field matches any of the values.

        :param other: The list of values to match.
        """
        return Query(BinaryExpression(Operator.IN, self, other))

    def any_of(self, *others: Expression | Query) -> Query:
        """
        Matches documents where the array field matches any of the expressions.

        :param others: The expressions to match.
        """
        return Query(
            VariadicExpression(
                Operator.ANY,
                [
                    self,
                    *(other.expression if isinstance(other, Query) else other for other in others),
                ],
            )
        )

    def all_of(self, *others: Expression | Query) -> Query:
        """
        Matches documents where the array field matches all of the expressions.

        :param others: The expressions to match.
        """
        return Query(
            VariadicExpression(
                Operator.ALL,
                [
                    self,
                    *(other.expression if isinstance(other, Query) else other for other in others),
                ],
            )
        )

    def partial(self, other: dict[str, Any]) -> Query:
        """
        Matches documents where the field matches a partial document.

        :param other: The partial document to match.
        """
        if not other:
            raise ValueError("Partial document cannot be empty")

        return reduce(
            lambda a, b: a | b,
            [self[key] == value for key, value in other.items()],
        )

    def accept(self, visitor: ExpressionVisitor) -> Any:
        return visitor.visit_field(self)

    def __str__(self) -> str:
        return "::".join([*self.__fields__])

    def __repr__(self) -> str:
        return f"<FieldExpression {self}>"


class UnaryExpression(Expression):
    def __init__(self, operator: Operator, operand: Expression):
        self.operator = operator
        self.operand = operand if isinstance(operand, Expression) else LiteralExpression(operand)

    def __str__(self) -> str:
        return f"({self.operator.value} {self.operand})"

    def __repr__(self) -> str:
        return f"<UnaryExpression {self}>"

    def accept(self, visitor: ExpressionVisitor) -> Any:
        return visitor.visit_unary(self)


class BinaryExpression(Expression):
    def __init__(self, operator: Operator, left: FieldExpression, right: Expression):
        self.operator = operator
        self.left = left
        self.right = right if isinstance(right, Expression) else LiteralExpression(right)

    def __str__(self) -> str:
        return f"({self.left} {self.operator.value} {self.right})"

    def __repr__(self) -> str:
        return f"<BinaryExpression {self}>"

    def accept(self, visitor: ExpressionVisitor) -> Any:
        return visitor.visit_binary(self)


class VariadicExpression(Expression):
    def __init__(self, operator: Operator, operands: list[Expression]):
        self.operator = operator
        self.operands = [
            operand if isinstance(operand, Expression) else LiteralExpression(operand)
            for operand in operands
        ]

    def __str__(self) -> str:
        return f"({self.operator.value} {' '.join(map(str, self.operands))})"

    def __repr__(self) -> str:
        return f"<VariadicExpression {self}>"

    def accept(self, visitor: ExpressionVisitor) -> Any:
        return visitor.visit_variadic(self)


class Query:
    def __init__(self, expression: Expression):
        self.expression = expression

    def __and__(self, other: Query) -> Query:
        return Query(BinaryExpression(Operator.AND, self.expression, other.expression))

    def __or__(self, other: Query) -> Query:
        return Query(BinaryExpression(Operator.OR, self.expression, other.expression))

    def __invert__(self) -> Query:
        return Query(UnaryExpression(Operator.NOT, self.expression))

    def __str__(self) -> str:
        return f"{self.expression}"

    def __repr__(self) -> str:
        return f"<Query {self}>"

    def accept(self, visitor: ExpressionVisitor) -> Any:
        return visitor.visit_query(self)


class FieldMeta(type):
    def __getattr__(cls, field: str) -> FieldExpression:
        return FieldExpression(field)

    def __getitem__(cls, field: str) -> FieldExpression:
        return FieldExpression(field)


class Field(metaclass=FieldMeta):
    pass


class Document(BaseModel):
    _doc_id_: UUID = PrivateAttr(default_factory=uuid4)

    @classproperty
    def collection_name(cls) -> str:
        if hasattr(cls, "__collection_name__"):
            return cls.__collection_name__
        return cls.__name__

    @classproperty
    def immutable_fields(cls) -> dict[tuple, bool]:
        return find_immutable_fields(cls)

    def merge(self, patch: dict) -> None:
        """
        Merge a patch into the document.

        :param patch: The patch to merge.
        """
        if not isinstance(patch, dict):
            raise ValueError("Patch must be a dictionary")

        merge(self, patch, self.immutable_fields)

    def dump(self, exclude_id: bool = True) -> dict:
        """
        Converts the document to a dictionary.

        :param exclude_id: Whether to exclude the document ID.
        :return: The dictionary representation of the document.
        """
        if exclude_id:
            return self.model_dump()
        else:
            return {"_doc_id_": self._doc_id_, **self.model_dump()}

    @classmethod
    def load(cls, data: dict) -> Document:
        """
        Loads a document from a dictionary.

        :param data: The dictionary to load from.
        :return: The loaded document.
        """
        document_uid = data.pop("_doc_id_", uuid4())

        if not isinstance(document_uid, UUID):
            document_uid = UUID(document_uid)

        document = cls.model_validate(data)
        document._doc_id_ = document_uid

        return document


class TransactionOperation(ABC):
    def __init__(self, documents: list[Document]):
        self.documents: list[Document] = documents

    @abstractmethod
    async def commit(self, database: BaseStorage) -> None:
        """
        Performs the operation on the database.

        :param database: The database to perform the operation on.
        """
        ...

    @abstractmethod
    async def rollback(self, database: BaseStorage) -> None:
        """
        Reverts the operation on the database.

        :param database: The database to revert the operation on.
        """
        ...


class InsertOperation(TransactionOperation):
    async def commit(self, database: BaseStorage) -> None:
        await database._insert(self.documents)

    async def rollback(self, database: BaseStorage) -> None:
        await database._delete(self.documents)


class DeleteOperation(TransactionOperation):
    async def commit(self, database: BaseStorage) -> None:
        await database._delete(self.documents)

    async def rollback(self, database: BaseStorage) -> None:
        await database._insert(self.documents)


class UpdateOperation(TransactionOperation):
    async def commit(self, database: BaseStorage) -> None:
        self.prev_view = [
            await database._get(type(document), document._doc_id_) for document in self.documents
        ]
        await database._update(self.documents)

    async def rollback(self, database: BaseStorage) -> None:
        self.documents = self.prev_view
        await database._update(self.documents)


class Transaction:
    def __init__(self, database: BaseStorage, parent: Transaction | None = None):
        self.database = database
        self.parent = parent

        self._savepoint = 0 if parent is None else len(parent._operations)
        self._operations: list[TransactionOperation] = []
        self._applied: list[TransactionOperation] = []

    def add_operation(
        self, operation_type: type[TransactionOperation], documents: list[Document]
    ) -> None:
        """
        Add an operation to the transaction.

        :param operation_type: The operation type.
        :param documents: The documents to perform the operation on.
        """
        assert isinstance(operation_type, type) and issubclass(operation_type, TransactionOperation)
        self._operations.append(operation_type(documents))

    async def commit(self) -> None:
        """
        Commit the transaction.
        """
        if self.parent is not None:
            self.parent._operations.extend(self._operations[self._savepoint :])
        elif not self._applied:
            try:
                for operation in self._operations:
                    await operation.commit(self.database)
                    self._applied.append(operation)
            except Exception:
                await self.rollback()
                raise

    async def rollback(self) -> None:
        """
        Rollback the transaction.
        """
        for operation in reversed(self._applied[self._savepoint :]):
            await operation.rollback(self.database)
        del self._applied[self._savepoint :]


class BaseStorage(ABC):
    _current_transaction: ContextVar[Transaction | None] = ContextVar(
        "_current_transaction", default=None
    )

    def __init__(self):
        self._visitor: ExpressionVisitor = self._get_visitor()
        self._transaction: Transaction | None = None
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    def _get_collection_name(self, document: Document) -> str:
        return document.collection_name

    @abstractmethod
    def _get_visitor(self) -> ExpressionVisitor: ...

    @abstractmethod
    async def start(self) -> None:
        """
        Starts the storage.
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """
        Stops the storage.
        """
        ...

    @abstractmethod
    async def current_revision_id(self) -> str | None:
        """
        Get the current migration revision ID the database is on.
        """
        ...

    @abstractmethod
    async def set_revision_id(self, revision_id: str) -> None:
        """
        Update the current migration revision ID the database is on.
        """
        ...

    @abstractmethod
    async def _insert(self, documents: list[Document]) -> None: ...

    @abstractmethod
    async def _delete(self, documents: list[Document]) -> None: ...

    @abstractmethod
    async def _update(self, documents: list[Document]) -> None: ...

    @abstractmethod
    async def _find(
        self,
        document_type: type[Document],
        query: Query,
        project: list[str] | None = None,
        limit: int = -1,
        skip: int = 0,
        sort: tuple[str, SortDirection] | None = None,
    ) -> list[Document]: ...

    @abstractmethod
    async def _get(self, document_type: type[Document], document_uid: UUID) -> Document | None: ...

    @abstractmethod
    async def _get_all(self, document_type: type[Document]) -> list[Document]: ...

    @abstractmethod
    async def create_collection(self, name: str): ...

    @abstractmethod
    async def drop_collection(self, name: str): ...

    @abstractmethod
    async def add_field(self, collection: str, field: str, default: Any = None): ...

    @abstractmethod
    async def drop_field(self, collection: str, field: str): ...

    @abstractmethod
    async def rename_field(self, collection: str, field: str, new_name: str): ...

    @abstractmethod
    async def add_index(self, collection: str, field: str, unique: bool = False): ...

    @abstractmethod
    async def drop_index(self, collection: str, field: str): ...

    @abstractmethod
    async def list_collections(self) -> list[str]: ...

    async def insert(self, documents: list[Document]) -> None:
        """
        Inserts a list of documents into the storage.
        """
        if transaction := self._current_transaction.get():
            transaction.add_operation(InsertOperation, documents)
        else:
            async with self._lock:
                await self._insert(documents)

    async def delete(self, documents: list[Document]) -> None:
        """
        Deletes given a list of documents.
        """
        if transaction := self._current_transaction.get():
            transaction.add_operation(DeleteOperation, documents)
        else:
            async with self._lock:
                await self._delete(documents)

    async def update(self, documents: list[Document]) -> None:
        """
        Updates based on a list of documents.
        """
        if transaction := self._current_transaction.get():
            transaction.add_operation(UpdateOperation, documents)
        else:
            async with self._lock:
                await self._update(documents)

    async def get(self, document_type: type[Document], document_uid: UUID) -> Document | None:
        """
        Retrieves a single document by its UID.
        """
        return await self._get(document_type, document_uid)

    async def get_all(self, document_type: type[Document]) -> list[Document]:
        """
        Retrieves all documents of a given type.
        """
        return await self._get_all(document_type)

    async def find(
        self,
        document_type: type[Document],
        query: Query,
        project: list[str] | None = None,
        limit: int = -1,
        skip: int = 0,
        sort: tuple[str, SortDirection] | None = None,
    ) -> list[Document]:
        """
        Finds documents based on a query.
        """
        return await self._find(
            document_type=document_type,
            query=query,
            project=project,
            limit=limit,
            skip=skip,
            sort=sort,
        )

    async def find_one(
        self,
        document_type: type[Document],
        query: Query,
        project: list[str] | None = None,
        skip: int = 0,
        sort: tuple[str, SortDirection] | None = None,
    ) -> Document | None:
        """
        Finds a single document based on a query.
        """
        documents = await self.find(
            document_type=document_type,
            query=query,
            project=project,
            limit=1,
            skip=skip,
            sort=sort,
        )
        if documents:
            return documents[0]
        return None

    @asynccontextmanager
    async def transaction(self) -> Transaction:
        """
        Perform operations in a transaction.
        """
        if parent := self._current_transaction.get():
            transaction = Transaction(self, parent=parent)
        else:
            transaction = Transaction(self)

        token = self._current_transaction.set(transaction)
        try:
            yield transaction
            await transaction.commit()
        except Exception:
            await transaction.rollback()
            raise
        finally:
            self._current_transaction.reset(token)
