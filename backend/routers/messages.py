from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from typing import Dict, List
from database import get_db
import models, schemas
from auth import get_current_user, decode_access_token


router = APIRouter(tags=["Messages"])


# ── CONNECTION MANAGER ─────────────────────────
# Tracks which user_id is connected to which active WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, data: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(data)


manager = ConnectionManager()


# ── WEBSOCKET ENDPOINT ─────────────────────────
# Connect: ws://localhost:8000/ws/chat?token=<jwt>
@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str = Query(...), db: Session = Depends(get_db)):
    user = decode_access_token(token, db)   # returns User or None — see note below
    if not user:
        await websocket.close(code=1008)
        return

    await manager.connect(user.id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            receiver_id = data.get("receiver_id")
            content = data.get("content", "").strip()

            if not receiver_id or not content:
                continue

            # NOTE: connection requirement removed — any logged-in user
            # can now message any other user directly (e.g. from an idea page).
            msg = models.Message(
                sender_id=user.id,
                receiver_id=receiver_id,
                content=content
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)

            payload = {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "receiver_id": msg.receiver_id,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }

            # Send to receiver if online, and echo back to sender
            await manager.send_to_user(receiver_id, payload)
            await manager.send_to_user(user.id, payload)

    except WebSocketDisconnect:
        manager.disconnect(user.id)


# ── REST: GET CONVERSATION LIST ────────────────
@router.get("/messages/conversations", response_model=List[schemas.ConversationOut])
def get_conversations(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    msgs = db.query(models.Message).filter(
        or_(models.Message.sender_id == current_user.id, models.Message.receiver_id == current_user.id)
    ).order_by(desc(models.Message.created_at)).all()

    seen = {}
    for m in msgs:
        other_id = m.receiver_id if m.sender_id == current_user.id else m.sender_id
        if other_id not in seen:
            seen[other_id] = m

    result = []
    for other_id, last_msg in seen.items():
        other_user = db.query(models.User).filter(models.User.id == other_id).first()
        if not other_user:
            continue
        unread = db.query(models.Message).filter(
            models.Message.sender_id == other_id,
            models.Message.receiver_id == current_user.id,
            models.Message.is_read == False
        ).count()
        result.append({
            "user": other_user,
            "last_message": last_msg.content,
            "last_time": last_msg.created_at,
            "unread_count": unread,
        })

    result.sort(key=lambda x: x["last_time"], reverse=True)
    return result


# ── REST: GET CHAT HISTORY WITH ONE USER ───────
@router.get("/messages/{other_user_id}", response_model=List[schemas.MessageOut])
def get_chat_history(other_user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    msgs = db.query(models.Message).filter(
        or_(
            and_(models.Message.sender_id == current_user.id, models.Message.receiver_id == other_user_id),
            and_(models.Message.sender_id == other_user_id, models.Message.receiver_id == current_user.id),
        )
    ).order_by(models.Message.created_at.asc()).all()

    # Mark incoming messages as read
    db.query(models.Message).filter(
        models.Message.sender_id == other_user_id,
        models.Message.receiver_id == current_user.id,
        models.Message.is_read == False
    ).update({"is_read": True})
    db.commit()

    return msgs