from .login import LoginView, CustomRefreshToken
from .register import RegisterView, ActivateUserView
from .logout import LogoutView
from .profile import ProfileView, UpdateUserAvatarView
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
    "ProfileView",
    "UpdateUserAvatarView",
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
