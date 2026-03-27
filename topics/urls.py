from django.urls import path
from .views import *

urlpatterns = [
    path("", AllTopicsView.as_view(), name="topic-list"),
    path("popular", PopularTopicsView.as_view(), name="topic-popular"),
    path("saved", UserSavedTopicsView.as_view(), name="topic-saved"),
    path("bulk-save", BulkSaveTopicsView.as_view(), name="topic-bulk-save"),
    path("update", UpdateUserTopicsView.as_view(), name="topic-update"),
    path("<uuid:pk>/toggle", ToggleSaveTopicView.as_view(), name="topic-toggle"),
    path("<slug:slug>/content", TopicContentView.as_view(), name="topic-content"),
]
