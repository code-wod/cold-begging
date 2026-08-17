import csv
import io
import logging
import re

import openpyxl
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Recipient, User
from ..schemas import ImportResult, RecipientIn, RecipientOut
from ..security import get_current_user

logger = logging.getLogger('cold_email_agent')

router = APIRouter(prefix='/api/recipients', tags=['recipients'])

EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

REQUIRED_HEADERS = ['email']
COLUMN_ALIASES = {
    'company name': 'company_name',
    'company website': 'company_website',
    'job role': 'job_role',
    'position level': 'position_level',
    'company linkedin url': 'linkedin_url',
    'company linkedin': 'linkedin_url',
    'employee count': 'employee_count',
    'funding status': 'funding_status',
    'recent news/updates': 'recent_news',
    'recent news': 'recent_news',
    'contact person name': 'contact_person_name',
    'contact name': 'contact_person_name',
}


def _parse_rows_from_rows(headers, data_rows):
    normalized = [str(c).strip().lower() if c is not None else '' for c in headers]
    for required in REQUIRED_HEADERS:
        if required not in normalized:
            raise ValueError(f'Missing required column: {required}')
    index = {name: i for i, name in enumerate(normalized)}

    def cell(name):
        return index.get(name)

    rows = []
    for raw in data_rows:
        email = str(raw[cell('email')] or '').strip() if cell('email') is not None and cell('email') < len(raw) else ''
        if not email or not EMAIL_REGEX.match(email):
            rows.append({'email': email, 'valid': False})
            continue
        row = {'email': email, 'valid': True}
        for header, attr in COLUMN_ALIASES.items():
            idx = index.get(header)
            if idx is not None and idx < len(raw) and raw[idx] is not None:
                row[attr] = str(raw[idx]).strip()
            else:
                row.setdefault(attr, '')
        rows.append(row)
    return rows


def _parse_excel(content):
    workbook = openpyxl.load_workbook(io.BytesIO(content))
    worksheet = workbook.active
    rows = list(worksheet.iter_rows(values_only=True))
    if not rows:
        raise ValueError('File is empty')
    return _parse_rows_from_rows(rows[0], rows[1:])


def _parse_csv(content):
    text = content.decode('utf-8-sig', errors='replace')
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError('File is empty')
    return _parse_rows_from_rows(rows[0], rows[1:])


def _parse_upload(file: UploadFile):
    filename = (file.filename or '').lower()
    content = file.file.read()
    try:
        if filename.endswith('.xlsx') or filename.endswith('.xlsm'):
            return _parse_excel(content)
        if filename.endswith('.csv') or filename.endswith('.txt'):
            return _parse_csv(content)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f'Could not parse file: {exc}') from exc
    raise ValueError('Unsupported file type. Upload an .xlsx or .csv file.')


def _existing_emails(db, user_id):
    rows = db.query(Recipient.email).filter(Recipient.user_id == user_id).all()
    return {r[0].lower() for r in rows}


@router.get('', response_model=list[RecipientOut])
def list_recipients(
    search: str = '',
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Recipient).filter(Recipient.user_id == user.id)
    if search:
        query = query.filter(Recipient.email.ilike(f'%{search}%'))
    total = query.count()
    items = query.order_by(Recipient.created_at.desc()).offset(offset).limit(limit).all()
    return [
        RecipientOut(
            id=r.id, email=r.email, company_name=r.company_name, industry=r.industry,
            company_website=r.company_website, job_role=r.job_role, position_level=r.position_level,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in items
    ]


@router.get('/count')
def recipient_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.query(Recipient).filter(Recipient.user_id == user.id).count()
    return {'count': count}


@router.post('', response_model=RecipientOut)
def add_recipient(
    payload: RecipientIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email = payload.email.lower()
    exists = (
        db.query(Recipient).filter(Recipient.user_id == user.id, Recipient.email == email).first()
    )
    if exists:
        raise HTTPException(status_code=409, detail='This recipient already exists')
    recipient = Recipient(user_id=user.id, email=email, **payload.dict(exclude={'email'}))
    db.add(recipient)
    db.commit()
    db.refresh(recipient)
    return RecipientOut(
        id=recipient.id, email=recipient.email, company_name=recipient.company_name,
        industry=recipient.industry, company_website=recipient.company_website,
        job_role=recipient.job_role, position_level=recipient.position_level,
        created_at=recipient.created_at.isoformat() if recipient.created_at else None,
    )


@router.post('/import/preview')
def import_preview(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rows = _parse_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    existing = _existing_emails(db, user.id)
    seen = set()
    preview = []
    for row in rows:
        if not row.get('valid'):
            preview.append({**row, 'duplicate': False, 'will_add': False})
            continue
        dup = row['email'].lower() in existing or row['email'].lower() in seen
        seen.add(row['email'].lower())
        preview.append({**row, 'duplicate': dup, 'will_add': not dup})
    return {
        'rows': preview,
        'valid': sum(1 for r in preview if r.get('valid')),
        'duplicates': sum(1 for r in preview if r.get('duplicate')),
        'invalid': sum(1 for r in preview if not r.get('valid')),
    }


@router.post('/import', response_model=ImportResult)
def import_recipients(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rows = _parse_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    existing = _existing_emails(db, user.id)
    seen = set()
    added = duplicates = invalid = 0
    for row in rows:
        if not row.get('valid'):
            invalid += 1
            continue
        email = row['email'].lower()
        if email in existing or email in seen:
            duplicates += 1
            continue
        seen.add(email)
        db.add(
            Recipient(
                user_id=user.id,
                email=email,
                company_name=row.get('company_name', ''),
                industry=row.get('industry', ''),
                company_website=row.get('company_website', ''),
                job_role=row.get('job_role', ''),
                position_level=row.get('position_level', ''),
                linkedin_url=row.get('linkedin_url', ''),
                employee_count=row.get('employee_count', ''),
                funding_status=row.get('funding_status', ''),
                recent_news=row.get('recent_news', ''),
                contact_person_name=row.get('contact_person_name', ''),
            )
        )
        added += 1
    db.commit()
    return ImportResult(added=added, duplicates=duplicates, invalid=invalid, total=added + duplicates + invalid)


@router.delete('/{recipient_id}')
def delete_recipient(
    recipient_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipient = (
        db.query(Recipient)
        .filter(Recipient.id == recipient_id, Recipient.user_id == user.id)
        .first()
    )
    if not recipient:
        raise HTTPException(status_code=404, detail='Recipient not found')
    db.delete(recipient)
    db.commit()
    return {'ok': True}


@router.post('/bulk-delete')
def bulk_delete(
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ids = payload.get('ids', [])
    db.query(Recipient).filter(Recipient.user_id == user.id, Recipient.id.in_(ids)).delete(
        synchronize_session=False
    )
    db.commit()
    return {'deleted': len(ids)}