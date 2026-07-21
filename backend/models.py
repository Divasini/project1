from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB as models_JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    email         = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    bio           = Column(Text, default="")
    location      = Column(String(100), default="")
    avatar_url    = Column(String(500), default="")
    is_pro        = Column(Boolean, default=False)
    plan_type     = Column(String(20), default="free")  # free / pro / premium
    is_admin      = Column(Boolean, default=False)
    is_verified   = Column(Boolean, default=False)
    is_banned     = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    # Relations
    ideas      = relationship("Idea",    back_populates="author",  cascade="all, delete")
    threads    = relationship("Thread",  back_populates="author",  cascade="all, delete")
    replies    = relationship("Reply",   back_populates="author",  cascade="all, delete")
    likes      = relationship("Like",    back_populates="user",    cascade="all, delete")
    bookmarks  = relationship("Bookmark",back_populates="user",    cascade="all, delete")
    idea_comments = relationship("IdeaComment", back_populates="user", cascade="all, delete")


class Idea(Base):
    __tablename__ = "ideas"

    id            = Column(Integer, primary_key=True, index=True)
    title         = Column(String(200), nullable=False)
    category      = Column(String(100), nullable=False)
    problem       = Column(Text, nullable=False)
    solution      = Column(Text, nullable=False)
    target        = Column(String(200), default="")
    revenue_model = Column(String(200), default="")
    tech_stack    = Column(String(200), default="")
    tags          = Column(String(300), default="")
    cover_image_url = Column(String(500), default="")
    ai_analysis   = Column(models_JSON, nullable=True)
    status        = Column(String(20),  default="published")  # published / draft
    views         = Column(Integer,     default=0)
    share_count   = Column(Integer,     default=0)
    author_id     = Column(Integer, ForeignKey("users.id"))
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    # Relations
    author    = relationship("User",     back_populates="ideas")
    likes     = relationship("Like",     back_populates="idea",    cascade="all, delete")
    bookmarks = relationship("Bookmark", back_populates="idea",    cascade="all, delete")
    comments  = relationship("IdeaComment", back_populates="idea", cascade="all, delete")
    access_requests = relationship("AccessRequest", back_populates="idea", cascade="all, delete")


class IdeaComment(Base):
    __tablename__ = "idea_comments"

    id         = Column(Integer, primary_key=True, index=True)
    body       = Column(Text, nullable=False)
    idea_id    = Column(Integer, ForeignKey("ideas.id"))
    user_id    = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    idea = relationship("Idea", back_populates="comments")
    user = relationship("User", back_populates="idea_comments")


class Thread(Base):
    __tablename__ = "threads"

    id         = Column(Integer, primary_key=True, index=True)
    title      = Column(String(200), nullable=False)
    body       = Column(Text,        nullable=False)
    category   = Column(String(100), default="General")
    image_url  = Column(String(500), default="")
    author_id  = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    author  = relationship("User",  back_populates="threads")
    replies = relationship("Reply", back_populates="thread", cascade="all, delete")


class Reply(Base):
    __tablename__ = "replies"

    id         = Column(Integer, primary_key=True, index=True)
    body       = Column(Text, nullable=False)
    thread_id  = Column(Integer, ForeignKey("threads.id"))
    author_id  = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    thread = relationship("Thread", back_populates="replies")
    author = relationship("User",   back_populates="replies")


class Like(Base):
    __tablename__ = "likes"

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id"))
    idea_id   = Column(Integer, ForeignKey("ideas.id"))

    user = relationship("User", back_populates="likes")
    idea = relationship("Idea", back_populates="likes")


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id"))
    idea_id   = Column(Integer, ForeignKey("ideas.id"))

    user = relationship("User", back_populates="bookmarks")
    idea = relationship("Idea", back_populates="bookmarks")


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id          = Column(Integer, primary_key=True, index=True)
    idea_id     = Column(Integer, ForeignKey("ideas.id"))
    requester_id = Column(Integer, ForeignKey("users.id"))
    status      = Column(String(20), default="pending")  # pending / accepted / rejected
    message     = Column(Text, default="")
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    idea      = relationship("Idea", back_populates="access_requests")
    requester = relationship("User", foreign_keys=[requester_id])


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
    token      = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
    token      = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


class Message(Base):
    __tablename__ = "messages"

    id            = Column(Integer, primary_key=True, index=True)
    sender_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    content       = Column(Text, nullable=False)
    is_read       = Column(Boolean, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    sender   = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])


class Connection(Base):
    __tablename__ = "connections"

    id            = Column(Integer, primary_key=True, index=True)
    requester_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    status        = Column(String(20), default="pending")  # pending / accepted / rejected
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    requester = relationship("User", foreign_keys=[requester_id])
    receiver  = relationship("User", foreign_keys=[receiver_id])


class Payment(Base):
    __tablename__ = "payments"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan            = Column(String(20), nullable=False)   # "pro" / "premium"
    amount          = Column(Integer, nullable=False)       # amount in paise (smallest unit)
    currency        = Column(String(10), default="INR")
    razorpay_order_id   = Column(String(100), unique=True, index=True, nullable=False)
    razorpay_payment_id = Column(String(100), nullable=True)
    razorpay_signature  = Column(String(255), nullable=True)
    status          = Column(String(20), default="created")  # created / paid / failed
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")