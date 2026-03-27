from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from gnoza.response import Ok, Created, BadRequest, NotFound, NoContent
from content.models import ContentCluster
from ..models import Comment, CommentLike
from ..serializers import CommentSerializer


class CommentsListView(APIView):
    """GET /api/v1/interactions/comments?cluster_id=<id> — list top-level comments."""
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer

    def get(self, request):
        cluster_id = request.query_params.get("cluster_id")
        if not cluster_id:
            return BadRequest("cluster_id query param is required.")
        comments = (
            Comment.objects.filter(cluster__id=cluster_id, parent__isnull=True)
            .select_related("user", "user__preferences")
            .prefetch_related("replies__user", "replies__user__preferences", "comment_likes")
            .order_by("-created_at")
        )
        data = CommentSerializer(comments, many=True, context={"request": request}).data
        return Ok("Comments", {"count": len(data), "comments": data})


class CommentAddView(APIView):
    """POST /api/v1/interactions/comments/add — post a comment on a cluster."""
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer

    def post(self, request):
        cluster_id = request.data.get("cluster_id")
        text = request.data.get("text", "").strip()
        parent_id = request.data.get("parent_id")

        if not cluster_id:
            return BadRequest("cluster_id is required.")
        if not text:
            return BadRequest("Comment text cannot be empty.")
        if len(text) > 2000:
            return BadRequest("Comment must be 2000 characters or fewer.")

        try:
            cluster = ContentCluster.objects.get(id=cluster_id)
        except ContentCluster.DoesNotExist:
            return NotFound("Cluster not found.")

        parent = None
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id, cluster=cluster)
            except Comment.DoesNotExist:
                return NotFound("Parent comment not found.")

        comment = Comment.objects.create(
            user=request.user, cluster=cluster, text=text, parent=parent
        )
        data = CommentSerializer(comment, context={"request": request}).data
        return Created("Comment added", data)


class CommentDeleteView(APIView):
    """DELETE /api/v1/interactions/comments/<comment_id> — delete own comment."""
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer

    def delete(self, request, comment_id):
        try:
            comment = Comment.objects.get(id=comment_id, user=request.user)
        except Comment.DoesNotExist:
            return NotFound("Comment not found.")
        comment.delete()
        return NoContent()


class CommentLikeToggleView(APIView):
    """POST /api/v1/interactions/comments/<comment_id>/like — like or unlike a comment."""
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer

    def post(self, request, comment_id):
        try:
            comment = Comment.objects.get(id=comment_id)
        except Comment.DoesNotExist:
            return NotFound("Comment not found.")

        like, created = CommentLike.objects.get_or_create(
            user=request.user, comment=comment
        )
        if not created:
            like.delete()
            return Ok("Comment unliked", {"is_liked": False, "like_count": comment.comment_likes.count()})

        return Created("Comment liked", {"is_liked": True, "like_count": comment.comment_likes.count()})
