from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..encryption import decrypt_plaintext, encrypt_plaintext
from ..models import AIModel, Subscription, User
from ..schemas import (
    AdminModelIn,
    AdminModelOut,
    AdminModelUpdate,
    AdminPlanUpdate,
    AdminRoleUpdate,
    AdminUserOut,
)
from ..security import get_current_admin

router = APIRouter(prefix='/api/admin', tags=['admin'])


def _model_out(model):
    return AdminModelOut(
        id=model.id,
        name=model.name,
        provider=model.provider,
        model=model.model,
        base_url=model.base_url or '',
        temperature=model.temperature or 0.7,
        max_tokens=model.max_tokens or 1000,
        price_usd=model.price_usd or 0,
        is_platform=model.is_platform,
        has_api_key=bool(model.api_key_encrypted),
        created_at=model.created_at.isoformat() if model.created_at else None,
    )


def _user_out(user, db):
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    return AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name or '',
        plan=sub.plan if sub else 'free',
        is_admin=bool(user.is_admin),
        is_verified=bool(user.is_verified),
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


def _load_platform_model(db, model_id):
    model = (
        db.query(AIModel)
        .filter(AIModel.id == model_id, AIModel.is_platform.is_(True))
        .first()
    )
    if not model:
        raise HTTPException(status_code=404, detail='Platform model not found')
    return model


# ---------------- Platform AI models ----------------
@router.get('/models', response_model=list[AdminModelOut])
def list_models(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    models = (
        db.query(AIModel).filter(AIModel.is_platform.is_(True)).order_by(AIModel.id).all()
    )
    return [_model_out(m) for m in models]


@router.post('/models', response_model=AdminModelOut)
def create_model(
    payload: AdminModelIn,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not payload.api_key:
        raise HTTPException(status_code=400, detail='An API key is required for a platform model')
    model = AIModel(
        user_id=admin.id,
        name=payload.name,
        provider=payload.provider,
        model=payload.model,
        api_key_encrypted=encrypt_plaintext(payload.api_key),
        base_url=payload.base_url,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        is_platform=True,
        price_usd=payload.price_usd or 0,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return _model_out(model)


@router.patch('/models/{model_id}', response_model=AdminModelOut)
def update_model(
    model_id: int,
    payload: AdminModelUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    model = _load_platform_model(db, model_id)
    if payload.api_key:
        model.api_key_encrypted = encrypt_plaintext(payload.api_key)
    for field in ('name', 'provider', 'model', 'base_url', 'temperature', 'max_tokens', 'price_usd'):
        value = getattr(payload, field)
        if value is not None:
            setattr(model, field, value)
    db.commit()
    db.refresh(model)
    return _model_out(model)


@router.delete('/models/{model_id}')
def delete_model(
    model_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    model = _load_platform_model(db, model_id)
    # Do not delete while users' agents reference it.
    from ..models import AIAgent

    used = db.query(AIAgent).filter(AIAgent.ai_model_id == model.id).count()
    if used:
        raise HTTPException(
            status_code=409,
            detail=f'This model is used by {used} agent(s). Unassign them first.',
        )
    db.delete(model)
    db.commit()
    return {'ok': True}


@router.post('/models/{model_id}/test')
def test_model(
    model_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    model = _load_platform_model(db, model_id)
    key = decrypt_plaintext(model.api_key_encrypted) if model.api_key_encrypted else None
    if not key:
        raise HTTPException(status_code=400, detail='No API key stored for this model')
    from ..ai import provider_for

    provider = provider_for(model, api_key=key)
    if provider is None:
        raise HTTPException(status_code=400, detail='Unsupported provider')
    try:
        provider.test_connection(model.model)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {'ok': True, 'message': f'Connection to {model.provider} verified'}


# ---------------- Users ----------------
@router.get('/users', response_model=list[AdminUserOut])
def list_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return [_user_out(u, db) for u in users]


@router.patch('/users/{user_id}/plan', response_model=AdminUserOut)
def set_plan(
    user_id: int,
    payload: AdminPlanUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if payload.plan not in ('free', 'pro'):
        raise HTTPException(status_code=400, detail='Plan must be "free" or "pro"')
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not sub:
        sub = Subscription(user_id=user.id, plan='free', status='active')
        db.add(sub)
    sub.plan = payload.plan
    sub.status = 'active'
    db.commit()
    return _user_out(user, db)


@router.patch('/users/{user_id}/role', response_model=AdminUserOut)
def set_role(
    user_id: int,
    payload: AdminRoleUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    if user.id == admin.id and not payload.is_admin:
        raise HTTPException(status_code=400, detail='You cannot remove your own admin role')
    user.is_admin = bool(payload.is_admin)
    db.commit()
    return _user_out(user, db)