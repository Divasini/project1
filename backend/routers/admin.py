from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth import get_admin_user
from upload_utils import delete_image

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── STATS OVERVIEW ─────────────────────────────
@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    total_users   = db.query(models.User).count()
    total_ideas   = db.query(models.Idea).count()
    total_threads = db.query(models.Thread).count()
    total_likes   = db.query(models.Like).count()
    banned_users  = db.query(models.User).filter(models.User.is_banned == True).count()
    draft_ideas   = db.query(models.Idea).filter(models.Idea.status == "draft").count()

    return {
        "total_users":   total_users,
        "total_ideas":   total_ideas,
        "total_threads": total_threads,
        "total_likes":   total_likes,
        "banned_users":  banned_users,
        "draft_ideas":   draft_ideas,
    }


# ── GET ALL USERS ──────────────────────────────
@router.get("/users", response_model=list[schemas.UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


# ── BAN / UNBAN USER ───────────────────────────
@router.post("/users/{user_id}/ban")
def toggle_ban(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        raise HTTPException(status_code=403, detail="Cannot ban another admin")

    user.is_banned = not user.is_banned
    db.commit()
    action = "banned" if user.is_banned else "unbanned"
    return {"message": f"User {action}", "is_banned": user.is_banned}


# ── TOGGLE ADMIN ───────────────────────────────
@router.post("/users/{user_id}/toggle-admin")
def toggle_admin(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=403, detail="Cannot change your own admin status")

    user.is_admin = not user.is_admin
    db.commit()
    return {"message": f"Admin status {'granted' if user.is_admin else 'revoked'}", "is_admin": user.is_admin}


# ── DELETE USER ────────────────────────────────
@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        raise HTTPException(status_code=403, detail="Cannot delete another admin")
    if user.id == admin.id:
        raise HTTPException(status_code=403, detail="Cannot delete yourself")

    # Clean up avatar file
    if user.avatar_url:
        delete_image(user.avatar_url)

    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


# ── GET ALL IDEAS (admin view) ──────────────────
@router.get("/ideas")
def get_all_ideas(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    ideas = db.query(models.Idea).order_by(models.Idea.created_at.desc()).all()
    return [{
        "id":         idea.id,
        "title":      idea.title,
        "category":   idea.category,
        "status":     idea.status,
        "views":      idea.views,
        "like_count": len(idea.likes),
        "author_id":  idea.author_id,
        "author_name": idea.author.name,
        "author_email": idea.author.email,
        "created_at": idea.created_at,
    } for idea in ideas]


# ── DELETE ANY IDEA ────────────────────────────
@router.delete("/ideas/{idea_id}")
def admin_delete_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    if idea.cover_image_url:
        delete_image(idea.cover_image_url)

    db.delete(idea)
    db.commit()
    return {"message": "Idea deleted"}


# ── TOGGLE IDEA STATUS (publish/draft) ─────────
@router.post("/ideas/{idea_id}/toggle-status")
def toggle_idea_status(
    idea_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user)
):
    idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    idea.status = "draft" if idea.status == "published" else "published"
    db.commit()
    return {"message": f"Idea {idea.status}", "status": idea.status}