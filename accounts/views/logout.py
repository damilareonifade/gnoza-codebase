from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from gnoza.response import Ok
from gnoza.views import ResponseCode
from drf_spectacular.utils import extend_schema, OpenApiResponse
from gnoza.exceptions import BadRequest


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"refresh_token": {"type": "string"}}, "required": ["refresh_token"]}},
        responses={200: OpenApiResponse(description="Logout successful")},
    )
    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            raise BadRequest("refresh_token is required.")
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            raise BadRequest("Invalid or expired refresh token.")
        return Ok(ResponseCode.LOGOUT_SUCCESS)
