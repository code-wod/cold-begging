"""User-owned recipient groups.

Every recipient belongs to a group owned by the same user. Groups are the
primary organizational unit for the recipients UI, import, and campaign
targeting. All queries here are scoped to the authenticated user.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Recipient, RecipientGroup, User
from ..schemas import RecipientGroupIn, RecipientGroupOut, RecipientGroupUpdate
from ..security import get_current_user

logger = logging.getLogger('recipient_groups')

router = APIRouter(prefix='/api/recipient-groups', tags=['recipient-groups'])

DEFAULT_GROUP_NAME = 'Uncategorized'


def _out(db: Session, group: RecipientGroup) -> RecipientGroupOut:
    count = (
        db.query(func.count(Recipient.id))
        .filter(Recipient.group_id == group.id)
        .scalar()
    )
    return RecipientGroupOut(
        id=group.id,
        name=group.name,
        recipient_count=count,
        created_at=group.created_at.isoformat() if group.created_at else None,
        updated_at=group.updated_at.isoformat() if group.updated_at else None,
    )


def _load_owned(db: Session, user: User, group_id: int) -> RecipientGroup:
    group = (
        db.query(RecipientGroup)
        .filter(RecipientGroup.id == group_id, RecipientGroup.user_id == user.id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail='Recipient group not found')
    return group


def ensure_group(db: Session, user: User, name: str) -> RecipientGroup:
    """Return the current user's group named `name`, creating it if needed.

    Group names are unique per user, so an existing matching group is reused
    instead of creating a duplicate.
    """
    name = (name or '').strip()
    if not name:
        raise HTTPException(status_code=400, detail='Group name is required')
    existing = (
        db.query(RecipientGroup)
        .filter(
            RecipientGroup.user_id == user.id,
            func.lower(RecipientGroup.name) == name.lower(),
        )
        .first()
    )
    if existing:
        return existing
    group = RecipientGroup(user_id=user.id, name=name)
    db.add(group)
    db.flush()
    return group


def ensure_default_group(db: Session, user: User) -> RecipientGroup:
    """The fallback group for legacy recipients (and group deletion)."""
    return ensure_group(db, user, DEFAULT_GROUP_NAME)


@router.get('', response_model=list[RecipientGroupOut])
def list_groups(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    groups = (
        db.query(RecipientGroup)
        .filter(RecipientGroup.user_id == user.id)
        .order_by(RecipientGroup.updated_at.desc(), RecipientGroup.created_at.desc())
        .all()
    )
    return [_out(db, g) for g in groups]


@router.post('', response_model=RecipientGroupOut)
def create_group(payload: RecipientGroupIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = ensure_group(db, user, payload.name)
    db.commit()
    db.refresh(group)
    return _out(db, group)


@router.get('/{group_id}', response_model=RecipientGroupOut)
def get_group(group_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(db, _load_owned(db, user, group_id))


@router.patch('/{group_id}', response_model=RecipientGroupOut)
def update_group(
    group_id: int,
    payload: RecipientGroupUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = _load_owned(db, user, group_id)
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail='Group name is required')
        dup = (
            db.query(RecipientGroup)
            .filter(
                RecipientGroup.user_id == user.id,
                RecipientGroup.id != group.id,
                func.lower(RecipientGroup.name) == name.lower(),
            )
            .first()
        )
        if dup:
            raise HTTPException(status_code=409, detail='A group with this name already exists')
        group.name = name
    db.commit()
    db.refresh(group)
    return _out(db, group)


@router.delete('/{group_id}')
def delete_group(group_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a group. Its recipients move to the user's 'Uncategorized' group."""
    group = _load_owned(db, user, group_id)
    moved = (
        db.query(Recipient)
        .filter(Recipient.group_id == group.id)
        .update({'group_id': ensure_default_group(db, user).id}, synchronize_session=False)
    )
    db.delete(group)
    db.commit()
    return {'ok': True, 'moved': moved}


@router.get('/{group_id}/recipients')
def list_group_recipients(
    group_id: int,
    page: int = 1,
    page_size: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Paginated recipients for one owned group.

    Filters by both the authenticated user and the requested group so a user
    can never see recipients belonging to another user's group.
    """
    group = _load_owned(db, user, group_id)
    if page < 1:
        page = 1
    page_size = max(1, min(page_size, 200))
    query = db.query(Recipient).filter(Recipient.user_id == user.id, Recipient.group_id == group.id)
    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total else 0
    items = query.order_by(Recipient.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        'group_id': group.id,
        'group_name': group.name,
        'items': [
            {
                'id': r.id,
                'email': r.email,
                'company_name': r.company_name or '',
                'industry': r.industry or '',
                'company_website': r.company_website or '',
                'job_role': r.job_role or '',
                'position_level': r.position_level or '',
                'group_id': r.group_id,
                'group_name': group.name,
                'created_at': r.created_at.isoformat() if r.created_at else None,
            }
            for r in items
        ],
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': total_pages,
    }