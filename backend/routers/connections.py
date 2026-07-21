from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import models, schemas
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/connections", tags=["Connections"])


# ── SEND CONNECTION REQUEST ────────────────────
@router.post("/{user_id}/request")
def send_connection_request(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot connect with yourself")

    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(models.Connection).filter(
        or_(
            and_(models.Connection.requester_id == current_user.id, models.Connection.receiver_id == user_id),
            and_(models.Connection.requester_id == user_id, models.Connection.receiver_id == current_user.id),
        )
    ).first()

    if existing:
        if existing.status == "accepted":
            raise HTTPException(status_code=400, detail="Already connected")
        raise HTTPException(status_code=400, detail=f"Connection already {existing.status}")

    conn = models.Connection(
        requester_id=current_user.id,
        receiver_id=user_id,
        status="pending"
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return {"message": "Connection request sent", "status": "pending"}


# ── GET CONNECTION STATUS WITH A SPECIFIC USER ──
@router.get("/{user_id}/status", response_model=schemas.ConnectionStatusOut)
def get_connection_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    conn = db.query(models.Connection).filter(
        or_(
            and_(models.Connection.requester_id == current_user.id, models.Connection.receiver_id == user_id),
            and_(models.Connection.requester_id == user_id, models.Connection.receiver_id == current_user.id),
        )
    ).first()

    if not conn:
        return {"status": "none", "connection_id": None}

    if conn.status == "accepted":
        return {"status": "accepted", "connection_id": conn.id}

    if conn.status == "pending":
        if conn.requester_id == current_user.id:
            return {"status": "pending_sent", "connection_id": conn.id}
        else:
            return {"status": "pending_received", "connection_id": conn.id}

    return {"status": "none", "connection_id": None}


# ── GET INCOMING PENDING REQUESTS ──────────────
@router.get("/requests/incoming", response_model=list[schemas.ConnectionOut])
def get_incoming_connection_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    requests = db.query(models.Connection).filter(
        models.Connection.receiver_id == current_user.id,
        models.Connection.status == "pending"
    ).order_by(models.Connection.created_at.desc()).all()
    return requests


# ── ACCEPT / REJECT A CONNECTION REQUEST ───────
@router.post("/{connection_id}/respond")
def respond_to_connection(
    connection_id: int,
    decision: str,  # "accept" or "reject"
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    conn = db.query(models.Connection).filter(models.Connection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Request not found")

    if conn.receiver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your request to respond to")

    if decision not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Decision must be 'accept' or 'reject'")

    conn.status = "accepted" if decision == "accept" else "rejected"
    db.commit()
    return {"message": f"Connection {conn.status}", "status": conn.status}


# ── GET MY CONNECTION COUNT (for a given user's profile) ──
@router.get("/{user_id}/count")
def get_connection_count(user_id: int, db: Session = Depends(get_db)):
    count = db.query(models.Connection).filter(
        or_(models.Connection.requester_id == user_id, models.Connection.receiver_id == user_id),
        models.Connection.status == "accepted"
    ).count()
    return {"count": count}


# ── GET MY CONNECTIONS LIST ────────────────────
@router.get("/", response_model=list[schemas.ConnectionOut])
def get_my_connections(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    connections = db.query(models.Connection).filter(
        or_(models.Connection.requester_id == current_user.id, models.Connection.receiver_id == current_user.id),
        models.Connection.status == "accepted"
    ).order_by(models.Connection.created_at.desc()).all()
    return connections