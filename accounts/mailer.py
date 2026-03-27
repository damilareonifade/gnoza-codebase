from django.core.mail import send_mail
from django.conf import settings


def send_activation_email(user, token: str) -> None:
    subject = "Activate Your GnozaAI Account"
    activation_url = f"http://localhost:8000/api/v1/auth/activate-account/{token}"
    message = (
        f"Hi {user.first_name or user.email},\n\n"
        f"Thank you for registering on GnozaAI!\n\n"
        f"Please click the link below to activate your account:\n{activation_url}\n\n"
        f"This link expires in 24 hours.\n\n"
        f"— The GnozaAI Team"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset_email(user, token: str) -> None:
    subject = "Reset Your GnozaAI Password"
    reset_url = f"http://localhost:8000/api/v1/auth/password/reset-confirm/{token}"
    message = (
        f"Hi {user.first_name or user.email},\n\n"
        f"We received a request to reset your GnozaAI password.\n\n"
        f"Click the link below to set a new password:\n{reset_url}\n\n"
        f"This link expires in 1 hour. If you did not request a password reset, "
        f"please ignore this email.\n\n"
        f"— The GnozaAI Team"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
