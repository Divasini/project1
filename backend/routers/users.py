import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth import hash_password, verify_password, create_access_token, get_current_user
from email_utils import send_login_alert, send_welcome_email, send_verification_email, send_password_reset_email
from upload_utils import save_image, delete_image
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/users", tags=["Users"])

# Frontend URL used to build the verification link.
# In production, replace with your deployed frontend domain.
FRONTEND_URL = "http://127.0.0.1:5500/frontend"


# ── SIGNUP ────────────────────────────────────
@router.post("/signup")
@limiter.limit("5/minute")
def signup(
    request: Request,
    user_data: schemas.UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    existing = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = models.User(
        name          = user_data.name,
        email         = user_data.email,
        password_hash = hash_password(user_data.password),
        is_verified   = False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # ── Create email verification token ──
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)

    verification = models.EmailVerificationToken(
        user_id=new_user.id,
        token=token,
        expires_at=expires
    )
    db.add(verification)
    db.commit()

    verify_link = f"{FRONTEND_URL}/verify-email.html?token={token}"

    # Send verification + welcome email in background (won't block signup)
    background_tasks.add_task(send_verification_email, new_user.email, new_user.name, verify_link)
    background_tasks.add_task(send_welcome_email, new_user.email, new_user.name)

    return {
        "message": "Account created! Please check your email to verify your account before logging in.",
        "email": new_user.email
    }


# ── VERIFY EMAIL ───────────────────────────────
@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    record = db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.token == token
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="Invalid or already used verification link")

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification link has expired. Please request a new one.")

    user = db.query(models.User).filter(models.User.id == record.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    db.delete(record)  # one-time use
    db.commit()

    return {"message": "Email verified successfully", "verified": True}


# ── RESEND VERIFICATION EMAIL ──────────────────
@router.post("/resend-verification")
def resend_verification(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    # Remove old tokens for this user
    db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.user_id == current_user.id
    ).delete()

    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)

    verification = models.EmailVerificationToken(
        user_id=current_user.id,
        token=token,
        expires_at=expires
    )
    db.add(verification)
    db.commit()

    verify_link = f"{FRONTEND_URL}/verify-email.html?token={token}"
    background_tasks.add_task(send_verification_email, current_user.email, current_user.name, verify_link)

    return {"message": "Verification email sent"}


# ── LOGIN ─────────────────────────────────────
@router.post("/login", response_model=schemas.Token)
@limiter.limit("10/minute")
def login(
    request: Request,
    credentials: schemas.UserLogin,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.is_banned:
        raise HTTPException(status_code=403, detail="Your account has been suspended. Contact support.")

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="EMAIL_NOT_VERIFIED"
        )

    token = create_access_token({"user_id": user.id})

    # Track last login time
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # Send login alert email in background (won't block or fail the login)
    background_tasks.add_task(send_login_alert, user.email, user.name)

    return {"access_token": token, "token_type": "bearer", "user": user}


# ── RESEND VERIFICATION (before login — needs email, not a token) ──
@router.post("/resend-verification-by-email")
@limiter.limit("3/minute")
def resend_verification_by_email(
    request: Request,
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Don't reveal whether the email exists
        return {"message": "If this email is registered, a verification link has been sent."}

    if user.is_verified:
        return {"message": "This email is already verified. You can log in."}

    db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.user_id == user.id
    ).delete()

    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)

    verification = models.EmailVerificationToken(
        user_id=user.id,
        token=token,
        expires_at=expires
    )
    db.add(verification)
    db.commit()

    verify_link = f"{FRONTEND_URL}/verify-email.html?token={token}"
    background_tasks.add_task(send_verification_email, user.email, user.name, verify_link)

    return {"message": "If this email is registered, a verification link has been sent."}


# ── GET MY PROFILE ────────────────────────────
@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


# ── VERIFY RESET TOKEN (must come BEFORE /{user_id} so it isn't swallowed by it) ──
@router.get("/verify-reset-token")
def verify_reset_token(token: str, db: Session = Depends(get_db)):
    record = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == token
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="Invalid or already used reset link")

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This reset link has expired. Please request a new one.")

    return {"valid": True}

# ── SEARCH USERS BY NAME (for starting a new chat) ──
# NOTE: Must stay ABOVE the /{user_id} route, or FastAPI will treat
# "search" as a user_id value.
@router.get("/search/query", response_model=list[schemas.UserOut])
def search_users(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    q = q.strip()
    if len(q) < 2:
        return []

    users = db.query(models.User).filter(
        models.User.name.ilike(f"%{q}%"),
        models.User.id != current_user.id
    ).limit(8).all()

    return users


# ── GET ANY USER PROFILE ──────────────────────
@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── GET ANY USER PROFILE ──────────────────────
@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── UPDATE PROFILE ────────────────────────────
@router.put("/me/update", response_model=schemas.UserOut)
def update_profile(
    updates: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    for key, value in updates.items():
        if hasattr(current_user, key) and key not in ["id", "email", "password_hash"]:
            setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return current_user


# ── UPLOAD PROFILE AVATAR ─────────────────────
@router.post("/me/upload-avatar", response_model=schemas.UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    new_url = await save_image(file, "avatars")

    # Clean up the old avatar file (if any) to avoid orphaned files piling up
    old_url = current_user.avatar_url
    if old_url:
        delete_image(old_url)

    current_user.avatar_url = new_url
    db.commit()
    db.refresh(current_user)
    return current_user


# ── REMOVE PROFILE AVATAR ─────────────────────
@router.delete("/me/remove-avatar", response_model=schemas.UserOut)
def remove_avatar(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    old_url = current_user.avatar_url
    if old_url:
        delete_image(old_url)
    current_user.avatar_url = ""
    db.commit()
    db.refresh(current_user)
    return current_user


# ── FORGOT PASSWORD — request a reset link ────
@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(
    request: Request,
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user = db.query(models.User).filter(models.User.email == email).first()

    # Always return the same message — don't reveal whether the email exists
    generic_message = {"message": "If this email is registered, a password reset link has been sent."}

    if not user:
        return generic_message

    # Remove any old reset tokens for this user
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id
    ).delete()

    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)

    reset_token = models.PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires
    )
    db.add(reset_token)
    db.commit()

    reset_link = f"{FRONTEND_URL}/reset-password.html?token={token}"
    background_tasks.add_task(send_password_reset_email, user.email, user.name, reset_link)

    return generic_message


# ── RESET PASSWORD — set new password using the token ──
@router.post("/reset-password")
def reset_password(
    payload: dict,
    db: Session = Depends(get_db)
):
    token = payload.get("token")
    new_password = payload.get("new_password")

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and new password are required")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if len(new_password) > 72:
        raise HTTPException(status_code=400, detail="Password is too long")

    record = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == token
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="Invalid or already used reset link")

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This reset link has expired. Please request a new one.")

    user = db.query(models.User).filter(models.User.id == record.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(new_password)
    db.delete(record)  # one-time use
    db.commit()

    return {"message": "Password reset successfully. You can now log in with your new password."}

    # ── GET PUBLIC PROFILE STATS + IDEAS FOR ANY USER ──
@router.get("/{user_id}/public-stats")
def get_user_public_stats(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ideas = db.query(models.Idea).filter(
        models.Idea.author_id == user_id,
        models.Idea.status == "published"
    ).order_by(models.Idea.created_at.desc()).all()

    total_likes = sum(len(i.likes) for i in ideas)
    total_views = sum(i.views for i in ideas)

    idea_list = [{
        "id": i.id,
        "title": i.title,
        "category": i.category,
        "summary": (i.problem[:110] + "...") if i.problem and len(i.problem) > 110 else i.problem,
        "like_count": len(i.likes),
        "views": i.views,
        "created_at": i.created_at,
    } for i in ideas]

    return {
        "total_ideas": len(ideas),
        "total_likes": total_likes,
        "total_views": total_views,
        "ideas": idea_list,
    }