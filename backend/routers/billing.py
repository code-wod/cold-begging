import datetime as dt
import hashlib
import hmac
import json
import logging

import razorpay
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import FREE_RATE_PER_HOUR, MAX_RATE_PER_HOUR, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET
from ..database import get_db
from ..email_credit_service import add_credits, PURCHASE_TYPE, REFUND_TYPE
from ..models import CreditTransaction, EmailLog, Subscription, UsageRecord, User
from ..schemas import SubscriptionOut, UsageOut
from ..security import get_current_user

logger = logging.getLogger('billing')

router = APIRouter(prefix='/api/billing', tags=['billing'])

# Razorpay client (initialized lazily)
_razorpay_client = None


def _get_razorpay_client():
    global _razorpay_client
    if _razorpay_client is None:
        if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
            raise HTTPException(status_code=500, detail='Razorpay not configured')
        _razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    return _razorpay_client


# Credit packs: (id, credits, amount_in_paise, label, type)
CREDIT_PACKS = [
    {'id': 'starter',    'credits': 200,    'amount': 4900,   'label': 'Starter',    'type': 'one_time', 'desc': 'Send up to 200 cold emails'},
    {'id': 'pro_monthly', 'credits': 1199,  'amount': 9900,   'label': 'Pro Monthly', 'type': 'monthly',  'desc': 'Send up to 1,199 cold emails/month'},
]

LIMITS = {
    'free': {
        'ai_generation': 100,
        'email_sent': 200,
        'emails_per_hour': FREE_RATE_PER_HOUR,
        'agents': 1,
        'campaigns': 3,
    },
    'pro': {
        'ai_generation': 5000,
        'email_sent': 10000,
        'emails_per_hour': MAX_RATE_PER_HOUR,
        'agents': 50,
        'campaigns': 500,
    },
}


def _get_subscription(db, user):
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not sub:
        sub = Subscription(user_id=user.id, plan='free', status='active')
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


@router.get('', response_model=UsageOut)
def billing(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = _get_subscription(db, user)
    ai = (
        db.query(func.coalesce(func.sum(UsageRecord.quantity), 0))
        .filter(UsageRecord.user_id == user.id, UsageRecord.metric == 'ai_generation')
        .scalar()
    )
    sent = (
        db.query(func.coalesce(func.sum(UsageRecord.quantity), 0))
        .filter(UsageRecord.user_id == user.id, UsageRecord.metric == 'email_sent')
        .scalar()
    )
    return UsageOut(
        ai_generation=int(ai),
        email_sent=int(sent),
        limits=LIMITS.get(sub.plan, LIMITS['free']),
    )


@router.get('/subscription', response_model=SubscriptionOut)
def subscription(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = _get_subscription(db, user)
    return SubscriptionOut(
        plan=sub.plan,
        status=sub.status,
        started_at=sub.started_at.isoformat() if sub.started_at else None,
        renews_at=sub.renews_at.isoformat() if sub.renews_at else None,
    )


@router.post('/upgrade')
def upgrade(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Upgrade to Pro — ONLY via Razorpay payment. This endpoint is disabled."""
    raise HTTPException(status_code=403, detail='Upgrades must be made through the payment system')


@router.post('/downgrade')
def downgrade(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = _get_subscription(db, user)
    if sub.plan == 'free':
        return {'plan': 'free'}
    sub.plan = 'free'
    sub.status = 'active'
    sub.renews_at = None
    db.commit()
    return {'plan': 'free'}


@router.get('/payment-history')
def payment_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get payment transaction history for the user."""
    transactions = (
        db.query(CreditTransaction)
        .filter(
            CreditTransaction.user_id == user.id,
            CreditTransaction.type.in_(['PURCHASE', 'REFUND']),
        )
        .order_by(CreditTransaction.created_at.desc())
        .all()
    )

    history = []
    for tx in transactions:
        history.append({
            'id': tx.id,
            'type': tx.type,
            'amount': tx.amount,
            'description': tx.description,
            'reference_id': tx.reference_id,
            'balance_after': tx.balance_after,
            'status': 'completed' if tx.type == 'PURCHASE' else 'refunded',
            'created_at': tx.created_at.isoformat() if tx.created_at else None,
        })

    return {'payments': history}


# ── Razorpay Credit Packs ──────────────────────────────────────────────


class CreateOrderRequest(BaseModel):
    pack_id: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    pack_id: str


@router.get('/credit-packs')
def list_credit_packs():
    """List available credit packs for purchase."""
    return {'packs': CREDIT_PACKS}


@router.post('/create-order')
def create_order(payload: CreateOrderRequest, user: User = Depends(get_current_user)):
    """Create a Razorpay order for purchasing email credits."""
    pack = next((p for p in CREDIT_PACKS if p['id'] == payload.pack_id), None)
    if not pack:
        raise HTTPException(status_code=400, detail='Invalid pack ID')

    client = _get_razorpay_client()
    try:
        order = client.order.create({
            'amount': pack['amount'],
            'currency': 'INR',
            'receipt': f'user_{user.id}_{pack["id"]}',
            'notes': {
                'user_id': str(user.id),
                'pack_id': pack['id'],
                'credits': str(pack['credits']),
            },
        })
    except Exception as exc:
        logger.error('Razorpay order creation failed: %s', exc)
        raise HTTPException(status_code=500, detail='Failed to create payment order')

    return {
        'order_id': order['id'],
        'amount': pack['amount'],
        'currency': 'INR',
        'key_id': RAZORPAY_KEY_ID,
    }


@router.post('/verify-payment')
def verify_payment(payload: VerifyPaymentRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Verify Razorpay payment signature, credit user, and upgrade plan."""
    pack = next((p for p in CREDIT_PACKS if p['id'] == payload.pack_id), None)
    if not pack:
        raise HTTPException(status_code=400, detail='Invalid pack ID')

    # Verify signature: HMAC-SHA256(order_id + "|" + payment_id, KEY_SECRET)
    if not RAZORPAY_KEY_SECRET:
        logger.error('RAZORPAY_KEY_SECRET not set — cannot verify payment')
        raise HTTPException(status_code=500, detail='Payment verification not configured')

    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        f'{payload.razorpay_order_id}|{payload.razorpay_payment_id}'.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, payload.razorpay_signature):
        logger.warning('Payment signature mismatch for user %s', user.id)
        raise HTTPException(status_code=400, detail='Invalid payment signature')

    # Idempotency: check if this payment was already processed
    existing = db.query(CreditTransaction).filter(
        CreditTransaction.reference_id == payload.razorpay_payment_id,
        CreditTransaction.type == PURCHASE_TYPE,
    ).first()
    if existing:
        # Already processed — return current balance
        from .email_credit_service import get_balance
        balance = get_balance(db, user.id)
        return {
            'status': 'already_processed',
            'credits_added': 0,
            'new_balance': balance['remaining'],
            'plan': _get_subscription(db, user).plan,
        }

    # Add credits to user
    success, new_balance = add_credits(
        db, user.id, pack['credits'], PURCHASE_TYPE,
        reference_id=payload.razorpay_payment_id,
        description=f'Purchased {pack["label"]} — {pack["desc"]}',
    )

    if not success:
        raise HTTPException(status_code=500, detail='Failed to credit account')

    # Upgrade subscription plan based on pack type
    sub = _get_subscription(db, user)
    if sub:
        if pack['type'] in ('monthly', 'yearly'):
            sub.plan = 'pro'
            sub.status = 'active'
            sub.started_at = dt.datetime.now(dt.timezone.utc)
            if pack['type'] == 'monthly':
                sub.renews_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=30)
            else:
                sub.renews_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=365)
            db.commit()
            logger.info('Plan upgraded to pro for user %s', user.id)

    db.commit()
    logger.info('Payment verified: %s credits + plan upgrade for user %s', pack['credits'], user.id)
    return {
        'status': 'success',
        'credits_added': pack['credits'],
        'new_balance': new_balance,
        'plan': sub.plan if sub else 'free',
    }


# ── Razorpay Webhooks ──────────────────────────────────────────────────


def _verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify Razorpay webhook signature: HMAC-SHA256(body, WEBHOOK_SECRET)."""
    if not RAZORPAY_WEBHOOK_SECRET:
        logger.error('RAZORPAY_WEBHOOK_SECRET not set — webhook verification DISABLED')
        return False
    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _extract_user_id_from_receipt(receipt: str):
    """Extract user_id from receipt format 'user_{id}_{pack_id}'."""
    try:
        parts = receipt.split('_')
        if len(parts) >= 2 and parts[0] == 'user':
            return int(parts[1])
    except (ValueError, IndexError):
        pass
    return None


def _pack_from_amount(amount: int):
    """Look up credit pack by amount in paise."""
    return next((p for p in CREDIT_PACKS if p['amount'] == amount), None)


@router.post('/razorpay-webhook')
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Razorpay webhook events.

    Configure at https://dashboard.razorpay.com/app/settings/webhooks
    Events to subscribe: payment.captured, payment.failed, refund.created, refund.processed
    """
    body = await request.body()
    signature = request.headers.get('x-razorpay-signature', '')

    if not _verify_webhook_signature(body, signature):
        logger.warning('Webhook signature verification failed')
        raise HTTPException(status_code=400, detail='Invalid webhook signature')

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail='Invalid JSON')

    event = payload.get('event', '')
    entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
    refund_entity = payload.get('payload', {}).get('refund', {}).get('entity', {})

    logger.info('Razorpay webhook received: %s', event)

    # ── payment.captured ── Credits user after successful payment
    if event == 'payment.captured':
        order = entity.get('order_id', '')
        amount = entity.get('amount', 0)
        payment_id = entity.get('id', '')
        status = entity.get('status', '')

        # Fetch order to get receipt (contains user_id + pack_id)
        try:
            client = _get_razorpay_client()
            order_data = client.order.fetch(order)
            receipt = order_data.get('receipt', '')
        except Exception as exc:
            logger.error('Failed to fetch order %s: %s', order, exc)
            return {'status': 'error', 'detail': 'Could not fetch order'}

        user_id = _extract_user_id_from_receipt(receipt)
        pack = _pack_from_amount(amount)

        if not user_id or not pack:
            logger.warning('Webhook: could not resolve user/pack from receipt=%s amount=%s', receipt, amount)
            return {'status': 'skipped', 'reason': 'invalid receipt or amount'}

        # Check for duplicate credit (idempotent)
        existing = db.query(CreditTransaction).filter(
            CreditTransaction.reference_id == payment_id,
            CreditTransaction.type == PURCHASE_TYPE,
        ).first()
        if existing:
            logger.info('Webhook: payment %s already credited (tx %s)', payment_id, existing.id)
            return {'status': 'already_credited'}

        success, balance = add_credits(
            db, user_id, pack['credits'], PURCHASE_TYPE,
            reference_id=payment_id,
            description=f'Purchased {pack["label"]} via webhook — {pack["desc"]}',
        )

        # Upgrade subscription plan for monthly/yearly packs
        if success and pack['type'] in ('monthly', 'yearly'):
            sub = _get_subscription(db, user_id)
            if sub:
                sub.plan = 'pro'
                sub.status = 'active'
                sub.started_at = dt.datetime.now(dt.timezone.utc)
                if pack['type'] == 'monthly':
                    sub.renews_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=30)
                else:
                    sub.renews_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=365)

        db.commit()

        if success:
            logger.info('Webhook: credited %d credits to user %s (balance: %d)', pack['credits'], user_id, balance)
        else:
            logger.error('Webhook: failed to credit user %s', user_id)

        return {'status': 'credited' if success else 'error'}

    # ── payment.failed ── Log failed payment
    elif event == 'payment.failed':
        payment_id = entity.get('id', '')
        error_desc = entity.get('error_description', '')
        logger.warning('Webhook: payment failed — %s: %s', payment_id, error_desc)
        return {'status': 'logged'}

    # ── refund.created / refund.processed ── Deduct credits on refund
    elif event in ('refund.created', 'refund.processed'):
        if event == 'refund.processed' and refund_entity.get('status') != 'processed':
            return {'status': 'skipped', 'reason': 'refund not yet processed'}

        payment_id = refund_entity.get('payment_id', '')
        refund_id = refund_entity.get('id', '')
        amount = refund_entity.get('amount', 0)

        # Find the original purchase transaction
        original_tx = db.query(CreditTransaction).filter(
            CreditTransaction.reference_id == payment_id,
            CreditTransaction.type == PURCHASE_TYPE,
        ).first()

        if not original_tx:
            logger.warning('Webhook: refund for unknown payment %s', payment_id)
            return {'status': 'skipped', 'reason': 'original payment not found'}

        # Check if refund already recorded
        existing_refund = db.query(CreditTransaction).filter(
            CreditTransaction.reference_id == refund_id,
            CreditTransaction.type == REFUND_TYPE,
        ).first()
        if existing_refund:
            logger.info('Webhook: refund %s already recorded', refund_id)
            return {'status': 'already_refunded'}

        # Calculate credits to deduct based on refund amount vs original amount
        pack = _pack_from_amount(original_tx.amount * 100)  # amount is in paise
        if pack:
            credits_to_deduct = pack['credits']
        else:
            # Fallback: proportional deduction
            credits_to_deduct = int((amount / (original_tx.amount * 100)) * 100) if original_tx.amount else 0

        if credits_to_deduct > 0:
            add_credits(
                db, original_tx.user_id, -credits_to_deduct, REFUND_TYPE,
                reference_id=refund_id,
                description=f'Refund: {credits_to_deduct} credits deducted',
            )
            db.commit()
            logger.info('Webhook: deducted %d credits from user %s for refund', credits_to_deduct, original_tx.user_id)

        return {'status': 'refunded'}

    # ── Other events ── Log and ignore
    else:
        logger.info('Webhook: unhandled event %s', event)
        return {'status': 'ignored'}