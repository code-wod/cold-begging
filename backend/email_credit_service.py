"""
Email Credit Service

Handles all email credit operations with atomic database transactions.
Ensures race-condition safety and idempotent operations.

Credit types:
- FREE_GRANT: Initial 50 free credits on signup
- PURCHASE: Credits purchased via Razorpay (future)
- EMAIL_SEND: Credit consumed per email sent
- REFUND: Credits refunded (future)
- ADMIN_ADJUSTMENT: Admin manual adjustment (future)
"""

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import CreditTransaction, User

logger = logging.getLogger('email_credit')

# Constants
FREE_CREDIT_AMOUNT = 50
FREE_GRANT_TYPE = 'FREE_GRANT'
EMAIL_SEND_TYPE = 'EMAIL_SEND'
PURCHASE_TYPE = 'PURCHASE'
REFUND_TYPE = 'REFUND'
ADMIN_ADJUSTMENT_TYPE = 'ADMIN_ADJUSTMENT'


def get_balance(db: Session, user_id: int) -> dict:
    """Get the current email credit balance for a user.

    Returns dict with remaining, free_credits, and purchased_credits.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {'remaining': 0, 'free_credits': 0, 'purchased_credits': 0}

    remaining = user.email_credits or 0

    # Count free grants and purchases for breakdown
    free_granted = db.query(CreditTransaction).filter(
        CreditTransaction.user_id == user_id,
        CreditTransaction.type == FREE_GRANT_TYPE,
    ).with_entities(CreditTransaction.amount).all()
    free_credits = sum(t.amount for t in free_granted)

    purchased = db.query(CreditTransaction).filter(
        CreditTransaction.user_id == user_id,
        CreditTransaction.type == PURCHASE_TYPE,
    ).with_entities(CreditTransaction.amount).all()
    purchased_credits = sum(t.amount for t in purchased)

    return {
        'remaining': remaining,
        'free_credits': free_credits,
        'purchased_credits': purchased_credits,
    }


def consume_credit(db: Session, user_id: int, reference_id: str = '',
                   description: str = 'Email sent') -> tuple[bool, int]:
    """Atomically consume 1 email credit.

    Uses SQL-level atomic UPDATE with WHERE clause to prevent race conditions.

    Returns:
        (success, remaining_credits)
        success=True if credit was consumed, False if insufficient credits
    """
    # Atomic UPDATE — only succeeds if credits > 0
    result = db.execute(
        text('UPDATE users SET email_credits = email_credits - 1 '
             'WHERE id = :user_id AND email_credits > 0'),
        {'user_id': user_id},
    )

    if result.rowcount == 0:
        # No credits available
        user = db.query(User).filter(User.id == user_id).first()
        remaining = user.email_credits if user else 0
        logger.warning(f'Insufficient credits for user {user_id} (remaining: {remaining})')
        return False, remaining

    # Read updated balance
    db.flush()
    db.expire(db.query(User).filter(User.id == user_id).first())
    user = db.query(User).filter(User.id == user_id).first()
    remaining = user.email_credits

    # Record transaction
    transaction = CreditTransaction(
        user_id=user_id,
        type=EMAIL_SEND_TYPE,
        amount=-1,
        reference_id=reference_id,
        description=description,
        balance_after=remaining,
    )
    db.add(transaction)
    db.flush()

    logger.info(f'Consumed 1 credit for user {user_id}, remaining: {remaining}')
    return True, remaining


def add_credits(db: Session, user_id: int, amount: int, tx_type: str,
                reference_id: str = '', description: str = '') -> tuple[bool, int]:
    """Atomically add credits to a user's balance.

    Used for:
    - FREE_GRANT on signup
    - PURCHASE after Razorpay payment
    - REFUND
    - ADMIN_ADJUSTMENT

    Returns:
        (success, new_balance)
    """
    if amount <= 0:
        raise ValueError('Amount must be positive')

    # Atomic UPDATE
    result = db.execute(
        text('UPDATE users SET email_credits = email_credits + :amount '
             'WHERE id = :user_id'),
        {'user_id': user_id, 'amount': amount},
    )

    if result.rowcount == 0:
        logger.error(f'Failed to add credits: user {user_id} not found')
        return False, 0

    db.flush()
    db.expire(db.query(User).filter(User.id == user_id).first())
    user = db.query(User).filter(User.id == user_id).first()
    new_balance = user.email_credits

    # Record transaction
    transaction = CreditTransaction(
        user_id=user_id,
        type=tx_type,
        amount=amount,
        reference_id=reference_id,
        description=description or f'{tx_type}: +{amount} credits',
        balance_after=new_balance,
    )
    db.add(transaction)
    db.flush()

    logger.info(f'Added {amount} credits ({tx_type}) to user {user_id}, new balance: {new_balance}')
    return True, new_balance


def grant_free_credits(db: Session, user_id: int) -> bool:
    """Grant initial 50 free credits to a new user. Idempotent.

    Uses a uniqueness check on the FREE_GRANT transaction type
    to ensure this only happens once per user.

    Returns True if credits were granted, False if already granted.
    """
    # Check if already granted
    existing = db.query(CreditTransaction).filter(
        CreditTransaction.user_id == user_id,
        CreditTransaction.type == FREE_GRANT_TYPE,
    ).first()

    if existing:
        logger.info(f'Free credits already granted to user {user_id}')
        return False

    success, balance = add_credits(
        db, user_id, FREE_CREDIT_AMOUNT, FREE_GRANT_TYPE,
        description='Welcome! 50 free email credits',
    )

    if success:
        logger.info(f'Granted {FREE_CREDIT_AMOUNT} free credits to user {user_id}')

    return success


def get_transactions(db: Session, user_id: int, limit: int = 50,
                     offset: int = 0) -> list[dict]:
    """Get credit transaction history for a user."""
    transactions = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.user_id == user_id)
        .order_by(CreditTransaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            'id': t.id,
            'type': t.type,
            'amount': t.amount,
            'description': t.description,
            'reference_id': t.reference_id,
            'balance_after': t.balance_after,
            'created_at': t.created_at.isoformat() if t.created_at else None,
        }
        for t in transactions
    ]
