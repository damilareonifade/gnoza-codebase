import uuid
import os


def upload_avatar_to(instance, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    new_name = f"{uuid.uuid4()}.{ext}"
    return os.path.join("avatars", str(instance.user.id), new_name)


def generate_uid() -> str:
    return str(uuid.uuid4())
