import json
import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from backend.models_job_application import JobProfile, AutofillApplication, AutofillField

logger = logging.getLogger('job_profile_service')


class JobProfileService:
    """Service for job profile CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user_id: int) -> JobProfile:
        """Get existing profile or create a new one."""
        profile = self.db.query(JobProfile).filter(JobProfile.user_id == user_id).first()
        if not profile:
            profile = JobProfile(user_id=user_id)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    def get(self, user_id: int) -> Optional[JobProfile]:
        """Get user's job profile."""
        return self.db.query(JobProfile).filter(JobProfile.user_id == user_id).first()

    def update(self, user_id: int, data: dict) -> JobProfile:
        """Update user's job profile. Creates one if it doesn't exist."""
        profile = self.get(user_id)
        if not profile:
            profile = JobProfile(user_id=user_id)
            self.db.add(profile)

        # Simple scalar fields
        simple_fields = [
            'first_name', 'middle_name', 'last_name', 'preferred_name',
            'email', 'phone', 'country', 'state', 'city', 'address', 'postal_code',
            'current_title', 'current_company', 'years_of_experience',
            'linkedin_url', 'github_url', 'portfolio_url', 'personal_website',
            'degree', 'field_of_study', 'university', 'graduation_year', 'gpa',
            'authorized_to_work', 'requires_sponsorship',
            'remote_preference', 'employment_type', 'notice_period',
            'expected_salary', 'expected_salary_currency',
            'willing_to_relocate', 'willing_to_travel',
        ]

        for field in simple_fields:
            if field in data:
                setattr(profile, field, data[field])

        # JSON array fields
        json_array_fields = [
            'work_authorization_countries', 'preferred_locations',
            'programming_languages', 'frameworks', 'databases', 'tools', 'other_skills',
            'education_history', 'experience_history', 'projects', 'certifications',
        ]

        for field in json_array_fields:
            if field in data:
                profile.set_json_field(field, data[field])

        # JSON dict fields
        json_dict_fields = ['common_answers', 'eeoo_answers', 'custom_answers']

        for field in json_dict_fields:
            if field in data:
                setattr(profile, field, json.dumps(data[field] or {}))

        self.db.commit()
        self.db.refresh(profile)
        return profile


class AutofillApplicationService:
    """Service for autofill application operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, job_url: str, resume_id: int = None) -> AutofillApplication:
        """Create a new autofill application."""
        app = AutofillApplication(
            user_id=user_id,
            job_url=job_url,
            resume_id=resume_id,
            status='preparing',
        )
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        return app

    def get(self, application_id: int, user_id: int) -> Optional[AutofillApplication]:
        """Get a specific application, ensuring user ownership."""
        return self.db.query(AutofillApplication).filter(
            AutofillApplication.id == application_id,
            AutofillApplication.user_id == user_id,
        ).first()

    def list_user_applications(
        self, user_id: int, status: str = None, limit: int = 50, offset: int = 0
    ):
        """List user's applications with optional status filter."""
        query = self.db.query(AutofillApplication).filter(
            AutofillApplication.user_id == user_id
        )
        if status:
            query = query.filter(AutofillApplication.status == status)
        total = query.count()
        items = query.order_by(AutofillApplication.created_at.desc()).offset(offset).limit(limit).all()
        return {'items': items, 'total': total}

    def update_status(self, application_id: int, user_id: int, status: str, **kwargs) -> Optional[AutofillApplication]:
        """Update application status and optional fields."""
        app = self.get(application_id, user_id)
        if not app:
            return None
        app.status = status
        for key, val in kwargs.items():
            if hasattr(app, key):
                setattr(app, key, val)
        self.db.commit()
        self.db.refresh(app)
        return app

    def set_fields(self, application_id: int, fields_data: list) -> list:
        """Bulk set extracted fields for an application."""
        # Delete existing fields
        self.db.query(AutofillField).filter(
            AutofillField.application_id == application_id
        ).delete()

        created = []
        for i, fd in enumerate(fields_data):
            field = AutofillField(
                application_id=application_id,
                field_label=fd.get('field_label', ''),
                field_name=fd.get('field_name', ''),
                field_id=fd.get('field_id', ''),
                field_type=fd.get('field_type', 'text'),
                field_selector=fd.get('field_selector', ''),
                placeholder=fd.get('placeholder', ''),
                aria_label=fd.get('aria_label', ''),
                section=fd.get('section', ''),
                options=json.dumps(fd.get('options', [])),
                profile_field=fd.get('profile_field', ''),
                mapped_value=fd.get('mapped_value', ''),
                confidence=fd.get('confidence', 0.0),
                mapping_reasoning=fd.get('mapping_reasoning', ''),
                requires_review=fd.get('requires_review', False),
                status=fd.get('status', 'pending'),
                order=i,
            )
            self.db.add(field)
            created.append(field)

        self.db.commit()
        return created

    def get_fields(self, application_id: int) -> list:
        """Get all fields for an application."""
        return self.db.query(AutofillField).filter(
            AutofillField.application_id == application_id
        ).order_by(AutofillField.order).all()

    def update_field(self, field_id: int, application_id: int, user_value: str = None, skipped: bool = None) -> Optional[AutofillField]:
        """Update a single field (user edit)."""
        field = self.db.query(AutofillField).filter(
            AutofillField.id == field_id,
            AutofillField.application_id == application_id,
        ).first()
        if not field:
            return None
        if user_value is not None:
            field.user_value = user_value
            field.user_edited = True
            field.status = 'mapped'
        if skipped is not None:
            field.skipped = skipped
            if skipped:
                field.status = 'skipped'
        self.db.commit()
        self.db.refresh(field)
        return field

    def get_stats(self, application_id: int) -> dict:
        """Get field statistics for an application."""
        fields = self.get_fields(application_id)
        total = len(fields)
        auto_filled = sum(1 for f in fields if f.status == 'filled' and not f.requires_review)
        needs_review = sum(1 for f in fields if f.requires_review and not f.skipped)
        unanswered = sum(1 for f in fields if f.status == 'pending' and not f.skipped)
        skipped = sum(1 for f in fields if f.skipped)
        return {
            'total_fields': total,
            'auto_filled': auto_filled,
            'needs_review': needs_review,
            'unanswered': unanswered,
            'skipped': skipped,
        }
