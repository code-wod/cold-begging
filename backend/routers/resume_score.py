import json
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import User, Resume, JobPreferences, Subscription
from backend.security import get_current_user

logger = logging.getLogger('resume_score')

router = APIRouter(prefix='/api/resume-score', tags=['resume-score'])

# Plan limits for resume score checks
LIMITS = {
    'free': 10,
    'starter': 50,
    'pro': 999999,  # unlimited
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_plan(db: Session, user: User) -> str:
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    return sub.plan if sub else 'free'


@router.get('/usage')
def get_usage(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get remaining resume score checks."""
    plan = _get_plan(db, user)
    used = user.resume_score_checks or 0
    limit = LIMITS.get(plan, LIMITS['free'])
    remaining = max(0, limit - used) if limit < 999999 else -1  # -1 = unlimited
    return {
        'used': used,
        'limit': limit if limit < 999999 else None,
        'remaining': remaining,
        'plan': plan,
        'is_unlimited': limit >= 999999,
    }


@router.post('')
async def score_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a resume PDF and get an AI-powered score with improvement tips."""
    plan = _get_plan(db, user)
    used = user.resume_score_checks or 0
    limit = LIMITS.get(plan, LIMITS['free'])

    if limit < 999999 and used >= limit:
        raise HTTPException(
            status_code=402,
            detail=f'Resume score limit reached ({limit} checks for {plan} plan). Upgrade for more checks.',
        )

    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='Only PDF files are allowed')

    # Read and extract text
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail='File too large (max 10MB)')

    text_content = ''
    try:
        import pypdf
        import io
        reader = pypdf.PdfReader(io.BytesIO(content))
        for page in reader.pages:
            text_content += page.extract_text() or ''
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to read PDF: {str(e)}')

    if not text_content.strip():
        raise HTTPException(status_code=400, detail='Could not extract text from PDF')

    # Extract skills
    common_skills = [
        'Python', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'Java', 'C++', 'C#',
        'React', 'Vue', 'Angular', 'Next.js', 'Node.js', 'Django', 'Flask', 'FastAPI',
        'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch', 'DynamoDB',
        'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes', 'Terraform', 'Ansible',
        'Git', 'CI/CD', 'Jenkins', 'GitHub Actions', 'GitLab CI',
        'GraphQL', 'REST', 'gRPC', 'Kafka', 'RabbitMQ',
        'Machine Learning', 'TensorFlow', 'PyTorch', 'NLP',
        'Agile', 'Scrum', 'Jira', 'Confluence',
    ]
    text_lower = text_content.lower()
    detected_skills = [s for s in common_skills if s.lower() in text_lower]

    # Try AI scoring
    score_result = None
    try:
        from backend.models import AIModel
        from backend.ai import provider_for, is_managed
        from backend.encryption import decrypt_plaintext

        model = db.query(AIModel).filter(
            AIModel.user_id == user.id, AIModel.is_default.is_(True)
        ).first()
        if not model:
            model = db.query(AIModel).filter(
                AIModel.is_platform.is_(True), AIModel.price_usd == 0
            ).first()

        if model:
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
                    raise RuntimeError('No provider')

            prompt = f"""You are an expert career coach and resume reviewer. Score this resume and provide actionable feedback.

RESUME CONTENT:
{text_content[:4000]}

Detected skills: {', '.join(detected_skills) if detected_skills else 'None detected'}

Return ONLY a JSON object (no markdown fences):
{{
  "overall_score": 0-100,
  "sections": {{
    "contact_info": {{"score": 0-100, "feedback": "brief feedback"}},
    "experience": {{"score": 0-100, "feedback": "brief feedback"}},
    "skills": {{"score": 0-100, "feedback": "brief feedback"}},
    "education": {{"score": 0-100, "feedback": "brief feedback"}},
    "formatting": {{"score": 0-100, "feedback": "brief feedback"}}
  }},
  "strengths": ["strength1", "strength2", "strength3"],
  "improvements": ["improvement1", "improvement2", "improvement3"],
  "missing_keywords": ["keyword1", "keyword2"],
  "summary": "One paragraph overall assessment"
}}

Scoring guide:
- 90-100: Excellent, ATS-optimized
- 75-89: Good, minor improvements needed
- 50-74: Average, several improvements needed
- Below 50: Needs significant work

Be specific and actionable. Focus on what matters most for ATS systems and recruiters."""

            response = provider.complete(model_name, prompt, 1500, 0.3)
            if response:
                cleaned = response.replace('```json', '').replace('```', '').strip()
                score_result = json.loads(cleaned)
                score_result['overall_score'] = max(0, min(100, int(score_result.get('overall_score', 0))))

    except Exception as e:
        logger.warning('AI resume scoring failed: %s', e)

    # Fallback scoring if AI failed
    if not score_result:
        score_result = _fallback_score(text_content, detected_skills)

    # Increment check count
    user.resume_score_checks = (user.resume_score_checks or 0) + 1
    db.commit()

    remaining_limit = LIMITS.get(plan, LIMITS['free'])
    remaining = max(0, remaining_limit - user.resume_score_checks) if remaining_limit < 999999 else -1

    return {
        'score': score_result,
        'detected_skills': detected_skills,
        'text_length': len(text_content),
        'checks_remaining': remaining,
        'plan': plan,
    }


def _fallback_score(text: str, skills: list) -> dict:
    """Keyword-based fallback scoring."""
    text_lower = text.lower()
    lines = text.split('\n')
    non_empty = [l.strip() for l in lines if l.strip()]

    # Contact info
    has_email = '@' in text_lower
    has_phone = any(c.isdigit() for c in text) and ('phone' in text_lower or '+' in text or len([c for c in text if c.isdigit()]) >= 7)
    has_linkedin = 'linkedin' in text_lower
    contact_score = sum([has_email * 30, has_phone * 30, has_linkin * 20, (len(non_empty) > 5) * 20])

    # Experience
    has_experience = any(w in text_lower for w in ['experience', 'worked', 'employment', 'career'])
    has_dates = any(w in text_lower for w in ['2020', '2021', '2022', '2023', '2024', '2025', '2026', 'present'])
    exp_score = min(100, (has_experience * 40) + (has_dates * 30) + (len(non_empty) > 15) * 30)

    # Skills
    skills_score = min(100, len(skills) * 10)

    # Education
    has_edu = any(w in text_lower for w in ['education', 'university', 'college', 'bachelor', 'master', 'degree', 'b.s.', 'm.s.', 'phd'])
    edu_score = 100 if has_edu else 30

    # Formatting
    fmt_score = min(100, (len(non_empty) > 10) * 30 + (len(non_empty) > 20) * 30 + (len(text) > 500) * 20 + 20)

    overall = int((contact_score + exp_score + skills_score + edu_score + fmt_score) / 5)

    return {
        'overall_score': overall,
        'sections': {
            'contact_info': {'score': contact_score, 'feedback': 'Add email, phone, and LinkedIn if missing'},
            'experience': {'score': exp_score, 'feedback': 'Include dates and detailed descriptions'},
            'skills': {'score': skills_score, 'feedback': f'Detected {len(skills)} skills — add more relevant keywords'},
            'education': {'score': edu_score, 'feedback': 'Add education section if missing'},
            'formatting': {'score': fmt_score, 'feedback': 'Use clear sections and bullet points'},
        },
        'strengths': [f'Detected {len(skills)} technical skills'] if skills else ['Has readable text content'],
        'improvements': [
            'Add more quantified achievements (numbers, percentages)',
            'Include relevant keywords from job descriptions',
            'Use a clean, ATS-friendly format',
        ],
        'missing_keywords': ['metrics/quantified results', 'action verbs', 'ATS keywords'],
        'summary': 'This is a basic heuristic score. Configure an AI model for detailed, personalized resume feedback.',
    }
