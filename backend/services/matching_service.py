import json
import logging
import datetime as dt
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from backend.models import User, Resume, Job, Application, JobPreferences, AIModel
from backend.ai import provider_for, is_managed
from backend.encryption import decrypt_plaintext
from backend.config import AUTO_PREPARE_THRESHOLD, REVIEW_THRESHOLD
from backend.database import SessionLocal

logger = logging.getLogger('matching_service')


class MatchingService:
    """Service for AI-powered job matching and application preparation."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_profile_context(self, user: User) -> str:
        """Build user profile context from preferences and resume."""
        prefs = self.db.query(JobPreferences).filter(JobPreferences.user_id == user.id).first()
        default_resume = self.db.query(Resume).filter(
            Resume.user_id == user.id,
            Resume.is_default.is_(True)
        ).first()
        
        parts = []
        
        if prefs:
            if prefs.preferred_roles:
                try:
                    roles = json.loads(prefs.preferred_roles)
                    parts.append(f"Preferred Roles: {', '.join(roles)}")
                except json.JSONDecodeError:
                    pass
            
            if prefs.skills:
                try:
                    skills = json.loads(prefs.skills)
                    parts.append(f"Skills: {', '.join(skills)}")
                except json.JSONDecodeError:
                    pass
            
            if prefs.preferred_locations:
                try:
                    locations = json.loads(prefs.preferred_locations)
                    parts.append(f"Preferred Locations: {', '.join(locations)}")
                except json.JSONDecodeError:
                    pass
            
            if prefs.employment_types:
                try:
                    types = json.loads(prefs.employment_types)
                    parts.append(f"Employment Types: {', '.join(types)}")
                except json.JSONDecodeError:
                    pass
            
            if prefs.experience_levels:
                try:
                    levels = json.loads(prefs.experience_levels)
                    parts.append(f"Experience Levels: {', '.join(levels)}")
                except json.JSONDecodeError:
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
                    parts.append(f"Resume Skills: {', '.join(skills)}")
                except json.JSONDecodeError:
                    pass
        
        return '\n'.join(parts) if parts else 'No profile information available.'
    
    def get_ai_provider(self, user: User, model_id: Optional[int] = None):
        """Get AI provider for matching."""
        model = None
        if model_id:
            model = self.db.query(AIModel).filter(AIModel.id == model_id).first()
        
        if not model:
            # Try user's default model
            model = self.db.query(AIModel).filter(
                AIModel.user_id == user.id,
                AIModel.is_default.is_(True)
            ).first()
        
        if not model:
            # Try free platform model
            model = self.db.query(AIModel).filter(
                AIModel.is_platform.is_(True),
                AIModel.price_usd == 0
            ).first()
        
        if not model:
            raise RuntimeError('No AI model configured for matching')
        
        if is_managed(model):
            from backend.ai import AnthropicProvider
            from backend.config import MANAGED_MODEL_NAME
            return AnthropicProvider(), MANAGED_MODEL_NAME, 1000, 0.7
        
        api_key = decrypt_plaintext(model.api_key_encrypted) if model.api_key_encrypted else None
        provider = provider_for(model, api_key=api_key)
        if not provider:
            raise RuntimeError(f'Failed to create provider for model {model.name}')
        
        return provider, model.model, model.max_tokens or 1000, model.temperature or 0.7
    
    def match_job(self, user: User, job: Job, model_id: Optional[int] = None) -> Dict[str, Any]:
        """Run AI matching between user profile and job."""
        try:
            provider, model_name, max_tokens, temperature = self.get_ai_provider(user, model_id)
        except RuntimeError as e:
            logger.warning('No AI provider for user %d: %s', user.id, e)
            return self._fallback_match(user, job)
        
        profile_context = self.get_user_profile_context(user)
        job_skills = []
        try:
            job_skills = json.loads(job.skills) if job.skills else []
        except json.JSONDecodeError:
            pass
        
        prompt = f"""You are an expert career coach. Analyze how well this candidate matches the job.

CANDIDATE PROFILE:
{profile_context}

JOB DETAILS:
Title: {job.title}
Company: {job.company_name}
Location: {job.location or 'Not specified'}
Remote Type: {job.remote_type or 'Not specified'}
Employment Type: {job.employment_type or 'Not specified'}
Experience Level: {job.experience_level or 'Not specified'}
Salary Range: {job.salary_min or 0} - {job.salary_max or 0} {job.currency}
Description: {job.description[:3000]}
Requirements: {job.requirements[:2000] if job.requirements else 'Not specified'}
Required Skills: {', '.join(job_skills) if job_skills else 'Not specified'}

OUTPUT FORMAT (JSON only):
{{
  "match_score": 0-100,
  "recommendation": "strong_apply|apply|consider|weak|reject",
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1", "skill2"],
  "experience_match": true/false,
  "location_match": true/false,
  "reasoning_summary": "Brief explanation of the match",
  "risk_factors": ["factor1", "factor2"],
  "recommended_resume_type": "backend|frontend|fullstack|general"
}}

Scoring Guidelines:
- 90-100: Excellent match, strong_apply
- 80-89: Strong match, apply
- 70-79: Good match, consider
- 60-69: Weak match, weak
- <60: Poor match, reject

Be strict and honest. Never inflate scores. Consider:
1. Skills overlap (required vs candidate)
2. Experience level alignment
3. Location/remote preference match
4. Salary expectations
5. Domain relevance"""

        try:
            response = provider.complete(prompt, model_name, max_tokens, temperature)
            if not response:
                raise RuntimeError('Empty AI response')
            
            # Parse JSON from response
            cleaned = response.replace('```json', '').replace('```', '').strip()
            result = json.loads(cleaned)
            
            # Validate and clamp score
            score = max(0, min(100, int(result.get('match_score', 0))))
            result['match_score'] = score
            
            # Set recommendation based on thresholds
            if score >= AUTO_PREPARE_THRESHOLD:
                result['recommendation'] = 'strong_apply'
            elif score >= REVIEW_THRESHOLD:
                result['recommendation'] = 'apply'
            elif score >= 60:
                result['recommendation'] = 'consider'
            elif score >= 40:
                result['recommendation'] = 'weak'
            else:
                result['recommendation'] = 'reject'
            
            return result
            
        except Exception as e:
            logger.error('AI matching failed for user %d, job %d: %s', user.id, job.id, e)
            return self._fallback_match(user, job)
    
    def _fallback_match(self, user: User, job: Job) -> Dict[str, Any]:
        """Fallback matching without AI."""
        prefs = self.db.query(JobPreferences).filter(JobPreferences.user_id == user.id).first()
        default_resume = self.db.query(Resume).filter(
            Resume.user_id == user.id,
            Resume.is_default.is_(True)
        ).first()
        
        score = 50  # Base score
        matched = []
        missing = []
        reasoning = []
        
        # Skills matching
        job_skills = []
        try:
            job_skills = [s.lower() for s in json.loads(job.skills)] if job.skills else []
        except json.JSONDecodeError:
            pass
        
        user_skills = []
        if prefs and prefs.skills:
            try:
                user_skills = [s.lower() for s in json.loads(prefs.skills)]
            except json.JSONDecodeError:
                pass
        if default_resume and default_resume.skills:
            try:
                user_skills.extend([s.lower() for s in json.loads(default_resume.skills)])
            except json.JSONDecodeError:
                pass
        
        user_skills = list(set(user_skills))
        
        for skill in job_skills:
            if skill in user_skills:
                matched.append(skill)
                score += 5
            else:
                missing.append(skill)
                score -= 3
        
        # Location match
        location_match = False
        if prefs and prefs.preferred_locations:
            try:
                preferred = [l.lower() for l in json.loads(prefs.preferred_locations)]
                job_loc = (job.location or '').lower()
                if any(p in job_loc or job_loc in p for p in preferred):
                    location_match = True
                    score += 10
                    reasoning.append('Location matches preference')
            except json.JSONDecodeError:
                pass
        
        # Remote preference
        if prefs and prefs.remote_preference != 'any':
            if prefs.remote_preference == 'remote_only' and job.remote_type == 'remote':
                score += 10
                reasoning.append('Remote position matches preference')
            elif prefs.remote_preference == 'hybrid_or_remote' and job.remote_type in ('remote', 'hybrid'):
                score += 5
                reasoning.append('Remote/hybrid matches preference')
        
        # Experience level
        experience_match = False
        if prefs and prefs.experience_levels:
            try:
                preferred = [l.lower() for l in json.loads(prefs.experience_levels)]
                job_level = (job.experience_level or '').lower()
                if job_level in preferred:
                    experience_match = True
                    score += 10
                    reasoning.append('Experience level matches')
            except json.JSONDecodeError:
                pass
        
        # Salary
        if prefs and prefs.minimum_salary and job.salary_max:
            if job.salary_max >= prefs.minimum_salary:
                score += 5
                reasoning.append('Salary meets minimum')
            else:
                score -= 10
                reasoning.append('Salary below minimum')
        
        score = max(0, min(100, score))
        
        if score >= AUTO_PREPARE_THRESHOLD:
            recommendation = 'strong_apply'
        elif score >= REVIEW_THRESHOLD:
            recommendation = 'apply'
        elif score >= 60:
            recommendation = 'consider'
        elif score >= 40:
            recommendation = 'weak'
        else:
            recommendation = 'reject'
        
        return {
            'match_score': score,
            'recommendation': recommendation,
            'matched_skills': matched[:10],
            'missing_skills': missing[:10],
            'experience_match': experience_match,
            'location_match': location_match,
            'reasoning_summary': '; '.join(reasoning) if reasoning else 'Basic keyword matching',
            'risk_factors': [],
            'recommended_resume_type': default_resume.resume_type if default_resume else 'general'
        }
    
    def prepare_application(
        self,
        user: User,
        job: Job,
        match_result: Dict[str, Any],
        model_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate application package for a job."""
        try:
            provider, model_name, max_tokens, temperature = self.get_ai_provider(user, model_id)
        except RuntimeError as e:
            logger.warning('No AI provider for user %d: %s', user.id, e)
            return self._fallback_application(user, job, match_result)
        
        profile_context = self.get_user_profile_context(user)
        
        # Get recommended resume
        recommended_type = match_result.get('recommended_resume_type', 'general')
        resume = self.db.query(Resume).filter(
            Resume.user_id == user.id,
            Resume.resume_type == recommended_type
        ).first()
        if not resume:
            resume = self.db.query(Resume).filter(
                Resume.user_id == user.id,
                Resume.is_default.is_(True)
            ).first()
        
        # Generate cover letter
        cover_letter = self._generate_cover_letter(provider, model_name, max_tokens, temperature, user, job, profile_context, resume)
        
        # Generate screening answers
        screening_answers = self._generate_screening_answers(provider, model_name, max_tokens, temperature, user, job, profile_context)
        
        # Generate recruiter email
        recruiter_email = self._generate_recruiter_email(provider, model_name, max_tokens, temperature, user, job, profile_context)
        
        return {
            'cover_letter': cover_letter,
            'screening_answers': screening_answers,
            'recruiter_email': recruiter_email,
            'recommended_resume_id': resume.id if resume else None,
            'match_analysis': match_result
        }
    
    def _generate_cover_letter(self, provider, model_name, max_tokens, temperature, user, job, profile_context, resume) -> str:
        """Generate tailored cover letter."""
        resume_text = resume.text_content[:2000] if resume and resume.text_content else 'Resume not available'
        
        prompt = f"""Write a compelling, tailored cover letter for this job application.

CANDIDATE PROFILE:
{profile_context}

RESUME ({resume.name if resume else 'Default'}):
{resume_text}

JOB:
Title: {job.title}
Company: {job.company_name}
Description: {job.description[:2000]}
Requirements: {job.requirements[:1500] if job.requirements else 'Not specified'}

REQUIREMENTS:
1. Address the hiring manager personally if possible
2. Reference specific company achievements/products
3. Connect 2-3 key experiences to job requirements
4. Show genuine interest in the company/role
5. Professional but conversational tone
6. 3-4 paragraphs max
7. NO generic templates - MUST be specific to this company/role
8. Do NOT invent experience, skills, or achievements
9. If information is not in the profile, don't mention it

Format as plain text, no markdown."""

        response = provider.complete(prompt, model_name, max_tokens, temperature)
        return response.strip() if response else self._fallback_cover_letter(user, job, resume)
    
    def _generate_screening_answers(self, provider, model_name, max_tokens, temperature, user, job, profile_context) -> Dict[str, str]:
        """Generate answers to common screening questions."""
        common_questions = [
            "Why are you interested in this role?",
            "What makes you a good fit for this position?",
            "Describe your experience with [key technology from job].",
            "What are your salary expectations?",
            "When can you start?",
            "Do you require visa sponsorship?"
        ]
        
        # Filter to relevant questions based on job
        job_skills = []
        try:
            job_skills = json.loads(job.skills) if job.skills else []
        except json.JSONDecodeError:
            pass
        
        relevant_questions = common_questions[:4]
        if job_skills:
            relevant_questions[2] = f"Describe your experience with {job_skills[0]}."
        
        prompt = f"""Answer these screening questions based ONLY on the candidate's real profile. 
If information is not available, respond with "Not specified in profile - please review."

CANDIDATE PROFILE:
{profile_context}

JOB:
Title: {job.title}
Company: {job.company_name}
Description: {job.description[:1500]}

QUESTIONS:
{chr(10).join(f'{i+1}. {q}' for i, q in enumerate(relevant_questions))}

OUTPUT FORMAT (JSON only):
{{
  "answers": {{
    "question1": "answer1",
    "question2": "answer2"
  }}
}}

Rules:
- NEVER invent experience, companies, degrees, certifications, projects, or skills
- Only use information from the profile above
- Be honest and specific
- If unknown, say "Not specified in profile - please review"
"""

        response = provider.complete(prompt, model_name, max_tokens, temperature)
        try:
            cleaned = response.replace('```json', '').replace('```', '').strip()
            result = json.loads(cleaned)
            return result.get('answers', {})
        except Exception:
            return {q: "Not specified in profile - please review" for q in relevant_questions}
    
    def _generate_recruiter_email(self, provider, model_name, max_tokens, temperature, user, job, profile_context) -> str:
        """Generate cold email to recruiter/hiring manager."""
        prompt = f"""Write a concise, personalized cold email to a recruiter or hiring manager at {job.company_name} for the {job.title} role.

CANDIDATE PROFILE:
{profile_context}

JOB:
Title: {job.title}
Company: {job.company_name}
Description: {job.description[:1500]}

REQUIREMENTS:
1. Short subject line (under 50 chars), personalized to company
2. 2-3 short paragraphs
3. Reference specific company detail
4. Clear value proposition from candidate's real background
5. Low-friction CTA (15-min chat, coffee chat)
6. Professional but warm tone
7. NO generic templates
8. Do NOT invent any facts

Format:
SUBJECT: [subject line]
BODY:
[email body]"""

        response = provider.complete(prompt, model_name, max_tokens, temperature)
        return response.strip() if response else self._fallback_recruiter_email(user, job)
    
    def _fallback_cover_letter(self, user, job, resume) -> str:
        return f"""Dear Hiring Manager,

I am writing to express my interest in the {job.title} position at {job.company_name}. With my background in {resume.resume_type if resume else 'software development'}, I believe I can contribute meaningfully to your team.

{job.company_name}'s work in {job.description[:200] if job.description else 'your industry'} particularly resonates with me. My experience aligns well with your requirements, and I'm eager to bring my skills to this role.

I would welcome the opportunity to discuss how my background matches your needs. Thank you for your consideration.

Best regards,
{user.full_name or 'Candidate'}"""
    
    def _fallback_recruiter_email(self, user, job) -> str:
        return f"""SUBJECT: {job.title} at {job.company_name} - {user.full_name or 'Candidate'}

BODY:
Hi there,

I came across the {job.title} role at {job.company_name} and wanted to reach out directly. My background in software development aligns well with what you're looking for, and I'd love to learn more about the team's current challenges.

Would you be open to a brief 15-minute conversation this week?

Best,
{user.full_name or 'Candidate'}"""
    
    def _fallback_application(self, user, job, match_result) -> Dict[str, Any]:
        return {
            'cover_letter': self._fallback_cover_letter(user, job, None),
            'screening_answers': {
                "Why are you interested in this role?": "Not specified in profile - please review",
                "What makes you a good fit for this position?": "Not specified in profile - please review"
            },
            'recruiter_email': self._fallback_recruiter_email(user, job),
            'recommended_resume_id': None,
            'match_analysis': match_result
        }


def get_matching_service() -> MatchingService:
    db = SessionLocal()
    try:
        return MatchingService(db)
    finally:
        db.close()