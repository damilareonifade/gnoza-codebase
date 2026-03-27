from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import JSONParser
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from gnoza.response import Ok
from gnoza.views import ResponseCode
from accounts.serializers import LoginSerializer


class LoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Ok(ResponseCode.LOGIN_SUCCESS, serializer.data)


class CustomRefreshToken(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
        return Ok(ResponseCode.TOKEN_REFRESHED, serializer.data)
