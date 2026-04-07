from django.urls import path
from .views import *

urlpatterns = [
    # Auth
    path("login", LoginView.as_view(), name="login"),
    path("register", RegisterView.as_view(), name="register"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("token/refresh", CustomRefreshToken.as_view(), name="token-refresh"),
    path("activate-account/<str:token>", ActivateUserView.as_view(), name="activate-account"),

    # Profile (existing)
    path("profile", UserProfileDetailView.as_view(), name="profile"),

    # Password
    path("password/change", PasswordChangeView.as_view(), name="password-change"),
    path("password/forgot", PasswordForgotView.as_view(), name="password-forgot"),
    path("password/reset-confirm/<str:token>", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("token/blacklist", BlacklistAccessTokenView.as_view(), name="token-blacklist"),

    # Onboarding & extended profile
    path("onboarding", OnboardingUpdateView.as_view(), name="onboarding-update"),
    path("profile/edit", EditProfileView.as_view(), name="profile-edit"),
    path("profile/picture", UploadProfilePictureView.as_view(), name="profile-picture-upload"),
    path("profile/picture/delete", DeleteProfilePictureView.as_view(), name="profile-picture-delete"),
    path("user-profile", UserProfileDetailView.as_view(), name="user-profile-detail"),

    # Preferences
    path("preferences", UserPreferencesView.as_view(), name="user-preferences"),
    path("fcm-token", SaveFCMTokenView.as_view(), name="fcm-token"),
]
