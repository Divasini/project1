from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# ── USER ──────────────────────────────────────
class UserCreate(BaseModel):
    name:     str = Field(..., min_length=2, max_length=100)
    email:    EmailStr
    password: str = Field(..., min_length=8, max_length=72)

class UserLogin(BaseModel):
    email:    EmailStr
    password: str

class UserOut(BaseModel):
    id:          int
    name:        str
    email:       str
    bio:         Optional[str] = ""
    location:    Optional[str] = ""
    avatar_url:  Optional[str] = ""
    is_pro:      bool
    plan_type:   Optional[str] = "free"
    is_admin:    bool = False
    is_verified: bool = False
    is_banned:   bool = False
    created_at:  datetime

    class Config:
        from_attributes = True


# ── TOKEN ─────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type:   str
    user:         UserOut


# ── IDEA ──────────────────────────────────────
class IdeaCreate(BaseModel):
    title:         str = Field(..., min_length=3, max_length=200)
    category:      str = Field(..., min_length=1, max_length=100)
    problem:       str = Field(..., min_length=3, max_length=5000)
    solution:      str = Field(..., min_length=3, max_length=5000)
    target:        Optional[str] = Field("", max_length=500)
    revenue_model: Optional[str] = Field("", max_length=500)
    tech_stack:    Optional[str] = Field("", max_length=500)
    tags:          Optional[str] = Field("", max_length=500)
    status:        Optional[str] = "published"

class IdeaPublicOut(BaseModel):
    id:            int
    title:         str
    category:      str
    summary:       Optional[str] = ""   # short teaser, auto-generated from problem
    problem:       Optional[str] = ""   # full problem statement (feed shows this)
    cover_image_url: Optional[str] = ""
    status:        str
    views:         int
    author_id:     int
    author:        UserOut
    like_count:    Optional[int] = 0
    comment_count: Optional[int] = 0
    share_count:   Optional[int] = 0
    liked:         Optional[bool] = False
    bookmarked:    Optional[bool] = False
    is_owner:      Optional[bool] = False
    has_access:    Optional[bool] = False
    created_at:    datetime

    class Config:
        from_attributes = True

# Full idea — used in idea-details.html ONLY if owner or access granted
class IdeaOut(BaseModel):
    id:            int
    title:         str
    category:      str
    problem:       Optional[str] = None
    solution:      Optional[str] = None
    target:        Optional[str] = ""
    revenue_model: Optional[str] = ""
    tech_stack:    Optional[str] = ""
    tags:          Optional[str] = ""
    cover_image_url: Optional[str] = ""
    status:        str
    views:         int
    author_id:     int
    author:        UserOut
    like_count:    Optional[int] = 0
    comment_count: Optional[int] = 0
    share_count:   Optional[int] = 0
    is_owner:      Optional[bool] = False
    has_access:    Optional[bool] = False
    request_status: Optional[str] = None  # null / pending / accepted / rejected
    created_at:    datetime

    class Config:
        from_attributes = True


# ── IDEA COMMENTS ──────────────────────────────
class IdeaCommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=1000)

class IdeaCommentOut(BaseModel):
    id:         int
    body:       str
    user:       UserOut
    created_at: datetime

    class Config:
        from_attributes = True


# ── THREAD ────────────────────────────────────
class ThreadCreate(BaseModel):
    title:    str
    body:     str
    category: Optional[str] = "General"

class ThreadOut(BaseModel):
    id:           int
    title:        str
    body:         str
    category:     str
    image_url:    Optional[str] = ""
    author:       UserOut
    reply_count:  Optional[int] = 0
    created_at:   datetime

    class Config:
        from_attributes = True


# ── REPLY ─────────────────────────────────────
class ReplyCreate(BaseModel):
    body: str

class ReplyOut(BaseModel):
    id:         int
    body:       str
    author:     UserOut
    created_at: datetime

    class Config:
        from_attributes = True


# ── PAGINATION ────────────────────────────────
class PaginatedIdeas(BaseModel):
    items:       list[IdeaPublicOut]
    total:       int
    page:        int
    page_size:   int
    total_pages: int


# ── ACCESS REQUEST ────────────────────────────
class AccessRequestCreate(BaseModel):
    message: Optional[str] = ""

class AccessRequestOut(BaseModel):
    id:         int
    idea_id:    int
    status:     str
    message:    Optional[str] = ""
    requester:  UserOut
    idea_title: Optional[str] = ""
    created_at: datetime

    class Config:
        from_attributes = True


# ── NOTIFICATIONS ─────────────────────────────
class NotificationOut(BaseModel):
    type:       str   # "like" | "access_request" | "access_accepted" | "access_rejected"
    icon:       str
    title:      str
    subtitle:   str
    created_at: datetime


# ── DASHBOARD ─────────────────────────────────
class DashboardOut(BaseModel):
    total_ideas:     int
    total_likes:     int
    total_views:     int
    total_bookmarks: int
    recent_ideas:    list[IdeaPublicOut]
    bookmarked_ideas: list[IdeaPublicOut]
    pending_requests: list[AccessRequestOut] = []
    notifications:    list[NotificationOut] = []


# ── MESSAGES / CHAT ────────────────────────────
class MessageCreate(BaseModel):
    receiver_id: int
    content:     str = Field(..., min_length=1, max_length=2000)

class MessageOut(BaseModel):
    id:          int
    sender_id:   int
    receiver_id: int
    content:     str
    is_read:     bool
    created_at:  datetime

    class Config:
        from_attributes = True

# One row in the conversation list (sidebar) — shows the OTHER user + last message
class ConversationOut(BaseModel):
    user:          UserOut       # the other person in the conversation
    last_message:  str
    last_time:     datetime
    unread_count:  int

# ── CONNECTIONS ────────────────────────────────
class ConnectionOut(BaseModel):
    id:         int
    status:     str
    requester:  UserOut
    receiver:   UserOut
    created_at: datetime

    class Config:
        from_attributes = True

class ConnectionStatusOut(BaseModel):
    status: str  # "none" | "pending_sent" | "pending_received" | "accepted"
    connection_id: Optional[int] = None


# ── PAYMENTS ────────────────────────────────────
class CreateOrderRequest(BaseModel):
    plan: str  # "pro" or "premium"

class CreateOrderOut(BaseModel):
    order_id:  str
    amount:    int      # in paise
    currency:  str
    key_id:    str       # Razorpay public key, needed by the frontend checkout widget
    plan:      str

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str

class VerifyPaymentOut(BaseModel):
    success: bool
    message: str
    plan_type: Optional[str] = None