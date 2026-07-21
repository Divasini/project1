import os
import uuid
from fastapi import HTTPException, UploadFile

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
AVATAR_DIR = os.path.join(UPLOAD_DIR, "avatars")
COVER_DIR  = os.path.join(UPLOAD_DIR, "covers")

os.makedirs(AVATAR_DIR, exist_ok=True)
os.makedirs(COVER_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


async def save_image(file: UploadFile, subfolder: str) -> str:
    """
    Validates and saves an uploaded image file.
    Returns the relative URL path (e.g. /uploads/avatars/xxxx.jpg) to store in the DB.
    Raises HTTPException on invalid file type or size.
    """
    # ── Validate extension ──
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # ── Validate content-type (defense in depth, browsers can lie but this adds a layer) ──
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file content type.")

    # ── Read and validate size ──
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    # ── Generate a safe random filename (never trust user-provided filenames) ──
    safe_filename = f"{uuid.uuid4().hex}{ext}"

    target_dir = AVATAR_DIR if subfolder == "avatars" else COVER_DIR
    filepath = os.path.join(target_dir, safe_filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    return f"/uploads/{subfolder}/{safe_filename}"


def delete_image(relative_url: str):
    """Deletes an old image file given its stored relative URL, ignoring errors."""
    if not relative_url or not relative_url.startswith("/uploads/"):
        return
    try:
        filepath = os.path.join(UPLOAD_DIR, relative_url.replace("/uploads/", "", 1))
        filepath = os.path.normpath(filepath)
        # Safety check: ensure we're still within UPLOAD_DIR
        if os.path.commonpath([filepath, UPLOAD_DIR]) == UPLOAD_DIR and os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"[UPLOAD CLEANUP WARNING] Could not delete {relative_url}: {e}")