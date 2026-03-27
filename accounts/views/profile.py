from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404

from gnoza.response import Ok, NoContent
from gnoza.views import ResponseCode
from drf_spectacular.utils import extend_schema, OpenApiResponse
from accounts.permissions import IsOwner
from accounts.serializers import ProfileSerializer, AvatarSerializer
from accounts.models import Profile


class ProfileView(APIView):
    serializer_class = ProfileSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request):
        profile = get_object_or_404(Profile, user=request.user)
        serializer = self.serializer_class(profile, context={"request": request})
        return Ok(ResponseCode.PROFILE_FETCHED, serializer.data)

    def put(self, request):
        profile = get_object_or_404(Profile, user=request.user)
        serializer = self.serializer_class(
            profile, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Ok(ResponseCode.PROFILE_UPDATED, serializer.data)

    def delete(self, request):
        profile = get_object_or_404(Profile, user=request.user)
        user = request.user
        profile.delete()
        user.delete()
        return NoContent()


class UpdateUserAvatarView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = AvatarSerializer

    @extend_schema(request=AvatarSerializer, responses=OpenApiResponse(description="Avatar updated"))
    def patch(self, request):
        profile = get_object_or_404(Profile, user=request.user)
        serializer = AvatarSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Ok(
            ResponseCode.AVATAR_UPDATED,
            ProfileSerializer(profile, context={"request": request}).data,
        )
