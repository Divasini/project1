from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth import get_current_user
from routers.ideas import make_summary, check_access

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/", response_model=schemas.DashboardOut)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # My ideas
    my_ideas = db.query(models.Idea).filter(
        models.Idea.author_id == current_user.id
    ).order_by(models.Idea.created_at.desc()).all()

    total_likes = sum(len(idea.likes) for idea in my_ideas)
    total_views = sum(idea.views for idea in my_ideas)

    # Bookmarked ideas (could belong to anyone)
    bookmarks = db.query(models.Bookmark).filter(
        models.Bookmark.user_id == current_user.id
    ).order_by(models.Bookmark.id.desc()).all()
    bookmarked_ideas = [bm.idea for bm in bookmarks if bm.idea is not None]

    # Build public-shaped idea dict — correctly reflects ownership/access for ANY idea
    def to_public(idea):
        is_owner, has_access, _ = check_access(idea, current_user, db)
        return {
            "id": idea.id,
            "title": idea.title,
            "category": idea.category,
            "summary": make_summary(idea.problem),
            "cover_image_url": idea.cover_image_url,
            "status": idea.status,
            "views": idea.views,
            "author_id": idea.author_id,
            "author": idea.author,
            "like_count": len(idea.likes),
            "is_owner": is_owner,
            "has_access": has_access,
            "created_at": idea.created_at,
        }

    # Pending access requests for ideas I own (people wanting access)
    pending = db.query(models.AccessRequest).join(models.Idea).filter(
        models.Idea.author_id == current_user.id,
        models.AccessRequest.status == "pending"
    ).order_by(models.AccessRequest.created_at.desc()).all()

    pending_out = [{
        "id": r.id,
        "idea_id": r.idea_id,
        "status": r.status,
        "message": r.message,
        "requester": r.requester,
        "idea_title": r.idea.title,
        "created_at": r.created_at,
    } for r in pending]

    # ── Build real notifications feed ──
    notifications = []

    # 1. Likes received on my ideas (each Like row -> one notification)
    for idea in my_ideas:
        for like in idea.likes:
            liker = db.query(models.User).filter(models.User.id == like.user_id).first()
            if liker and liker.id != current_user.id:
                notifications.append({
                    "type": "like",
                    "icon": "❤️",
                    "title": f"{liker.name} liked your idea",
                    "subtitle": idea.title,
                    "created_at": idea.created_at,  # Like model has no timestamp; fallback to idea time
                })

    # 2. Access requests received (pending) on my ideas
    for r in pending:
        notifications.append({
            "type": "access_request",
            "icon": "🔓",
            "title": f"{r.requester.name} requested access",
            "subtitle": r.idea.title,
            "created_at": r.created_at,
        })

    # 3. My own access requests that got accepted/rejected
    my_requests = db.query(models.AccessRequest).filter(
        models.AccessRequest.requester_id == current_user.id,
        models.AccessRequest.status.in_(["accepted", "rejected"])
    ).order_by(models.AccessRequest.created_at.desc()).limit(10).all()

    for r in my_requests:
        if r.status == "accepted":
            notifications.append({
                "type": "access_accepted",
                "icon": "✅",
                "title": "Your access request was accepted",
                "subtitle": r.idea.title,
                "created_at": r.created_at,
            })
        else:
            notifications.append({
                "type": "access_rejected",
                "icon": "❌",
                "title": "Your access request was declined",
                "subtitle": r.idea.title,
                "created_at": r.created_at,
            })

    # Sort all notifications by most recent first, limit to 15
    notifications.sort(key=lambda n: n["created_at"], reverse=True)
    notifications = notifications[:15]

    return {
        "total_ideas":      len(my_ideas),
        "total_likes":      total_likes,
        "total_views":      total_views,
        "total_bookmarks":  len(bookmarked_ideas),
        "recent_ideas":     [to_public(i) for i in my_ideas[:5]],
        "bookmarked_ideas": [to_public(i) for i in bookmarked_ideas[:10]],
        "pending_requests": pending_out,
        "notifications":    notifications,
    }