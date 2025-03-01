from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel


class APIErrorModel(BaseModel):
    status_code: int = 500
    detail: str = "string"


class APIError(HTTPException):
    status_code: int = 500
    detail: str = "Internal Server Error"

    def __init__(self, status_code: Optional[int] = None, detail: Optional[str] = None, **kwargs):
        kwargs.pop("status_code", None)
        kwargs.pop("detail", None)

        super().__init__(
            status_code=status_code or self.status_code, detail=detail or self.detail, **kwargs
        )


class DatabaseConnectionError(APIError):
    status_code: int = 0
    detail: str = "Could not connect to the Database"


class MethodNotAllowedError(APIError):
    status_code: int = 405
    detail: str = "Method not allowed"


class NotAuthorizedError(APIError):
    status_code: int = 403
    detail: str = "Not authorized"


class ResourceNotFoundError(APIError):
    status_code: int = 404
    detail: str = "Resource not found"


class InvalidCredentialsError(APIError):
    status_code: int = 403
    detail: str = "Invalid credentials"


class InactiveUserError(APIError):
    status_code: int = 403
    detail: str = "Inactive user"


class InvalidJWTError(APIError):
    status_code: int = 403
    detail: str = "Invalid JWT token"


class UserNotFoundError(APIError):
    status_code: int = 404
    detail: str = "User not found"


class NonUniqueValue(APIError):
    status_code: int = 422
    detail: str = "Value does not satisfy unique constraint"


class BadRequestError(APIError):
    status_code: int = 400
    detail: str = "Bad request"
