from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from gnoza.response import Ok, Created, NoContent, BadRequest, NotFound
from content.models import ContentCluster
from feed.serializers import ContentClusterSerializer
from ..models import Bookmark


class BookmarkListView(APIView):
    """GET /api/v1/interactions/bookmarks — list the user's bookmarked clusters."""
    permission_classes = [IsAuthenticated]
    serializer_class = ContentClusterSerializer

    def get(self, request):
        bookmarks = (
            Bookmark.objects.filter(user=request.user)
            .select_related("cluster")
            .prefetch_related("cluster__sources__raw_content")
            .order_by("-created_at")
        )
        clusters = [b.cluster for b in bookmarks]
        data = ContentClusterSerializer(clusters, many=True, context={"request": request}).data
        return Ok("Bookmarks", {"count": len(data), "bookmarks": data})


class BookmarkToggleView(APIView):
    """POST /api/v1/interactions/bookmarks/toggle — add or remove a bookmark."""
    permission_classes = [IsAuthenticated]
    serializer_class = ContentClusterSerializer

    def post(self, request):
        cluster_id = request.data.get("cluster_id") or request.data.get("id")
        if not cluster_id:
            return BadRequest("cluster_id is required.")
        try:
            cluster = ContentCluster.objects.get(id=cluster_id)
        except ContentCluster.DoesNotExist:
            return NotFound("Cluster not found.")

        bookmark, created = Bookmark.objects.get_or_create(
            user=request.user, cluster=cluster
        )
        if not created:
            bookmark.delete()
            return Ok("Removed from bookmarks", {"is_bookmarked": False})
        return Created("Bookmarked", {"is_bookmarked": True})


class BookmarkCheckView(APIView):
    """POST /api/v1/interactions/bookmarks/check — check if a cluster is bookmarked."""
    permission_classes = [IsAuthenticated]
    serializer_class = ContentClusterSerializer

    def post(self, request):
        cluster_id = request.data.get("cluster_id") or request.data.get("id")
        if not cluster_id:
            return BadRequest("cluster_id is required.")
        is_bookmarked = Bookmark.objects.filter(
            user=request.user, cluster__id=cluster_id
        ).exists()
        return Ok("Bookmark status", {"is_bookmarked": is_bookmarked})


class BookmarkDeleteView(APIView):
    """POST /api/v1/interactions/bookmarks/delete — explicitly delete a bookmark."""
    permission_classes = [IsAuthenticated]
    serializer_class = ContentClusterSerializer

    def post(self, request):
        cluster_id = request.data.get("cluster_id") or request.data.get("id")
        if not cluster_id:
            return BadRequest("cluster_id is required.")
        deleted, _ = Bookmark.objects.filter(
            user=request.user, cluster__id=cluster_id
        ).delete()
        if not deleted:
            return NotFound("Bookmark not found.")
        return Ok("Bookmark removed")
