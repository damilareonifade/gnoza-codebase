from django.urls import path
from .views import *

urlpatterns = [
    # Reminders CRUD
    path("", ReminderListCreateView.as_view(), name="reminder-list-create"),
    path("quick", QuickReminderView.as_view(), name="reminder-quick"),
    path("<uuid:pk>", ReminderDetailView.as_view(), name="reminder-detail"),
    path("<uuid:pk>/<str:action>", ReminderPauseResumeView.as_view(), name="reminder-action"),

    # Learning schedules
    path("learning", LearningScheduleListCreateView.as_view(), name="learning-list-create"),
    path("learning/<uuid:pk>", LearningScheduleDetailView.as_view(), name="learning-detail"),
    path("learning/<uuid:pk>/complete-session", CompleteSessionView.as_view(), name="learning-complete-session"),

    # Birthdays
    path("birthdays/import", BirthdayImportView.as_view(), name="birthday-import"),
    path("birthdays/upcoming", UpcomingBirthdaysView.as_view(), name="birthday-upcoming"),

    # NLP
    path("nlp", NLPReminderView.as_view(), name="reminder-nlp"),
]
