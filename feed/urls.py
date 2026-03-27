from django.urls import path
from .views import PersonalizedFeedView

urlpatterns = [
    path("feed", PersonalizedFeedView.as_view(), name="personalized-feed"),
]
