from .login import LoginView, CustomRefreshToken
from .register import RegisterView, ActivateUserView
from .logout import LogoutView
from .password import (
    PasswordChangeView,
    PasswordForgotView,
    PasswordResetConfirmView,
    BlacklistAccessTokenView,
)
from .onboarding import (
    OnboardingUpdateView,
    EditProfileView,
    UploadProfilePictureView,
    DeleteProfilePictureView,
)
from .preferences import UserPreferencesView, UserProfileDetailView, SaveFCMTokenView

__all__ = [
    "LoginView",
    "CustomRefreshToken",
    "RegisterView",
    "ActivateUserView",
    "LogoutView",
    "PasswordChangeView",
    "PasswordForgotView",
    "PasswordResetConfirmView",
    "BlacklistAccessTokenView",
    "OnboardingUpdateView",
    "EditProfileView",
    "UploadProfilePictureView",
    "DeleteProfilePictureView",
    "UserPreferencesView",
    "UserProfileDetailView",
    "SaveFCMTokenView",
]
