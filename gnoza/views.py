class ResponseCode:
    """Centralised string constants for response messages."""

    # Auth
    LOGIN_SUCCESS = "Login successful."
    LOGOUT_SUCCESS = "Logged out successfully."
    REGISTER_SUCCESS = "Registration successful. Please check your email to activate your account."
    ACCOUNT_ACTIVATED = "Account activated successfully."
    TOKEN_REFRESHED = "Token refreshed."

    # Profile
    PROFILE_FETCHED = "Profile fetched successfully."
    PROFILE_UPDATED = "Profile updated successfully."
    PROFILE_DELETED = "Account deleted successfully."
    AVATAR_UPDATED = "Avatar updated successfully."

    # Password
    PASSWORD_CHANGED = "Password changed successfully."
    PASSWORD_RESET_SENT = "Password reset email has been sent."
    PASSWORD_RESET_SUCCESS = "Password has been reset successfully."

    # Generic
    SUCCESS = "Success."
    NOT_FOUND = "Resource not found."
