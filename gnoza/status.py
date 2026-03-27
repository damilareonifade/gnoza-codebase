from http import HTTPStatus


class HttpStatus:
    OK = HTTPStatus.OK.value                          # 200
    CREATED = HTTPStatus.CREATED.value                # 201
    ACCEPTED = HTTPStatus.ACCEPTED.value              # 202
    NO_CONTENT = HTTPStatus.NO_CONTENT.value          # 204
    BAD_REQUEST = HTTPStatus.BAD_REQUEST.value        # 400
    UNAUTHORIZED = HTTPStatus.UNAUTHORIZED.value      # 401
    FORBIDDEN = HTTPStatus.FORBIDDEN.value            # 403
    NOT_FOUND = HTTPStatus.NOT_FOUND.value            # 404
    CONFLICT = HTTPStatus.CONFLICT.value              # 409
    PRECONDITION_FAILED = HTTPStatus.PRECONDITION_FAILED.value  # 412
    UNPROCESSABLE_ENTITY = HTTPStatus.UNPROCESSABLE_ENTITY.value  # 422
    INTERNAL_SERVER_ERROR = HTTPStatus.INTERNAL_SERVER_ERROR.value  # 500
    SERVICE_UNAVAILABLE = HTTPStatus.SERVICE_UNAVAILABLE.value  # 503
