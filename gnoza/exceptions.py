from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler
from rest_framework.response import Response
from .status import HttpStatus


# ---------------------------------------------------------------------------
# Custom exception classes
# ---------------------------------------------------------------------------

class NotFound(APIException):
    status_code = HttpStatus.NOT_FOUND
    default_code = "not_found"

    def __init__(self, detail="Resource not found."):
        super().__init__(detail=detail)


class BadRequest(APIException):
    status_code = HttpStatus.BAD_REQUEST
    default_code = "bad_request"

    def __init__(self, detail="Bad request."):
        super().__init__(detail=detail)


class AuthenticationFailed(APIException):
    status_code = HttpStatus.UNAUTHORIZED
    default_code = "authentication_failed"

    def __init__(self, detail="Authentication credentials were invalid."):
        super().__init__(detail=detail)


class InactiveAccountException(APIException):
    status_code = HttpStatus.UNAUTHORIZED
    default_code = "inactive_account"

    def __init__(self, detail="Account is inactive. Please verify your email."):
        super().__init__(detail=detail)


class Conflict(APIException):
    status_code = HttpStatus.CONFLICT
    default_code = "conflict"

    def __init__(self, detail="A conflict occurred."):
        super().__init__(detail=detail)


class PermissionDenied(APIException):
    status_code = HttpStatus.FORBIDDEN
    default_code = "permission_denied"

    def __init__(self, detail="You do not have permission to perform this action."):
        super().__init__(detail=detail)


class PreconditionFailed(APIException):
    status_code = HttpStatus.PRECONDITION_FAILED
    default_code = "precondition_failed"

    def __init__(self, detail="Precondition failed."):
        super().__init__(detail=detail)


class UnprocessableEntity(APIException):
    status_code = HttpStatus.UNPROCESSABLE_ENTITY
    default_code = "unprocessable_entity"

    def __init__(self, detail="Unprocessable entity."):
        super().__init__(detail=detail)


class ServiceUnavailable(APIException):
    status_code = HttpStatus.SERVICE_UNAVAILABLE
    default_code = "service_unavailable"

    def __init__(self, detail="External service is unavailable. Try again later."):
        super().__init__(detail=detail)


# ---------------------------------------------------------------------------
# Global exception handler — converts all errors to our standard shape
# ---------------------------------------------------------------------------

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        detail = response.data.get("detail", response.data)
        if hasattr(detail, "code"):
            message = str(detail)
        elif isinstance(detail, dict):
            message = detail
        elif isinstance(detail, list):
            message = detail[0] if len(detail) == 1 else detail
        else:
            message = str(detail)

        response.data = {
            "status_code": response.status_code,
            "success": False,
            "message": message,
            "data": None,
        }

    return response
