"""Secure file upload validators."""
import os

from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "csv",
    "png", "jpg", "jpeg", "gif", "txt",
}

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1].lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type '.{ext}'. Allowed: "
            + ", ".join(sorted(ALLOWED_EXTENSIONS))
        )


def validate_image_extension(value):
    ext = os.path.splitext(value.name)[1].lower().lstrip(".")
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            "Unsupported image type. Allowed: " + ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))
        )


def validate_file_size(value):
    if value.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(
            f"File too large ({value.size // 1024} KB). "
            f"Maximum allowed size is {int(settings.MAX_UPLOAD_SIZE_MB)} MB."
        )


def sanitize_filename(filename):
    """Replace unsafe characters in a filename."""
    name = os.path.basename(str(filename))
    name = "".join(ch for ch in name if ch.isalnum() or ch in "._- ")
    return name or "file"
