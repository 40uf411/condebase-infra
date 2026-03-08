from pathlib import Path
import re

from fastapi import HTTPException, UploadFile, status

from ..core.config import Settings

_ALLOWED_EXTENSIONS = {"jpg", "png", "gif", "webp"}
_CONTENT_TYPE_TO_EXTENSION = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


def ensure_media_directories(settings: Settings) -> None:
    avatar_directory(settings).mkdir(parents=True, exist_ok=True)


def avatar_directory(settings: Settings) -> Path:
    return Path(settings.media_dir) / "avatars"


def find_profile_picture_url(settings: Settings, subject: str | None) -> str | None:
    safe_subject = _safe_subject(subject)
    if not safe_subject:
        return None

    directory = avatar_directory(settings)
    if not directory.exists():
        return None

    candidates = []
    for entry in directory.glob(f"{safe_subject}.*"):
        extension = entry.suffix.lower().lstrip(".")
        if extension not in _ALLOWED_EXTENSIONS:
            continue
        try:
            stat = entry.stat()
        except OSError:
            continue
        candidates.append((stat.st_mtime_ns, entry.name))

    if not candidates:
        return None

    candidates.sort(reverse=True)
    _, filename = candidates[0]
    return _build_picture_url(settings=settings, filename=filename, version=candidates[0][0])


async def save_profile_picture(
    *,
    settings: Settings,
    subject: str,
    uploaded_file: UploadFile,
) -> str:
    safe_subject = _safe_subject(subject)
    if not safe_subject:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to identify user for profile picture upload",
        )

    max_bytes = settings.max_avatar_mb * 1024 * 1024
    raw = await uploaded_file.read(max_bytes + 1)
    await uploaded_file.close()

    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is too large. Maximum allowed size is {settings.max_avatar_mb} MB",
        )

    extension = _detect_image_extension(
        content=raw,
        content_type=uploaded_file.content_type,
        filename=uploaded_file.filename,
    )

    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PNG, JPG, GIF, and WEBP images are supported",
        )

    directory = avatar_directory(settings)
    directory.mkdir(parents=True, exist_ok=True)

    for existing in directory.glob(f"{safe_subject}.*"):
        try:
            existing.unlink()
        except OSError:
            pass

    destination = directory / f"{safe_subject}.{extension}"
    destination.write_bytes(raw)
    version = destination.stat().st_mtime_ns
    return _build_picture_url(settings=settings, filename=destination.name, version=version)


def _build_picture_url(*, settings: Settings, filename: str, version: int | None = None) -> str:
    base = settings.api_base_url.rstrip("/")
    url = f"{base}/media/avatars/{filename}"
    if version is None:
        return url
    return f"{url}?v={version}"


def _safe_subject(subject: str | None) -> str:
    if not subject:
        return ""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", subject.strip())
    return cleaned[:120]


def _detect_image_extension(
    *,
    content: bytes,
    content_type: str | None,
    filename: str | None,
) -> str | None:
    signature_extension = _extension_from_signature(content)
    if signature_extension is None:
        return None

    mime_extension = _CONTENT_TYPE_TO_EXTENSION.get((content_type or "").strip().lower())
    if mime_extension is not None and mime_extension != signature_extension:
        return None

    filename_extension = _extension_from_filename(filename)
    if filename_extension is not None and filename_extension != signature_extension:
        return None

    return signature_extension


def _extension_from_signature(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        return "gif"
    if len(content) >= 12 and content[0:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    return None


def _extension_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None

    extension = Path(filename).suffix.lower().lstrip(".")
    if not extension:
        return None
    if extension == "jpeg":
        return "jpg"
    if extension in _ALLOWED_EXTENSIONS:
        return extension
    return None
