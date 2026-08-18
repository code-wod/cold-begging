import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import campaign_service
from ..config import FREE_RESUME_LIMIT, PRO_RESUME_LIMIT, UPLOAD_DIR
from ..database import get_db
from ..models import User, UserProfileAsset
from ..schemas import ProfileAssetIn, ProfileAssetOut
from ..security import get_current_user

router = APIRouter(prefix='/api/profile-assets', tags=['profile-assets'])

RESUME_TYPES = ('resume', 'resume_link')
LINK_TYPES = ('resume_link', 'github', 'linkedin', 'website')
ALLOWED_TYPES = ('resume',) + LINK_TYPES
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


def _resume_limit(plan):
    return PRO_RESUME_LIMIT if plan == 'pro' else FREE_RESUME_LIMIT


def _resume_count(db, user):
    return (
        db.query(UserProfileAsset)
        .filter(UserProfileAsset.user_id == user.id, UserProfileAsset.asset_type.in_(RESUME_TYPES))
        .count()
    )


def _serialize(asset):
    return ProfileAssetOut(
        id=asset.id,
        asset_type=asset.asset_type,
        title=asset.title or '',
        url=asset.url or '',
        filename=asset.filename or '',
        created_at=asset.created_at.isoformat() if asset.created_at else None,
    )


@router.get('', response_model=list[ProfileAssetOut])
def list_assets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    assets = (
        db.query(UserProfileAsset)
        .filter(UserProfileAsset.user_id == user.id)
        .order_by(UserProfileAsset.created_at.desc())
        .all()
    )
    return [_serialize(a) for a in assets]


@router.post('/resume', response_model=ProfileAssetOut)
def upload_resume(
    title: str = Form(''),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename = (file.filename or '').strip()
    if not filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='Only PDF resumes are supported')
    data = file.file.read()
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail='Resume PDF is too large (max 10 MB)')
    if not data.startswith(b'%PDF'):
        raise HTTPException(status_code=400, detail='File is not a valid PDF')

    plan = campaign_service._plan_of(db, user)
    limit = _resume_limit(plan)
    if _resume_count(db, user) >= limit:
        raise HTTPException(
            status_code=403,
            detail=(
                f'Resume limit reached ({limit}). Delete a resume or upgrade to Pro '
                'to keep more.'
            ),
        )

    user_dir = os.path.join(UPLOAD_DIR, str(user.id))
    os.makedirs(user_dir, exist_ok=True)
    stored_name = f'{uuid.uuid4().hex}.pdf'
    stored_path = os.path.join(user_dir, stored_name)
    with open(stored_path, 'wb') as handle:
        handle.write(data)

    text_content = _extract_pdf_text(stored_path)

    asset = UserProfileAsset(
        user_id=user.id,
        asset_type='resume',
        title=(title or filename).strip(),
        filename=filename,
        stored_path=stored_path,
        text_content=text_content,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _serialize(asset)


@router.post('/link', response_model=ProfileAssetOut)
def add_link(
    payload: ProfileAssetIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    asset_type = payload.asset_type
    if asset_type not in LINK_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f'asset_type must be one of: {", ".join(LINK_TYPES)}',
        )
    url = (payload.url or '').strip()
    if not url:
        raise HTTPException(status_code=400, detail='A URL is required')
    if not (url.startswith('http://') or url.startswith('https://')):
        raise HTTPException(status_code=400, detail='URL must start with http:// or https://')

    if asset_type == 'resume_link':
        plan = campaign_service._plan_of(db, user)
        limit = _resume_limit(plan)
        if _resume_count(db, user) >= limit:
            raise HTTPException(
                status_code=403,
                detail=(
                    f'Resume limit reached ({limit}). Delete a resume or upgrade to Pro '
                    'to keep more.'
                ),
            )

    title = (payload.title or '').strip() or _default_title(asset_type, url)
    asset = UserProfileAsset(
        user_id=user.id,
        asset_type=asset_type,
        title=title,
        url=url,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _serialize(asset)


@router.delete('/{asset_id}')
def delete_asset(
    asset_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    asset = (
        db.query(UserProfileAsset)
        .filter(UserProfileAsset.id == asset_id, UserProfileAsset.user_id == user.id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail='Asset not found')
    if asset.stored_path and os.path.exists(asset.stored_path):
        try:
            os.remove(asset.stored_path)
        except OSError:
            pass
    db.delete(asset)
    db.commit()
    return {'status': 'deleted'}


def _extract_pdf_text(path):
    try:
        from pypdf import PdfReader

        reader = PdfReader(path)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or '')
        return '\n'.join(pages).strip()[:20000]
    except Exception:
        return ''


def _default_title(asset_type, url):
    labels = {
        'resume_link': 'Resume link',
        'github': 'GitHub',
        'linkedin': 'LinkedIn',
        'website': 'Personal website',
    }
    host = ''
    try:
        host = (url.split('://', 1)[1].split('/', 1)[0]).strip()
    except IndexError:
        pass
    return f'{labels.get(asset_type, asset_type)}{f" · {host}" if host else ""}'