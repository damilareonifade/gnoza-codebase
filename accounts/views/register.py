from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from rest_framework import serializers

from gnoza.response import Created, Accepted
from gnoza.views import ResponseCode
from accounts.serializers import RegisterSerializer
from accounts.models import UserToken, TokenPurpose
from drf_spectacular.utils import extend_schema, OpenApiResponse
from accounts.mailer import send_activation_email
from gnoza.exceptions import NotFound, BadRequest
from accounts.models import User


class RegisterView(APIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save(is_active=False)
            _, raw_token = UserToken.create_for_user(
                user, purpose=TokenPurpose.ACCOUNT_ACTIVATION, hours=24
            )
            try:
                send_activation_email(user, raw_token)
            except Exception:
                pass
        return Created(ResponseCode.REGISTER_SUCCESS, serializer.data)


class ActivateUserView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.Serializer

    @extend_schema(
        responses={200: OpenApiResponse(description="Account activated successfully")},
    )
    def get(self, request, token: str):
        token_obj = UserToken.verify(token, purpose=TokenPurpose.ACCOUNT_ACTIVATION)
        if token_obj is None:
            raise BadRequest("Invalid or expired activation link.")
        user = token_obj.user
        user.is_active = True
        user.save(update_fields=["is_active"])
        token_obj.used = True
        token_obj.save(update_fields=["used"])
        return Accepted(ResponseCode.ACCOUNT_ACTIVATED)
