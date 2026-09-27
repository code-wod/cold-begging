from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import zipfile
import io
import hashlib
import json
import datetime as dt

from ..database import get_db
from ..security import get_current_user
from ..models import User, Job, Resume, JobPreferences, AIModel
from ..ai import provider_for, is_managed
from ..encryption import decrypt_plaintext
from ..extension_models import (
    ExtensionProfile,
    ExtensionLearnedAnswer,
    ExtensionSession,
)

router = APIRouter(prefix='/api/extension', tags=['extension'])


# ── Pydantic Schemas ─────────────────────────────────────────────────────────

class AddressSchema(BaseModel):
    street: Optional[str] = ''
    city: Optional[str] = ''
    state: Optional[str] = ''
    country: Optional[str] = ''
    postalCode: Optional[str] = ''

class PersonalInfo(BaseModel):
    firstName: Optional[str] = ''
    middleName: Optional[str] = ''
    lastName: Optional[str] = ''
    fullName: Optional[str] = ''
    email: Optional[str] = ''
    phone: Optional[str] = ''
    address: Optional[AddressSchema] = AddressSchema()

class ProfessionalInfo(BaseModel):
    currentTitle: Optional[str] = ''
    yearsOfExperience: Optional[str] = ''
    skills: Optional[List[str]] = []
    linkedin: Optional[str] = ''
    github: Optional[str] = ''
    portfolio: Optional[str] = ''
    currentCompany: Optional[str] = ''

class EducationInfo(BaseModel):
    degree: Optional[str] = ''
    field: Optional[str] = ''
    school: Optional[str] = ''
    graduationYear: Optional[str] = ''

class WorkAuthInfo(BaseModel):
    authorizedToWork: Optional[bool] = False
    requiresSponsorship: Optional[bool] = False
    willingToRelocate: Optional[bool] = False

class PreferencesInfo(BaseModel):
    remotePreference: Optional[str] = ''
    noticePeriod: Optional[str] = ''
    salaryExpectation: Optional[str] = ''

class DocumentsInfo(BaseModel):
    resumePath: Optional[str] = ''
    resumeName: Optional[str] = ''
    coverLetterPath: Optional[str] = ''

class ProfileUpdate(BaseModel):
    personal: Optional[PersonalInfo] = None
    professional: Optional[ProfessionalInfo] = None
    education: Optional[List[EducationInfo]] = None
    workAuthorization: Optional[WorkAuthInfo] = None
    preferences: Optional[PreferencesInfo] = None
    documents: Optional[DocumentsInfo] = None
    customAnswers: Optional[Dict[str, str]] = None


class LearnedAnswerCreate(BaseModel):
    question: str
    answer: str
    scope: Optional[str] = 'global'
    company: Optional[str] = ''
    job_title: Optional[str] = ''


class SemanticMapRequest(BaseModel):
    fields: List[Dict[str, Optional[str]]]


class AnalyzeRequest(BaseModel):
    url: str
    fields: List[Dict[str, Any]]


class SessionCreate(BaseModel):
    url: str
    company: Optional[str] = ''
    job_title: Optional[str] = ''
    platform: Optional[str] = ''
    fields_detected: Optional[int] = 0
    fields_filled: Optional[int] = 0
    duration_seconds: Optional[int] = 0


class MatchScoreRequest(BaseModel):
    title: str
    company: str
    location: Optional[str] = ''
    description: Optional[str] = ''
    requirements: Optional[str] = ''


class JobCreate(BaseModel):
    title: str
    company: str
    url: Optional[str] = ''
    location: Optional[str] = ''
    description: Optional[str] = ''
    platform: Optional[str] = ''
    salary: Optional[str] = ''
    employment_type: Optional[str] = ''
    remote_type: Optional[str] = ''


# ── Profile Endpoints ────────────────────────────────────────────────────────

@router.get('/profile')
def get_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = db.query(ExtensionProfile).filter(
        ExtensionProfile.user_id == user.id
    ).first()

    if not profile:
        profile = ExtensionProfile(user_id=user.id, email=user.email or '')
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return _profile_to_dict(profile)


@router.put('/profile')
def update_profile(
    body: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = db.query(ExtensionProfile).filter(
        ExtensionProfile.user_id == user.id
    ).first()

    if not profile:
        profile = ExtensionProfile(user_id=user.id)
        db.add(profile)

    if body.personal:
        p = body.personal
        profile.first_name = p.firstName or profile.first_name
        profile.middle_name = p.middleName or profile.middle_name
        profile.last_name = p.lastName or profile.last_name
        profile.full_name = p.fullName or profile.full_name
        profile.email = p.email or profile.email
        profile.phone = p.phone or profile.phone
        if p.address:
            profile.street = p.address.street or profile.street
            profile.city = p.address.city or profile.city
            profile.state = p.address.state or profile.state
            profile.country = p.address.country or profile.country
            profile.postal_code = p.address.postalCode or profile.postal_code

    if body.professional:
        pr = body.professional
        profile.current_title = pr.currentTitle or profile.current_title
        profile.years_of_experience = pr.yearsOfExperience or profile.years_of_experience
        profile.current_company = pr.currentCompany or profile.current_company
        profile.linkedin = pr.linkedin or profile.linkedin
        profile.github = pr.github or profile.github
        profile.portfolio = pr.portfolio or profile.portfolio
        if pr.skills is not None:
            profile.skills = pr.skills

    if body.education is not None:
        profile.education = [e.dict() for e in body.education]

    if body.workAuthorization:
        wa = body.workAuthorization
        profile.authorized_to_work = wa.authorizedToWork if wa.authorizedToWork is not None else profile.authorized_to_work
        profile.requires_sponsorship = wa.requiresSponsorship if wa.requiresSponsorship is not None else profile.requires_sponsorship
        profile.willing_to_relocate = wa.willingToRelocate if wa.willingToRelocate is not None else profile.willing_to_relocate

    if body.preferences:
        pr = body.preferences
        profile.remote_preference = pr.remotePreference or profile.remote_preference
        profile.notice_period = pr.noticePeriod or profile.notice_period
        profile.salary_expectation = pr.salaryExpectation or profile.salary_expectation

    if body.documents:
        d = body.documents
        profile.resume_path = d.resumePath or profile.resume_path
        profile.resume_name = d.resumeName or profile.resume_name
        profile.cover_letter_path = d.coverLetterPath or profile.cover_letter_path

    if body.customAnswers is not None:
        profile.custom_answers = body.customAnswers

    db.commit()
    db.refresh(profile)
    return _profile_to_dict(profile)


# ── Learned Answers Endpoints ────────────────────────────────────────────────

@router.get('/learned-answers')
def get_learned_answers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    answers = db.query(ExtensionLearnedAnswer).filter(
        ExtensionLearnedAnswer.user_id == user.id
    ).order_by(ExtensionLearnedAnswer.updated_at.desc()).all()

    return [_answer_to_dict(a) for a in answers]


@router.post('/learned-answers')
def create_learned_answer(
    body: LearnedAnswerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    normalized = body.question.lower().replace('?', '').replace(':', '').replace('*', '').strip()

    existing = db.query(ExtensionLearnedAnswer).filter(
        ExtensionLearnedAnswer.user_id == user.id,
        ExtensionLearnedAnswer.normalized_question == normalized,
        ExtensionLearnedAnswer.scope == body.scope,
        ExtensionLearnedAnswer.company == (body.company or ''),
    ).first()

    if existing:
        existing.answer = body.answer
        existing.used_count += 1
        db.commit()
        db.refresh(existing)
        return _answer_to_dict(existing)

    answer = ExtensionLearnedAnswer(
        user_id=user.id,
        question=body.question,
        normalized_question=normalized,
        answer=body.answer,
        scope=body.scope,
        company=body.company or '',
        job_title=body.job_title or '',
        source='user',
        confidence=1.0,
        user_confirmed=True,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return _answer_to_dict(answer)


# ── Semantic Mapping Endpoint ────────────────────────────────────────────────

@router.post('/semantic-map')
def semantic_map_fields(
    body: SemanticMapRequest,
    user: User = Depends(get_current_user),
):
    result = {}

    CONCEPT_KEYWORDS = {
        'firstName': ['first name', 'given name', 'prenom'],
        'lastName': ['last name', 'surname', 'family name'],
        'fullName': ['full name', 'name', 'candidate name'],
        'email': ['email', 'e-mail'],
        'phone': ['phone', 'telephone', 'mobile', 'cell'],
        'street': ['street', 'address', 'street address'],
        'city': ['city', 'town'],
        'state': ['state', 'province', 'region'],
        'country': ['country', 'nation'],
        'postalCode': ['postal code', 'zip code', 'zip'],
        'linkedin': ['linkedin'],
        'github': ['github'],
        'portfolio': ['portfolio', 'website', 'url', 'homepage'],
        'currentTitle': ['job title', 'title', 'position', 'role'],
        'yearsExperience': ['years of experience', 'experience', 'yoe'],
        'currentCompany': ['company', 'employer', 'organization'],
        'salary': ['salary', 'compensation', 'pay'],
        'workAuthorization': ['work authorization', 'authorized to work', 'right to work'],
        'requiresSponsorship': ['sponsorship', 'visa', 'h1b'],
        'willingToRelocate': ['relocate', 'relocation'],
        'noticePeriod': ['notice period', 'availability', 'start date'],
    }

    for field in body.fields:
        text = ' '.join([
            field.get('label') or '',
            field.get('name') or '',
            field.get('placeholder') or '',
            field.get('ariaLabel') or '',
            field.get('context') or '',
        ]).lower().strip()

        if not text:
            continue

        best_concept = 'unknown'
        best_confidence = 0.0

        for concept, keywords in CONCEPT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    confidence = 0.85 if len(keyword) > 5 else 0.75
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_concept = concept

        if best_concept != 'unknown':
            field_key = field.get('label') or field.get('name') or field.get('placeholder') or ''
            result[field_key] = {
                'concept': best_concept,
                'confidence': best_confidence,
            }

    return result


# ── Analyze Endpoint ─────────────────────────────────────────────────────────

@router.post('/analyze')
def analyze_fields(
    body: AnalyzeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = db.query(ExtensionProfile).filter(
        ExtensionProfile.user_id == user.id
    ).first()

    if not profile:
        return {'suggestions': []}

    answers = db.query(ExtensionLearnedAnswer).filter(
        ExtensionLearnedAnswer.user_id == user.id
    ).all()
    answer_map = {a.normalized_question: a.answer for a in answers}

    suggestions = []
    for field in body.fields:
        label = (field.get('label') or field.get('name') or field.get('placeholder') or '').lower()
        normalized = label.replace('?', '').replace(':', '').replace('*', '').strip()

        value = None
        confidence = 0.0
        source = 'exact'
        requires_review = True

        value, confidence, source = _match_profile_field(normalized, profile)

        if not value and normalized in answer_map:
            value = answer_map[normalized]
            source = 'learned'
            confidence = 0.85

        if value:
            requires_review = confidence < 0.90

        suggestions.append({
            'fieldId': field.get('id', ''),
            'profilePath': normalized,
            'value': value,
            'confidence': confidence,
            'source': source,
            'requiresReview': requires_review,
        })

    return {'suggestions': suggestions}


def _match_profile_field(label: str, profile: ExtensionProfile):
    mapping = {
        'first name': profile.first_name,
        'firstname': profile.first_name,
        'given name': profile.first_name,
        'last name': profile.last_name,
        'lastname': profile.last_name,
        'surname': profile.last_name,
        'family name': profile.last_name,
        'full name': profile.full_name or f'{profile.first_name} {profile.last_name}'.strip(),
        'name': profile.full_name or f'{profile.first_name} {profile.last_name}'.strip(),
        'email': profile.email,
        'e-mail': profile.email,
        'phone': profile.phone,
        'telephone': profile.phone,
        'mobile': profile.phone,
        'street': profile.street,
        'address': profile.street,
        'street address': profile.street,
        'city': profile.city,
        'state': profile.state,
        'province': profile.state,
        'country': profile.country,
        'postal code': profile.postal_code,
        'zip code': profile.postal_code,
        'zip': profile.postal_code,
        'linkedin': profile.linkedin,
        'github': profile.github,
        'portfolio': profile.portfolio,
        'website': profile.portfolio,
        'job title': profile.current_title,
        'title': profile.current_title,
        'position': profile.current_title,
        'role': profile.current_title,
        'years of experience': profile.years_of_experience,
        'experience': profile.years_of_experience,
        'company': profile.current_company,
        'employer': profile.current_company,
        'notice period': profile.notice_period,
        'salary': profile.salary_expectation,
        'salary expectation': profile.salary_expectation,
        'authorized to work': 'Yes' if profile.authorized_to_work else 'No',
        'requires sponsorship': 'Yes' if profile.requires_sponsorship else 'No',
        'visa sponsorship': 'Yes' if profile.requires_sponsorship else 'No',
        'willing to relocate': 'Yes' if profile.willing_to_relocate else 'No',
    }

    value = mapping.get(label)
    if value:
        return value, 0.90, 'exact'

    for key, val in mapping.items():
        if key in label or label in key:
            if val:
                return val, 0.80, 'synonym'

    return None, 0.0, 'unknown'


# ── Sessions Endpoints ───────────────────────────────────────────────────────

@router.get('/sessions')
def get_sessions(
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sessions = db.query(ExtensionSession).filter(
        ExtensionSession.user_id == user.id
    ).order_by(ExtensionSession.created_at.desc()).limit(limit).all()

    return [{
        'id': s.id,
        'url': s.url,
        'company': s.company,
        'jobTitle': s.job_title,
        'platform': s.platform,
        'fieldsDetected': s.fields_detected,
        'fieldsFilled': s.fields_filled,
        'durationSeconds': s.duration_seconds,
        'completed': s.completed,
        'createdAt': s.created_at.isoformat() if s.created_at else None,
    } for s in sessions]


@router.post('/sessions')
def create_session(
    body: SessionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = ExtensionSession(
        user_id=user.id,
        url=body.url,
        company=body.company or '',
        job_title=body.job_title or '',
        platform=body.platform or '',
        fields_detected=body.fields_detected or 0,
        fields_filled=body.fields_filled or 0,
        duration_seconds=body.duration_seconds or 0,
        completed=True,
    )
    db.add(session)
    db.commit()
    return {'success': True}


# ── Jobs Endpoints ───────────────────────────────────────────────────────────

def _compute_job_hash(company: str, title: str, location: str, url: str) -> str:
    content = f"{company.strip().lower()}|{title.strip().lower()}|{location.strip().lower()}|{url.strip().lower()}"
    return hashlib.sha256(content.encode()).hexdigest()[:64]


@router.post('/jobs')
def save_job_from_extension(
    body: JobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Save a job discovered via the Chrome extension into the main jobs table."""
    job_hash = _compute_job_hash(body.company, body.title, body.location, body.url)

    existing = db.query(Job).filter(Job.job_hash == job_hash).first()
    if existing:
        existing.updated_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
        return {'job_id': existing.id, 'is_new': False}

    job = Job(
        source='extension',
        title=body.title,
        company_name=body.company,
        application_url=body.url or '',
        location=body.location or '',
        remote_type=body.remote_type or '',
        employment_type=body.employment_type or '',
        description=body.description or '',
        job_hash=job_hash,
        source_data=json.dumps({
            'platform': body.platform,
            'salary_text': body.salary,
            'discovered_via': 'chrome_extension',
        }),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {'job_id': job.id, 'is_new': True}


@router.post('/match-score')
def get_match_score(
    body: MatchScoreRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI-powered resume-to-job match score for the Chrome extension."""
    # Build profile context
    prefs = db.query(JobPreferences).filter(JobPreferences.user_id == user.id).first()
    default_resume = db.query(Resume).filter(
        Resume.user_id == user.id,
        Resume.is_default.is_(True)
    ).first()
    # Fallback: any resume if no default set
    if not default_resume:
        default_resume = db.query(Resume).filter(
            Resume.user_id == user.id
        ).order_by(Resume.created_at.desc()).first()

    parts = []
    if prefs:
        for field_name, label in [
            ('preferred_roles', 'Preferred Roles'),
            ('skills', 'Skills'),
            ('preferred_locations', 'Preferred Locations'),
            ('experience_levels', 'Experience Levels'),
        ]:
            val = getattr(prefs, field_name, None)
            if val:
                try:
                    items = json.loads(val)
                    if items:
                        parts.append(f"{label}: {', '.join(items)}")
                except (json.JSONDecodeError, TypeError):
                    pass
        if prefs.minimum_salary:
            parts.append(f"Minimum Salary: {prefs.currency} {prefs.minimum_salary:,}")
        parts.append(f"Remote Preference: {prefs.remote_preference}")

    if default_resume:
        if default_resume.text_content:
            parts.append(f"Resume ({default_resume.name}): {default_resume.text_content[:2000]}")
        if default_resume.skills:
            try:
                skills = json.loads(default_resume.skills)
                if skills:
                    parts.append(f"Resume Skills: {', '.join(skills)}")
            except (json.JSONDecodeError, TypeError):
                pass

    profile_context = '\n'.join(parts) if parts else 'No profile information available.'
    has_resume = default_resume is not None and bool(default_resume.text_content)
    has_preferences = prefs is not None and bool(prefs.preferred_roles)

    # Early return if no resume — can't do meaningful scoring
    if not has_resume:
        return {
            'match_score': 0,
            'recommendation': 'setup_required',
            'matched_skills': [],
            'missing_skills': [],
            'reasoning': '',
            'has_resume': False,
            'has_preferences': has_preferences,
        }

    # Find AI provider
    model = db.query(AIModel).filter(AIModel.user_id == user.id, AIModel.is_default.is_(True)).first()
    if not model:
        model = db.query(AIModel).filter(AIModel.is_platform.is_(True), AIModel.price_usd == 0).first()

    if not model:
        # Fallback: keyword-based scoring
        return _fallback_score(profile_context, body, has_resume, has_preferences)

    try:
        if is_managed(model):
            from backend.ai import AnthropicProvider
            from backend.config import MANAGED_MODEL_NAME
            provider = AnthropicProvider()
            model_name = MANAGED_MODEL_NAME
        else:
            api_key = decrypt_plaintext(model.api_key_encrypted) if model.api_key_encrypted else None
            provider = provider_for(model, api_key=api_key)
            model_name = model.model
            if not provider:
                return _fallback_score(profile_context, body, has_resume, has_preferences)

        prompt = f"""You are an expert career coach. Score how well this candidate matches the job.

CANDIDATE PROFILE:
{profile_context}

JOB:
Title: {body.title}
Company: {body.company}
Location: {body.location or 'Not specified'}
Description: {(body.description or '')[:3000]}
Requirements: {(body.requirements or '')[:2000]}

Return ONLY a JSON object (no markdown, no explanation):
{{
  "match_score": 0-100,
  "recommendation": "strong_apply|apply|consider|weak|reject",
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1", "skill2"],
  "reasoning": "One sentence explanation"
}}

Scoring: 90-100=strong_apply, 80-89=apply, 70-79=consider, 60-69=weak, <60=reject.
Be strict and honest. Never inflate scores."""

        response = provider.complete(model_name, prompt, 600, 0.3)
        if not response:
            return _fallback_score(profile_context, body, has_resume, has_preferences)

        cleaned = response.replace('```json', '').replace('```', '').strip()
        result = json.loads(cleaned)

        score = max(0, min(100, int(result.get('match_score', 0))))
        result['match_score'] = score
        result['has_resume'] = has_resume
        result['has_preferences'] = has_preferences

        if score >= 80:
            result['recommendation'] = 'strong_apply'
        elif score >= 70:
            result['recommendation'] = 'apply'
        elif score >= 60:
            result['recommendation'] = 'consider'
        elif score >= 40:
            result['recommendation'] = 'weak'
        else:
            result['recommendation'] = 'reject'

        return result

    except Exception as e:
        return _fallback_score(profile_context, body, has_resume, has_preferences)


def _fallback_score(profile_context: str, body: MatchScoreRequest, has_resume: bool = True, has_preferences: bool = True) -> dict:
    """Keyword-based fallback matching when AI is unavailable."""
    profile_lower = profile_context.lower()
    desc_lower = (body.description or '').lower()
    req_lower = (body.requirements or '').lower()
    combined = f"{desc_lower} {req_lower}"

    # Extract common tech skills from job description
    common_skills = [
        'python', 'javascript', 'typescript', 'go', 'rust', 'java', 'c++', 'c#',
        'react', 'vue', 'angular', 'next.js', 'node.js', 'django', 'flask', 'fastapi',
        'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
        'aws', 'gcp', 'azure', 'docker', 'kubernetes', 'terraform',
        'git', 'ci/cd', 'jenkins', 'github actions',
        'graphql', 'rest', 'grpc', 'kafka', 'rabbitmq',
    ]

    matched = [s for s in common_skills if s in combined and s in profile_lower]
    missing = [s for s in common_skills if s in combined and s not in profile_lower]

    score = 50
    score += min(30, len(matched) * 5)
    score -= min(20, len(missing) * 3)
    score = max(0, min(100, score))

    if score >= 80:
        rec = 'strong_apply'
    elif score >= 70:
        rec = 'apply'
    elif score >= 60:
        rec = 'consider'
    elif score >= 40:
        rec = 'weak'
    else:
        rec = 'reject'

    return {
        'match_score': score,
        'recommendation': rec,
        'matched_skills': matched[:10],
        'missing_skills': missing[:10],
        'reasoning': f'Keyword match: {len(matched)} skills found, {len(missing)} missing. (AI unavailable — heuristic score)',
        'has_resume': has_resume,
        'has_preferences': has_preferences,
    }


# ── Documents Endpoint ───────────────────────────────────────────────────────

@router.post('/documents')
async def upload_document(
    file: UploadFile = File(...),
    type: str = Form('resume'),
    user: User = Depends(get_current_user),
):
    upload_dir = f'backend/uploads/{user.id}'
    os.makedirs(upload_dir, exist_ok=True)

    filename = f'{type}_{len(os.listdir(upload_dir))}.pdf'
    filepath = os.path.join(upload_dir, filename)

    content = await file.read()
    with open(filepath, 'wb') as f:
        f.write(content)

    return {'path': filepath, 'name': filename}


# ── Application History ──────────────────────────────────────────────────────

@router.get('/applications')
def get_applications(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all tracked application sessions from the extension."""
    sessions = db.query(ExtensionSession).filter(
        ExtensionSession.user_id == user.id
    ).order_by(ExtensionSession.created_at.desc()).limit(limit).all()

    return [{
        'id': s.id,
        'url': s.url,
        'company': s.company,
        'jobTitle': s.job_title,
        'platform': s.platform,
        'fieldsDetected': s.fields_detected,
        'fieldsFilled': s.fields_filled,
        'durationSeconds': s.duration_seconds,
        'completed': s.completed,
        'createdAt': s.created_at.isoformat() if s.created_at else None,
    } for s in sessions]


@router.get('/stats')
def get_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get extension usage statistics."""
    sessions = db.query(ExtensionSession).filter(
        ExtensionSession.user_id == user.id
    ).all()

    total = len(sessions)
    completed = sum(1 for s in sessions if s.completed)
    total_fields_filled = sum(s.fields_filled or 0 for s in sessions)
    total_fields_detected = sum(s.fields_detected or 0 for s in sessions)

    # Group by company
    companies = {}
    for s in sessions:
        if s.company:
            companies[s.company] = companies.get(s.company, 0) + 1

    # Group by platform
    platforms = {}
    for s in sessions:
        p = s.platform or 'unknown'
        platforms[p] = platforms.get(p, 0) + 1

    return {
        'totalSessions': total,
        'completedSessions': completed,
        'totalFieldsDetected': total_fields_detected,
        'totalFieldsFilled': total_fields_filled,
        'topCompanies': sorted(companies.items(), key=lambda x: -x[1])[:10],
        'platformBreakdown': platforms,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _profile_to_dict(p: ExtensionProfile) -> dict:
    return {
        'personal': {
            'firstName': p.first_name,
            'middleName': p.middle_name,
            'lastName': p.last_name,
            'fullName': p.full_name,
            'email': p.email,
            'phone': p.phone,
            'address': {
                'street': p.street,
                'city': p.city,
                'state': p.state,
                'country': p.country,
                'postalCode': p.postal_code,
            },
        },
        'professional': {
            'currentTitle': p.current_title,
            'yearsOfExperience': p.years_of_experience,
            'skills': p.skills or [],
            'linkedin': p.linkedin,
            'github': p.github,
            'portfolio': p.portfolio,
            'currentCompany': p.current_company,
        },
        'education': p.education or [],
        'workAuthorization': {
            'authorizedToWork': p.authorized_to_work,
            'requiresSponsorship': p.requires_sponsorship,
            'willingToRelocate': p.willing_to_relocate,
        },
        'preferences': {
            'remotePreference': p.remote_preference,
            'noticePeriod': p.notice_period,
            'salaryExpectation': p.salary_expectation,
        },
        'documents': {
            'resumePath': p.resume_path,
            'resumeName': p.resume_name,
            'coverLetterPath': p.cover_letter_path,
        },
        'customAnswers': p.custom_answers or {},
    }


def _answer_to_dict(a: ExtensionLearnedAnswer) -> dict:
    return {
        'id': str(a.id),
        'question': a.question,
        'normalizedQuestion': a.normalized_question,
        'answer': a.answer,
        'answerType': a.answer_type,
        'scope': a.scope,
        'source': a.source,
        'confidence': a.confidence,
        'userConfirmed': a.user_confirmed,
        'usedCount': a.used_count,
        'company': a.company,
        'jobTitle': a.job_title,
        'createdAt': a.created_at.isoformat() if a.created_at else None,
        'updatedAt': a.updated_at.isoformat() if a.updated_at else None,
    }


# ── Extension Download ───────────────────────────────────────────────────────

EXTENSION_ZIP_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'extension', 'cold-begging-extension.zip')


@router.get('/download')
def download_extension():
    """Download the extension ZIP for sideloading into Chrome."""
    zip_path = os.path.abspath(EXTENSION_ZIP_PATH)
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail='Extension not built yet. Run the build script first.')
    return FileResponse(
        zip_path,
        media_type='application/zip',
        filename='cold-begging-extension.zip',
    )


@router.get('/version')
def extension_version():
    """Return extension version info."""
    return {
        'version': '1.0.0',
        'name': 'Cold-Begging Autofill',
        'description': 'Universal job application autofill — paste your profile once, fill every application instantly.',
        'minChromeVersion': 114,
    }
