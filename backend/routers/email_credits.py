"""
Email Credits API — balance and transaction history.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..email_credit_service import get_balance, get_transactions
from ..models import User
from ..security import get_current_user

router = APIRouter(prefix='/api/email-credits', tags=['Email Credits'])


@router.get('')
def get_credit_balance(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current email credit balance."""
    balance = get_balance(db, user.id)
    return balance


@router.get('/transactions')
def list_transactions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get credit transaction history."""
    transactions = get_transactions(db, user.id, limit=limit, offset=offset)
    return {'transactions': transactions, 'limit': limit, 'offset': offset}
