import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import MANAGED_MODEL_NAME
from ..database import get_db
from ..encryption import decrypt_plaintext, encrypt_plaintext
from ..models import AIAgent, AIModel, Subscription, User
from ..schemas import AIAgentIn, AIAgentOut, AIModelIn, AIModelOut
from ..security import get_current_user

router = APIRouter(prefix='/api', tags=['ai'])


def _model_out(model):
    return AIModelOut(
        id=model.id,
        name=model.name,
        provider=model.provider,
        model=model.model,
        base_url=model.base_url,
        temperature=model.temperature,
        max_tokens=model.max_tokens,
        is_default=model.is_default,
        has_api_key=bool(model.api_key_encrypted),
        created_at=model.created_at.isoformat() if model.created_at else None,
    )


def _agent_out(agent, model=None):
    return AIAgentOut(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        purpose=agent.purpose,
        ai_model_id=agent.ai_model_id,
        model_name=model.model if model else '',
        system_prompt=agent.system_prompt,
        temperature=agent.temperature,
        max_tokens=agent.max_tokens,
        status=agent.status,
        is_default=agent.is_default,
        created_at=agent.created_at.isoformat() if agent.created_at else None,
    )


def _load_model(db, user_id, model_id):
    return (
        db.query(AIModel)
        .filter(AIModel.id == model_id, AIModel.user_id == user_id)
        .first()
    )


def _get_plan(db, user):
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    return sub.plan if sub else 'free'


# ---------------- Models ----------------
@router.get('/ai-models', response_model=list[AIModelOut])
def list_models(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    models = (
        db.query(AIModel).filter(AIModel.user_id == user.id).order_by(AIModel.id).all()
    )
    return [_model_out(m) for m in models]


@router.get('/ai-models/available', response_model=dict)
def available_models(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    models = [
        _model_out(m).dict()
        for m in db.query(AIModel).filter(AIModel.user_id == user.id).order_by(AIModel.id).all()
    ]
    plan = _get_plan(db, user)
    return {
        'models': models,
        'managed': {
            'id': None,
            'name': 'PulseBoard Default AI',
            'provider': 'managed',
            'model': MANAGED_MODEL_NAME,
            'temperature': 0.7,
            'max_tokens': 1000,
            'is_default': True,
            'has_api_key': True,
        },
        'managed_available': plan == 'pro',
        'plan': plan,
    }


@router.post('/ai-models', response_model=AIModelOut)
def create_model(
    payload: AIModelIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.provider == 'managed':
        raise HTTPException(status_code=400, detail='The managed model is provided by the platform')
    model = AIModel(
        user_id=user.id,
        name=payload.name,
        provider=payload.provider,
        model=payload.model,
        api_key_encrypted=encrypt_plaintext(payload.api_key) if payload.api_key else None,
        base_url=payload.base_url,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        is_default=payload.is_default,
    )
    if payload.is_default:
        db.query(AIModel).filter(AIModel.user_id == user.id).update({'is_default': False})
    db.add(model)
    db.commit()
    db.refresh(model)
    return _model_out(model)


@router.put('/ai-models/{model_id}', response_model=AIModelOut)
def update_model(
    model_id: int,
    payload: AIModelIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model = _load_model(db, user.id, model_id)
    if not model:
        raise HTTPException(status_code=404, detail='Model not found')
    for field, value in payload.dict(exclude={'api_key'}).items():
        setattr(model, field, value)
    if payload.api_key:
        model.api_key_encrypted = encrypt_plaintext(payload.api_key)
    if payload.is_default:
        db.query(AIModel).filter(AIModel.user_id == user.id).update({'is_default': False})
    db.commit()
    db.refresh(model)
    return _model_out(model)


@router.delete('/ai-models/{model_id}')
def delete_model(
    model_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model = _load_model(db, user.id, model_id)
    if not model:
        raise HTTPException(status_code=404, detail='Model not found')
    db.delete(model)
    db.commit()
    return {'ok': True}


@router.post('/ai-models/{model_id}/test')
def test_model(model_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    model = _load_model(db, user.id, model_id)
    if not model:
        raise HTTPException(status_code=404, detail='Model not found')
    key = decrypt_api_key(model)
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


# ---------------- Agents ----------------
@router.get('/ai-agents', response_model=list[AIAgentOut])
def list_agents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agents = (
        db.query(AIAgent).filter(AIAgent.user_id == user.id).order_by(AIAgent.id).all()
    )
    models = {
        m.id: m
        for m in db.query(AIModel).filter(AIModel.user_id == user.id).all()
    }
    return [_agent_out(a, models.get(a.ai_model_id)) for a in agents]


@router.post('/ai-agents', response_model=AIAgentOut)
def create_agent(
    payload: AIAgentIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.ai_model_id:
        if not _load_model(db, user.id, payload.ai_model_id):
            raise HTTPException(status_code=404, detail='Model not found')
    agent = AIAgent(user_id=user.id, **payload.dict())
    count = db.query(AIAgent).filter(AIAgent.user_id == user.id).count()
    agent.is_default = count == 0
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return _agent_out(agent, _load_model(db, user.id, agent.ai_model_id))


@router.put('/ai-agents/{agent_id}', response_model=AIAgentOut)
def update_agent(
    agent_id: int,
    payload: AIAgentIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = (
        db.query(AIAgent).filter(AIAgent.id == agent_id, AIAgent.user_id == user.id).first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')
    for field, value in payload.dict().items():
        setattr(agent, field, value)
    db.commit()
    db.refresh(agent)
    return _agent_out(agent, _load_model(db, user.id, agent.ai_model_id))


@router.post('/ai-agents/{agent_id}/duplicate', response_model=AIAgentOut)
def duplicate_agent(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = (
        db.query(AIAgent).filter(AIAgent.id == agent_id, AIAgent.user_id == user.id).first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')
    copy = AIAgent(
        user_id=user.id,
        name=f'{agent.name} (copy)',
        description=agent.description,
        purpose=agent.purpose,
        ai_model_id=agent.ai_model_id,
        system_prompt=agent.system_prompt,
        temperature=agent.temperature,
        max_tokens=agent.max_tokens,
        status='disabled',
        is_default=False,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return _agent_out(copy, _load_model(db, user.id, copy.ai_model_id))


@router.post('/ai-agents/{agent_id}/toggle', response_model=AIAgentOut)
def toggle_agent(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = (
        db.query(AIAgent).filter(AIAgent.id == agent_id, AIAgent.user_id == user.id).first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')
    agent.status = 'disabled' if agent.status == 'active' else 'active'
    db.commit()
    db.refresh(agent)
    return _agent_out(agent, _load_model(db, user.id, agent.ai_model_id))


@router.delete('/ai-agents/{agent_id}')
def delete_agent(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = (
        db.query(AIAgent).filter(AIAgent.id == agent_id, AIAgent.user_id == user.id).first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')
    db.delete(agent)
    db.commit()
    return {'ok': True}


def decrypt_api_key(model):
    if not model or not model.api_key_encrypted:
        return None
    return decrypt_plaintext(model.api_key_encrypted)


def resolve_generation_config(db, user, agent_id, model_id=None):
    """Return (provider, model_name, max_tokens, temperature, system_prompt) for generation."""
    agent = (
        db.query(AIAgent).filter(AIAgent.id == agent_id, AIAgent.user_id == user.id).first()
        if agent_id else None
    )
    if not agent or agent.status == 'disabled':
        agent = db.query(AIAgent).filter(AIAgent.user_id == user.id, AIAgent.is_default.is_(True)).first()
    model = None
    if agent:
        model = _load_model(db, user.id, agent.ai_model_id)
    if model is None and model_id:
        model = _load_model(db, user.id, model_id)
    if model is None:
        model = (
            db.query(AIModel)
            .filter(AIModel.user_id == user.id, AIModel.is_default.is_(True))
            .first()
        )
    return agent, model