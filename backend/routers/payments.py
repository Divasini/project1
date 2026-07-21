import os
import hmac
import hashlib
import razorpay
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth import get_current_user

router = APIRouter(prefix="/payments", tags=["Payments"])

# ── Razorpay client ──
# Keys come from environment variables — never hardcode real keys in source.
RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ── Plan pricing (in paise — smallest currency unit for INR) ──
PLAN_PRICES = {
    "pro":     29900,    # ₹299
    "premium": 249900,   # ₹2,499
}


# ── CREATE ORDER ───────────────────────────────
# Called when the user clicks "Upgrade to Pro/Premium".
# Creates a Razorpay order and returns the order_id + public key so the
# frontend can open the Razorpay Checkout widget (which includes Google Pay/UPI).
@router.post("/create-order", response_model=schemas.CreateOrderOut)
def create_order(
    data: schemas.CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if data.plan not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail="Invalid plan. Must be 'pro' or 'premium'.")

    amount = PLAN_PRICES[data.plan]

    try:
        order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1,
            "notes": {
                "user_id": str(current_user.id),
                "plan": data.plan,
            }
        })
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not create payment order: {str(e)}")

    # Save a pending payment record
    payment = models.Payment(
        user_id=current_user.id,
        plan=data.plan,
        amount=amount,
        currency="INR",
        razorpay_order_id=order["id"],
        status="created"
    )
    db.add(payment)
    db.commit()

    return {
        "order_id": order["id"],
        "amount": amount,
        "currency": "INR",
        "key_id": RAZORPAY_KEY_ID,
        "plan": data.plan,
    }


# ── VERIFY PAYMENT ─────────────────────────────
# Called after the Razorpay Checkout widget completes successfully on the frontend.
# Verifies the cryptographic signature server-side before upgrading the user —
# never trust the "payment succeeded" signal from the browser alone.
@router.post("/verify", response_model=schemas.VerifyPaymentOut)
def verify_payment(
    data: schemas.VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    payment = db.query(models.Payment).filter(
        models.Payment.razorpay_order_id == data.razorpay_order_id,
        models.Payment.user_id == current_user.id
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Order not found")

    # ── Verify signature: HMAC-SHA256(order_id + "|" + payment_id, key_secret) ──
    body = f"{data.razorpay_order_id}|{data.razorpay_payment_id}"
    expected_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, data.razorpay_signature):
        payment.status = "failed"
        db.commit()
        raise HTTPException(status_code=400, detail="Payment verification failed. Signature mismatch.")

    # ── Signature valid — mark payment as paid and upgrade the user ──
    payment.status = "paid"
    payment.razorpay_payment_id = data.razorpay_payment_id
    payment.razorpay_signature = data.razorpay_signature

    current_user.is_pro = True
    current_user.plan_type = payment.plan

    db.commit()

    return {
        "success": True,
        "message": f"Payment verified. You are now on the {payment.plan.capitalize()} plan.",
        "plan_type": payment.plan,
    }


# ── GET MY PAYMENT HISTORY ─────────────────────
@router.get("/history")
def get_payment_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    payments = db.query(models.Payment).filter(
        models.Payment.user_id == current_user.id,
        models.Payment.status == "paid"
    ).order_by(models.Payment.created_at.desc()).all()

    return [
        {
            "id": p.id,
            "plan": p.plan,
            "amount": p.amount,
            "currency": p.currency,
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in payments
    ]