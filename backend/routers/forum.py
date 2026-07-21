from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth import get_current_user
from upload_utils import save_image, delete_image

router = APIRouter(prefix="/forum", tags=["Forum"])


# ── GET ALL THREADS ───────────────────────────
@router.get("/", response_model=list[schemas.ThreadOut])
def get_threads(db: Session = Depends(get_db)):
    threads = db.query(models.Thread).order_by(models.Thread.created_at.desc()).all()
    for t in threads:
        t.reply_count = len(t.replies)
    return threads


# ── CREATE THREAD ─────────────────────────────
@router.post("/", response_model=schemas.ThreadOut)
def create_thread(
    data: schemas.ThreadCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    thread = models.Thread(**data.dict(), author_id=current_user.id)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    thread.reply_count = 0
    return thread


# ── UPLOAD IMAGE FOR A THREAD ──────────────────
@router.post("/{thread_id}/upload-image")
async def upload_thread_image(
    thread_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    thread = db.query(models.Thread).filter(models.Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your post")

    new_url = await save_image(file, "forum")

    # Clean up the old image (if any) to avoid orphaned files
    old_url = thread.image_url
    if old_url:
        delete_image(old_url)

    thread.image_url = new_url
    db.commit()
    db.refresh(thread)
    return {"message": "Image uploaded", "image_url": new_url}


# ── GET SINGLE THREAD + REPLIES ───────────────
@router.get("/{thread_id}")
def get_thread(thread_id: int, db: Session = Depends(get_db)):
    thread = db.query(models.Thread).filter(models.Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread.reply_count = len(thread.replies)

    return {
        "thread": schemas.ThreadOut.model_validate(thread),
        "replies": [schemas.ReplyOut.model_validate(r) for r in thread.replies]
    }


# ── POST REPLY ────────────────────────────────
@router.post("/{thread_id}/reply", response_model=schemas.ReplyOut)
def post_reply(
    thread_id: int,
    data: schemas.ReplyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    thread = db.query(models.Thread).filter(models.Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    reply = models.Reply(
        body      = data.body,
        thread_id = thread_id,
        author_id = current_user.id
    )
    db.add(reply)
    db.commit()
    db.refresh(reply)
    return reply


# ── DELETE THREAD ─────────────────────────────
@router.delete("/{thread_id}")
def delete_thread(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    thread = db.query(models.Thread).filter(models.Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your thread")

    db.delete(thread)
    db.commit()
    return {"message": "Thread deleted"}