from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone, timedelta
from database import get_db
import models, schemas
from auth import get_current_user, get_current_user_optional
from upload_utils import save_image, delete_image

router = APIRouter(prefix="/ideas", tags=["Ideas"])


# ── Helper: build a short teaser summary from the problem statement ──
def make_summary(problem: str, length: int = 110) -> str:
    if not problem:
        return ""
    text = problem.strip()
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "..."


# ── Helper: check if a user has access to full idea details ──
# NOTE: Access request gating removed — all idea details are now public.
# is_owner is still tracked (used for edit/delete permission checks elsewhere).
def check_access(idea: models.Idea, user, db: Session):
    """Returns (is_owner, has_access, request_status). has_access is always True now."""
    is_owner = (user is not None and idea.author_id == user.id)
    return is_owner, True, None


# ── GET ALL IDEAS (Public listing — summary only) ───────────────
@router.get("/", response_model=schemas.PaginatedIdeas)
def get_ideas(
    category: Optional[str] = Query(None),
    search:   Optional[str] = Query(None),
    page:     int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    query = db.query(models.Idea).filter(models.Idea.status == "published")

    if category:
        query = query.filter(models.Idea.category == category)
    if search:
        query = query.filter(
            models.Idea.title.ilike(f"%{search}%") |
            models.Idea.problem.ilike(f"%{search}%") |
            models.Idea.tags.ilike(f"%{search}%")
        )

    total = query.count()

    ideas = (
        query.order_by(models.Idea.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = []
    for idea in ideas:
        is_owner, has_access, _ = check_access(idea, current_user, db)

        liked = False
        bookmarked = False
        if current_user:
            liked = db.query(models.Like).filter(
                models.Like.user_id == current_user.id,
                models.Like.idea_id == idea.id
            ).first() is not None

            bookmarked = db.query(models.Bookmark).filter(
                models.Bookmark.user_id == current_user.id,
                models.Bookmark.idea_id == idea.id
            ).first() is not None

        result.append({
    "id": idea.id,
    "title": idea.title,
    "category": idea.category,
    "summary": make_summary(idea.problem),
    "problem": idea.problem,
    "cover_image_url": idea.cover_image_url,
            "status": idea.status,
            "views": idea.views,
            "author_id": idea.author_id,
            "author": idea.author,
            "like_count": len(idea.likes),
            "comment_count": len(idea.comments),
            "share_count": idea.share_count,
            "liked": liked,
            "bookmarked": bookmarked,
            "is_owner": is_owner,
            "has_access": has_access,
            "created_at": idea.created_at,
        })

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


# ── GET TRENDING IDEAS ────────────────────────
@router.get("/trending", response_model=list[schemas.IdeaPublicOut])
def get_trending_ideas(
    limit: int = Query(default=10, le=30),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Returns top trending published ideas scored by:
      score = (likes × 3) + (bookmarks × 2) + (views × 1)
    With time decay — ideas older than 30 days get a reduced score.
    Ideas from the last 7 days get a 1.5× freshness boost.
    """
    now = datetime.now(timezone.utc)
    ideas = db.query(models.Idea).filter(models.Idea.status == "published").all()

    def trending_score(idea):
        likes     = len(idea.likes)
        bookmarks = len(idea.bookmarks)
        views     = idea.views

        base_score = (likes * 3) + (bookmarks * 2) + (views * 1)

        # Time decay
        created = idea.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        age_days = (now - created).days

        if age_days <= 7:
            multiplier = 1.5   # Fresh boost
        elif age_days <= 30:
            multiplier = 1.0   # Normal
        else:
            multiplier = max(0.1, 1.0 - (age_days - 30) * 0.02)  # Decay

        return base_score * multiplier

    sorted_ideas = sorted(ideas, key=trending_score, reverse=True)[:limit]

    result = []
    for idea in sorted_ideas:
        is_owner, has_access, _ = check_access(idea, current_user, db)

        liked = False
        bookmarked = False
        if current_user:
            liked = db.query(models.Like).filter(
                models.Like.user_id == current_user.id,
                models.Like.idea_id == idea.id
            ).first() is not None
            bookmarked = db.query(models.Bookmark).filter(
                models.Bookmark.user_id == current_user.id,
                models.Bookmark.idea_id == idea.id
            ).first() is not None

        result.append({
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
            "comment_count": len(idea.comments),
            "share_count": idea.share_count,
            "liked": liked,
            "bookmarked": bookmarked,
            "is_owner": is_owner,
            "has_access": has_access,
            "created_at": idea.created_at,
        })
    return result


# ── GET SINGLE IDEA (Full details if owner/access granted, else locked) ──
@router.get("/{idea_id}", response_model=schemas.IdeaOut)
def get_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # View count increment (only count non-owner views)
    is_owner, has_access, req_status = check_access(idea, current_user, db)
    if not is_owner:
        idea.views += 1
        db.commit()
        db.refresh(idea)

    unlocked = is_owner or has_access

    return {
        "id": idea.id,
        "title": idea.title,
        "category": idea.category,
        "problem":       idea.problem if unlocked else None,
        "solution":      idea.solution if unlocked else None,
        "target":        idea.target if unlocked else "",
        "revenue_model": idea.revenue_model if unlocked else "",
        "tech_stack":    idea.tech_stack if unlocked else "",
        "tags":          idea.tags,
        "cover_image_url": idea.cover_image_url,
        "status": idea.status,
        "views": idea.views,
        "author_id": idea.author_id,
        "author": idea.author,
        "like_count": len(idea.likes),
        "comment_count": len(idea.comments),
        "share_count": idea.share_count,
        "is_owner": is_owner,
        "has_access": unlocked,
        "request_status": req_status,
        "created_at": idea.created_at,
    }


# ── CREATE IDEA ───────────────────────────────
@router.post("/", response_model=schemas.IdeaOut)
def create_idea(
    idea_data: schemas.IdeaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    new_idea = models.Idea(**idea_data.dict(), author_id=current_user.id)
    db.add(new_idea)
    db.commit()
    db.refresh(new_idea)

    return {
        "id": new_idea.id,
        "title": new_idea.title,
        "category": new_idea.category,
        "problem": new_idea.problem,
        "solution": new_idea.solution,
        "target": new_idea.target,
        "revenue_model": new_idea.revenue_model,
        "tech_stack": new_idea.tech_stack,
        "tags": new_idea.tags,
        "cover_image_url": new_idea.cover_image_url,
        "status": new_idea.status,
        "views": new_idea.views,
        "author_id": new_idea.author_id,
        "author": new_idea.author,
        "like_count": 0,
        "comment_count": 0,
        "share_count": 0,
        "is_owner": True,
        "has_access": True,
        "request_status": None,
        "created_at": new_idea.created_at,
    }


# ── UPDATE IDEA ───────────────────────────────
@router.put("/{idea_id}")
def update_idea(
    idea_id: int,
    updates: schemas.IdeaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your idea")

    for key, value in updates.dict().items():
        setattr(idea, key, value)
    db.commit()
    db.refresh(idea)
    return {"message": "Idea updated successfully"}


# ── UPLOAD IDEA COVER IMAGE ────────────────────
@router.post("/{idea_id}/upload-cover")
async def upload_cover_image(
    idea_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your idea")

    new_url = await save_image(file, "covers")

    # Clean up the old cover image (if any)
    old_url = idea.cover_image_url
    if old_url:
        delete_image(old_url)

    idea.cover_image_url = new_url
    db.commit()
    db.refresh(idea)
    return {"message": "Cover image uploaded", "cover_image_url": new_url}


# ── DELETE IDEA ───────────────────────────────
@router.delete("/{idea_id}")
def delete_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your idea")

    db.delete(idea)
    db.commit()
    return {"message": "Idea deleted successfully"}


@router.post("/{idea_id}/like")
def toggle_like(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    existing_like = db.query(models.Like).filter(
        models.Like.user_id == current_user.id,
        models.Like.idea_id == idea_id
    ).first()

    if existing_like:
        db.delete(existing_like)
        db.commit()
        db.refresh(idea)
        return {"message": "Unliked", "liked": False, "likes": len(idea.likes)}
    else:
        new_like = models.Like(user_id=current_user.id, idea_id=idea_id)
        db.add(new_like)
        db.commit()
        db.refresh(idea)
        return {"message": "Liked", "liked": True, "likes": len(idea.likes)}


# ── BOOKMARK / UNBOOKMARK ─────────────────────
@router.post("/{idea_id}/bookmark")
def toggle_bookmark(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    existing = db.query(models.Bookmark).filter(
        models.Bookmark.user_id == current_user.id,
        models.Bookmark.idea_id == idea_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"message": "Bookmark removed", "bookmarked": False}
    else:
        new_bm = models.Bookmark(user_id=current_user.id, idea_id=idea_id)
        db.add(new_bm)
        db.commit()
        return {"message": "Bookmarked", "bookmarked": True}


# ── SHARE IDEA (tracks share count — called when link is copied) ──
@router.post("/{idea_id}/share")
def share_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    idea.share_count = (idea.share_count or 0) + 1
    db.commit()
    db.refresh(idea)
    return {"message": "Share recorded", "share_count": idea.share_count}


# ── GET COMMENTS FOR AN IDEA ──────────────────
@router.get("/{idea_id}/comments", response_model=list[schemas.IdeaCommentOut])
def get_comments(
    idea_id: int,
    db: Session = Depends(get_db)
):
    idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    comments = (
        db.query(models.IdeaComment)
        .filter(models.IdeaComment.idea_id == idea_id)
        .order_by(models.IdeaComment.created_at.asc())
        .all()
    )

    return [
        {
            "id": c.id,
            "body": c.body,
            "user": c.user,
            "created_at": c.created_at,
        }
        for c in comments
    ]


# ── POST A COMMENT ON AN IDEA ─────────────────
@router.post("/{idea_id}/comments", response_model=schemas.IdeaCommentOut)
def create_comment(
    idea_id: int,
    data: schemas.IdeaCommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    new_comment = models.IdeaComment(
        body=data.body,
        idea_id=idea_id,
        user_id=current_user.id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return {
        "id": new_comment.id,
        "body": new_comment.body,
        "user": new_comment.user,
        "created_at": new_comment.created_at,
    }


# ── DELETE A COMMENT (own comment only) ───────
@router.delete("/{idea_id}/comments/{comment_id}")
def delete_comment(
    idea_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    comment = db.query(models.IdeaComment).filter(
        models.IdeaComment.id == comment_id,
        models.IdeaComment.idea_id == idea_id
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your comment")

    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted"}


# ── REQUEST ACCESS TO FULL IDEA DETAILS ───────
@router.post("/{idea_id}/request-access")
def request_access(
    idea_id: int,
    data: schemas.AccessRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    if idea.author_id == current_user.id:
        raise HTTPException(status_code=400, detail="You already own this idea")

    existing = db.query(models.AccessRequest).filter(
        models.AccessRequest.idea_id == idea_id,
        models.AccessRequest.requester_id == current_user.id
    ).first()

    if existing:
        if existing.status == "accepted":
            raise HTTPException(status_code=400, detail="You already have access to this idea")
        raise HTTPException(status_code=400, detail=f"Request already {existing.status}")

    req = models.AccessRequest(
        idea_id=idea_id,
        requester_id=current_user.id,
        message=data.message,
        status="pending"
    )
    db.add(req)
    db.commit()
    return {"message": "Access request sent", "status": "pending"}


# ── GET ACCESS REQUESTS FOR MY IDEAS (Owner view) ─
@router.get("/requests/incoming", response_model=list[schemas.AccessRequestOut])
def get_incoming_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    requests = db.query(models.AccessRequest).join(models.Idea).filter(
        models.Idea.author_id == current_user.id,
        models.AccessRequest.status == "pending"
    ).order_by(models.AccessRequest.created_at.desc()).all()

    result = []
    for r in requests:
        result.append({
            "id": r.id,
            "idea_id": r.idea_id,
            "status": r.status,
            "message": r.message,
            "requester": r.requester,
            "idea_title": r.idea.title,
            "created_at": r.created_at,
        })
    return result


# ── ACCEPT / REJECT ACCESS REQUEST ────────────
@router.post("/requests/{request_id}/respond")
def respond_to_request(
    request_id: int,
    decision: str,  # "accept" or "reject"
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    req = db.query(models.AccessRequest).filter(models.AccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.idea.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your idea")

    if decision not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Decision must be 'accept' or 'reject'")

    req.status = "accepted" if decision == "accept" else "rejected"
    db.commit()
    return {"message": f"Request {req.status}", "status": req.status}