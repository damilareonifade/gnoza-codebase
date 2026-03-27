from rest_framework.response import Response
from .status import HttpStatus


class _BaseResponse(Response):
    status_code_value: int
    success: bool

    def __init__(self, message: str = "", data=None, **kwargs):
        payload = {
            "status_code": self.status_code_value,
            "success": self.success,
            "message": message,
            "data": data,
        }
        super().__init__(data=payload, status=self.status_code_value, **kwargs)


# ---------------------------------------------------------------------------
# 2xx Success
# ---------------------------------------------------------------------------

class Ok(_BaseResponse):
    status_code_value = HttpStatus.OK
    success = True


class Created(_BaseResponse):
    status_code_value = HttpStatus.CREATED
    success = True


class Accepted(_BaseResponse):
    status_code_value = HttpStatus.ACCEPTED
    success = True


class NoContent(Response):
    def __init__(self, **kwargs):
        super().__init__(data=None, status=HttpStatus.NO_CONTENT, **kwargs)


class Pagination(Response):
    def __init__(self, message: str, data: dict, **kwargs):
        payload = {
            "status_code": HttpStatus.OK,
            "success": True,
            "message": message,
            "data": data,
        }
        super().__init__(data=payload, status=HttpStatus.OK, **kwargs)


# ---------------------------------------------------------------------------
# 4xx Client errors
# ---------------------------------------------------------------------------

class BadRequest(_BaseResponse):
    status_code_value = HttpStatus.BAD_REQUEST
    success = False


class Unauthorized(_BaseResponse):
    status_code_value = HttpStatus.UNAUTHORIZED
    success = False


class Forbidden(_BaseResponse):
    status_code_value = HttpStatus.FORBIDDEN
    success = False


class NotFound(_BaseResponse):
    status_code_value = HttpStatus.NOT_FOUND
    success = False


class Conflict(_BaseResponse):
    status_code_value = HttpStatus.CONFLICT
    success = False


class PreconditionFailed(_BaseResponse):
    status_code_value = HttpStatus.PRECONDITION_FAILED
    success = False


class UnprocessableEntity(_BaseResponse):
    status_code_value = HttpStatus.UNPROCESSABLE_ENTITY
    success = False


# ---------------------------------------------------------------------------
# 5xx Server errors
# ---------------------------------------------------------------------------

class ServiceUnavailable(_BaseResponse):
    status_code_value = HttpStatus.SERVICE_UNAVAILABLE
    success = False
