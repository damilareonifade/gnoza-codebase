## Project Name: Gnoza

# Project description: GnozaAI is a personalized news and events aggregation backend that clusters content from multiple sources, delivers AI-powered analysis and chat, and surfaces trending articles and nearby events tailored to user preferences.
## Folder & File Structure

Never put all logic in a single `views.py`, `serializers.py`, or `models.py`. Split every logical unit into its own file, then re-export from `__init__.py`.

```
app_name/
├── models/
│   ├── __init__.py       # re-exports all models
│   ├── user.py
│   ├── profile.py
│   ├── token.py
│   └── images.py
├── views/
│   ├── __init__.py       # re-exports all views
│   ├── login.py
│   ├── register.py
│   ├── profile.py
│   ├── password.py
│   └── logout.py
├── serializers/
│   ├── __init__.py       # re-exports all serializers
│   ├── login.py
│   ├── profile.py
│   ├── password.py
│   └── images.py
├── managers.py
├── permissions.py
├── mailer.py
├── signals.py
└── urls.py
```

The `__init__.py` files exist only to re-export — keep them clean:
```python
# views/__init__.py
from .login import LoginView, CustomRefreshToken
from .register import RegisterView, CheckUsernameView
from .logout import LogoutView
from .profile import ProfileViews, UpdateUserImage
from .password import PasswordView, PasswordForgotView, PasswordResetView, PasswordConfirmView, BlacklistAccessToken
```

The core Django project config folder follows the same split pattern:
```
projectname/
├── settings/
│   └── __init__.py       # all settings in one file loaded via dotenv
├── response.py           # all HTTP response classes
├── exceptions.py         # all custom exception classes
├── status.py             # HttpStatus definitions
├── models.py             # abstract base models (e.g. TimestampedModel)
├── views.py              # ResponseCode helper
└── utils.py              # shared utilities
```

---

## Views

- Use `APIView` as the default base class
- Use `GenericAPIView` when you need a `serializer_class` on the class level with DRF's generic behaviour
- Use `CreateAPIView` only for simple create-only endpoints
- One view class (or at most two closely related classes) per file
- Always pass `context={"request": request}` to serializers that may need the request

```python
# views/register.py
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import IntegrityError, transaction
from django.core.cache import cache

from findproduct.response import Ok
from findproduct.exceptions import NotFound
from ..serializers import RegisterSerializer


class RegisterView(APIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid(raise_exception=True):
            try:
                with transaction.atomic():
                    user = serializer.save(is_active=False)
                    return Ok("Registration Successful", serializer.data)
            except IntegrityError:
                raise NotFound("A user with this email exists already")
```

```python
# views/profile.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404

from findproduct.response import Ok, NoContent
from findproduct.exceptions import NotFound
from ..permissions import IsOwnerOrReadOnly
from ..serializers import ProfileSerializer
from ..models import Profile


class ProfileViews(APIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(Profile, user=request.user)
        serializer = self.serializer_class(profile)
        return Ok("User Profile", serializer.data)

    def put(self, request, *args, **kwargs):
        profile = get_object_or_404(Profile, user=request.user)
        serializer = self.serializer_class(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.check_object_permissions(request, profile)
        serializer.save()
        return Ok("User Profile Updated successfully", serializer.data)

    def delete(self, request, *args, **kwargs):
        profile = get_object_or_404(Profile, user=request.user)
        self.check_object_permissions(request, profile)
        profile.delete()
        request.user.delete()
        return NoContent()
```

---

## Responses

Never return raw `Response(...)` from DRF. Always use the response classes from `<projectname>/response.py`.

Every response follows the shape:
```json
{
  "status_code": 200,
  "success": true,
  "message": "Human readable message",
  "data": {}
}
```

**Available response classes:**

| Class | HTTP Code | When to use |
|---|---|---|
| `Ok` | 200 | Successful GET / PUT |
| `Created` | 201 | Successful resource creation |
| `Accepted` | 202 | Async action triggered (e.g. email sent) |
| `NoContent` | 204 | Successful DELETE with no body |
| `BadRequest` | 400 | Invalid input, failed validation |
| `Unauthorized` | 401 | Auth credentials invalid |
| `NotFound` | 404 | Resource does not exist |
| `Conflict` | 409 | Duplicate resource |
| `PreconditionFailed` | 412 | State precondition not met |
| `UnprocessableEntity` | 422 | Validation passed but logic failed |
| `ServiceUnavailable` | 503 | External service down |
| `Pagination` | 200 | Paginated list results |

Usage:
```python
from findproduct.response import Ok, Created, Accepted, NoContent, BadRequest, NotFound

return Ok("Login Successful", serializer.data)
return Created("Post created", serializer.data)
return Accepted("Verification email sent")
return NoContent()                            # no message needed for deletes
return BadRequest(serializer.errors)
return NotFound("User not found")
```

---

## Exceptions

Never raise Django or DRF built-in exceptions directly. Use the custom exception classes from `<projectname>/exceptions.py`. These map to the same HTTP codes as the response classes.

```python
from findproduct.exceptions import (
    NotFound,
    BadRequest,
    AuthenticationFailed,
    InactiveAccountException,
    Conflict,
    PermissionDenied,
    ServiceUnavailable,
)

# Raise when a record doesn't exist
raise NotFound("Post not found")

# Raise inside serializer.validate() for bad input
raise BadRequest("Email already registered")

# Raise when credentials fail
raise AuthenticationFailed("Invalid email or password.")

# Raise when the account isn't activated yet
raise InactiveAccountException("Account is inactive.")
```

**Exceptions vs Response classes:**
- Raise **exceptions** inside serializers, service functions, helpers — anywhere that isn't directly returning from a view method
- Return **response classes** directly from view methods (`def get`, `def post`, etc.)

---

## Serializers

- One serializer (or closely related group) per file
- Field-level validation goes in `validate_<field>` methods — raise `BadRequest` (not DRF's `ValidationError`)
- Cross-field validation and side effects (token generation, sending email) go in `validate()`
- `create()` and `update()` override only when the default behaviour isn't sufficient
- Always `exclude` sensitive fields (`password`, `is_superuser`, `user_permissions`, `groups`) rather than using `fields = "__all__"`
- Mark `password` as `write_only=True`, `id` as `read_only=True`

```python
class RegisterSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=True)
    is_active = serializers.BooleanField(read_only=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise BadRequest("A user with this email exists already")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance

    class Meta:
        model = User
        exclude = ("groups", "created_at", "updated_at", "is_superuser",
                   "is_admin", "is_staff", "user_permissions")
```

For serializers that return tokens (login), build the token in `validate()` and expose as `read_only` fields:
```python
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, write_only=True)
    password = serializers.CharField(required=True, write_only=True)
    token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)

    def validate(self, attrs):
        # authenticate, generate tokens, update attrs
        ...
        return attrs
```

---

## Models

- All models use **UUID primary keys** — never auto-increment integers
- Extend `TimestampedModel` for any model that needs `created_at` / `updated_at`
- Post-save signal functions live at the bottom of the model file they relate to, not in a separate `signals.py`
- Connect signals at module level (bottom of file), not inside `AppConfig.ready()`
- Never allow `email` to be changed after creation — enforce in `save()`

```python
import uuid
from django.db import models
from findproduct.models import TimestampedModel


class SomeModel(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ...

    class Meta:
        db_table = "some_model"
        ordering = ("-updated_at",)
        verbose_name = "Some Model"
        verbose_name_plural = "Some Models"

    def __str__(self):
        return f"{self.id}"
```

Auto-create related records via `post_save` signals, not in views or serializers:
```python
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)
```

---

## URLs

- Each app has its own `urls.py`
- Import all views via `from .views import *` (the `__init__.py` controls what's exposed)
- No trailing slash on non-detail routes, trailing slash only on routes with sub-paths

```python
from django.urls import path
from .views import *

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("register", RegisterView.as_view(), name="register"),
    path("activate-account/", ActivateUser.as_view(), name="activate-account"),
]
```

Root `urls.py` namespaces each app under a versioned prefix:
```python
path("api/v1/auth/", include("accounts.urls")),
path("api/v1/search/", include("channels.urls")),
```
