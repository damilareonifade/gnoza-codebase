from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from gnoza.response import Ok, Created, BadRequest, NotFound
from content.models import ContentCluster
from ..models import Like


class LikeToggleView(APIView):
    """POST /api/v1/interactions/likes/toggle — like or unlike a cluster."""
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=OpenApiResponse(description="Toggle like on a content cluster"))
    def post(self, request):
        cluster_id = request.data.get("cluster_id") or request.data.get("id")
        if not cluster_id:
            return BadRequest("cluster_id is required.")
        try:
            cluster = ContentCluster.objects.get(id=cluster_id)
        except ContentCluster.DoesNotExist:
            return NotFound("Cluster not found.")

        like, created = Like.objects.get_or_create(user=request.user, cluster=cluster)
        if not created:
            like.delete()
            like_count = Like.objects.filter(cluster=cluster).count()
            return Ok("Unliked", {"is_liked": False, "like_count": like_count})

        like_count = Like.objects.filter(cluster=cluster).count()
        return Created("Liked", {"is_liked": True, "like_count": like_count})


class LikeCheckView(APIView):
    """POST /api/v1/interactions/likes/check — check if a cluster is liked."""
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=OpenApiResponse(description="Check like status for a content cluster"))
    def post(self, request):
        cluster_id = request.data.get("cluster_id") or request.data.get("id")
        if not cluster_id:
            return BadRequest("cluster_id is required.")
        is_liked = Like.objects.filter(
            user=request.user, cluster__id=cluster_id
        ).exists()
        like_count = Like.objects.filter(cluster__id=cluster_id).count()
        return Ok("Like status", {"is_liked": is_liked, "like_count": like_count})


class LikeListView(APIView):
    """GET /api/v1/interactions/likes — list clusters the user has liked."""
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiResponse(description="List of liked content clusters"))
    def get(self, request):
        from feed.serializers import ContentClusterSerializer
        likes = (
            Like.objects.filter(user=request.user)
            .select_related("cluster")
            .prefetch_related("cluster__sources__raw_content")
            .order_by("-created_at")
        )
        clusters = [lk.cluster for lk in likes]
        data = ContentClusterSerializer(clusters, many=True, context={"request": request}).data
        return Ok("Liked clusters", {"count": len(data), "likes": data})
