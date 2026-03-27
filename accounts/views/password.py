from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import JSONParser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

from gnoza.response import Ok, Accepted
from gnoza.views import ResponseCode
from gnoza.exceptions import BadRequest
from accounts.serializers import (
    PasswordChangeSerializer,
    PasswordForgotSerializer,
    PasswordResetConfirmSerializer,
)
from accounts.mailer import send_password_reset_email

from drf_spectacular.utils import extend_schema, OpenApiResponse


class PasswordChangeView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser,)
    serializer_class = PasswordChangeSerializer

    @extend_schema(
        request=PasswordChangeSerializer,
        responses={200: OpenApiResponse(description="Password changed successfully")},
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Ok(ResponseCode.PASSWORD_CHANGED)


class PasswordForgotView(APIView):
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)
    serializer_class=PasswordForgotSerializer

    @extend_schema(
        request=PasswordForgotSerializer,
        responses={202: OpenApiResponse(description="Password reset email sent")},
    )
    def post(self, request):
        serializer = PasswordForgotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, raw_token = serializer.save()
        try:
            send_password_reset_email(user, raw_token)
        except Exception:
            pass
        return Accepted(ResponseCode.PASSWORD_RESET_SENT)


class PasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)
    serializer_class = PasswordResetConfirmSerializer

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(description="Password reset successful")},
    )
    def post(self, request, token: str):
        data = {**request.data, "token": token}
        serializer = PasswordResetConfirmSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Ok(ResponseCode.PASSWORD_RESET_SUCCESS)


class BlacklistAccessTokenView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser,)

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"access_token": {"type": "string"}}, "required": ["access_token"]}},
        responses={200: OpenApiResponse(description="Access token blacklisted")},
    )
    def post(self, request):
        access_token = request.data.get("access_token")
        if not access_token:
            raise BadRequest("access_token is required.")
        try:
            token = AccessToken(access_token)
            token.blacklist()
        except (TokenError, AttributeError):
            raise BadRequest("Invalid or expired access token.")
        return Ok("Access token blacklisted.")