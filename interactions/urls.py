from django.urls import path
from .views import *

urlpatterns = [
    # Bookmarks
    path("bookmarks", BookmarkListView.as_view(), name="bookmark-list"),
    path("bookmarks/toggle", BookmarkToggleView.as_view(), name="bookmark-toggle"),
    path("bookmarks/check", BookmarkCheckView.as_view(), name="bookmark-check"),
    path("bookmarks/delete", BookmarkDeleteView.as_view(), name="bookmark-delete"),

    # Likes
    path("likes", LikeListView.as_view(), name="like-list"),
    path("likes/toggle", LikeToggleView.as_view(), name="like-toggle"),
    path("likes/check", LikeCheckView.as_view(), name="like-check"),

    # Comments
    path("comments", CommentsListView.as_view(), name="comment-list"),
    path("comments/add", CommentAddView.as_view(), name="comment-add"),
    path("comments/<int:comment_id>", CommentDeleteView.as_view(), name="comment-delete"),
    path("comments/<int:comment_id>/like", CommentLikeToggleView.as_view(), name="comment-like"),
]
