"""Deterministic field mapping from extracted fields to job profile."""
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger('ats.field_mapper')

# Mapping rules: field label patterns -> profile field paths + confidence
MAPPING_RULES = [
    # Personal info
    {'patterns': [r'first\s*name', r'given\s*name'], 'profile_field': 'first_name', 'confidence': 0.99},
    {'patterns': [r'middle\s*name'], 'profile_field': 'middle_name', 'confidence': 0.99},
    {'patterns': [r'last\s*name', r'family\s*name', r'surname'], 'profile_field': 'last_name', 'confidence': 0.99},
    {'patterns': [r'full\s*name', r'your\s*name', r'candidate\s*name'], 'profile_field': 'first_name', 'confidence': 0.95, 'combine': ['first_name', 'last_name']},
    {'patterns': [r'preferred\s*name'], 'profile_field': 'preferred_name', 'confidence': 0.95},

    # Contact
    {'patterns': [r'e-?mail', r'email\s*address'], 'profile_field': 'email', 'confidence': 0.99},
    {'patterns': [r'phone', r'mobile', r'telephone', r'contact\s*number'], 'profile_field': 'phone', 'confidence': 0.98},
    {'patterns': [r'linkedin'], 'profile_field': 'linkedin_url', 'confidence': 0.95},
    {'patterns': [r'github'], 'profile_field': 'github_url', 'confidence': 0.95},
    {'patterns': [r'portfolio', r'website', r'personal\s*site'], 'profile_field': 'portfolio_url', 'confidence': 0.90},

    # Location
    {'patterns': [r'city'], 'profile_field': 'city', 'confidence': 0.95},
    {'patterns': [r'state', r'province', r'region'], 'profile_field': 'state', 'confidence': 0.90},
    {'patterns': [r'country'], 'profile_field': 'country', 'confidence': 0.95},
    {'patterns': [r'zip\s*code', r'postal\s*code'], 'profile_field': 'postal_code', 'confidence': 0.95},
    {'patterns': [r'street\s*address', r'address\s*line', r'address'], 'profile_field': 'address', 'confidence': 0.90},

    # Professional
    {'patterns': [r'current\s*title', r'job\s*title', r'position', r'role'], 'profile_field': 'current_title', 'confidence': 0.90},
    {'patterns': [r'current\s*company', r'employer', r'company\s*name'], 'profile_field': 'current_company', 'confidence': 0.90},
    {'patterns': [r'years?\s*of\s*experience', r'experience\s*years', r'total\s*experience'], 'profile_field': 'years_of_experience', 'confidence': 0.90},

    # Education
    {'patterns': [r'university', r'college', r'school'], 'profile_field': 'university', 'confidence': 0.95},
    {'patterns': [r'degree'], 'profile_field': 'degree', 'confidence': 0.90},
    {'patterns': [r'field\s*of\s*study', r'major'], 'profile_field': 'field_of_study', 'confidence': 0.90},
    {'patterns': [r'graduation\s*year', r'year\s*of\s*graduation'], 'profile_field': 'graduation_year', 'confidence': 0.90},
    {'patterns': [r'gpa', r'grade\s*point'], 'profile_field': 'gpa', 'confidence': 0.85},

    # Work authorization
    {'patterns': [r'authorized\s*to\s*work', r'legally\s*authorized', r'work\s*authorization'], 'profile_field': 'authorized_to_work', 'confidence': 0.95, 'type': 'boolean'},
    {'patterns': [r'require.*sponsor', r'sponsorship', r'visa\s*sponsor'], 'profile_field': 'requires_sponsorship', 'confidence': 0.95, 'type': 'boolean'},

    # Preferences
    {'patterns': [r'salary\s*expect', r'expected\s*salary', r'compensation', r'desired\s*salary'], 'profile_field': 'expected_salary', 'confidence': 0.80},
    {'patterns': [r'notice\s*period', r'available\s*from', r'start\s*date'], 'profile_field': 'notice_period', 'confidence': 0.80},
    {'patterns': [r'relocat'], 'profile_field': 'willing_to_relocate', 'confidence': 0.85, 'type': 'boolean'},
    {'patterns': [r'travel'], 'profile_field': 'willing_to_travel', 'confidence': 0.80, 'type': 'boolean'},

    # Common questions
    {'patterns': [r'how\s*did\s*you\s*hear', r'source', r'referral'], 'profile_field': 'common_answers.how_heard', 'confidence': 0.70},
    {'patterns': [r'cover\s*letter'], 'profile_field': 'common_answers.cover_letter', 'confidence': 0.70},
    {'patterns': [r'why.*company', r'why.*join', r'interest.*position'], 'profile_field': 'common_answers.why_company', 'confidence': 0.60},
    {'patterns': [r'additional\s*information', r'anything\s*else', r'comments'], 'profile_field': 'common_answers.additional', 'confidence': 0.50},
]


def _normalize_label(label: str) -> str:
    """Normalize a field label for matching."""
    return re.sub(r'[\s\-_]+', ' ', label.lower().strip().rstrip(':*'))


def _match_profile_value(profile: dict, field_path: str) -> str:
    """Get a value from the profile by dot-separated path."""
    parts = field_path.split('.')
    val = profile
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            return ''
    if val is None:
        return ''
    return str(val)


def _boolean_match(value: str, target: bool) -> str:
    """Match a form field value to a boolean profile value."""
    if target is None:
        return ''
    val_lower = value.lower().strip()
    if target:
        # Look for yes/true/authorized options
        if any(w in val_lower for w in ['yes', 'true', 'authorized', 'no', 'do not']):
            return 'Yes' if 'no' not in val_lower else 'No'
        return 'Yes'
    else:
        return 'No'


def map_fields(fields: List[Dict[str, Any]], profile: dict) -> List[Dict[str, Any]]:
    """Map extracted fields to profile values with confidence scores.

    For each field, tries deterministic rules first, then returns lower confidence
    for fields that need AI mapping or user input.
    """
    mapped = []

    for field in fields:
        label = _normalize_label(field.get('field_label', ''))
        field_type = field.get('field_type', 'text')
        options = field.get('options', [])

        # Skip non-input fields
        if field_type in ('file',):
            field['status'] = 'pending'
            mapped.append(field)
            continue

        best_match = None
        best_confidence = 0.0

        for rule in MAPPING_RULES:
            for pattern in rule['patterns']:
                if re.search(pattern, label):
                    confidence = rule['confidence']
                    if confidence > best_confidence:
                        best_match = rule
                        best_confidence = confidence
                    break

        if best_match:
            profile_field = best_match['profile_field']
            raw_value = _match_profile_value(profile, profile_field)

            # Handle boolean fields
            if best_match.get('type') == 'boolean' and raw_value:
                raw_value = 'Yes' if raw_value in ('true', 'True', '1', True) else 'No'

            # Handle combined fields (e.g., full name)
            if best_match.get('combine'):
                parts = [_match_profile_value(profile, p) for p in best_match['combine']]
                raw_value = ' '.join(p for p in parts if p)

            field['profile_field'] = profile_field
            field['mapped_value'] = raw_value
            field['confidence'] = best_confidence
            field['mapping_reasoning'] = f'Matched pattern "{best_match["patterns"][0]}" in label "{field.get("field_label", "")}"'

            # Determine status based on confidence and field type
            if not raw_value:
                field['status'] = 'pending'
                field['requires_review'] = True
                field['confidence'] = 0.0
            elif best_confidence >= 0.90:
                field['status'] = 'mapped'
                field['requires_review'] = False
            elif best_confidence >= 0.70:
                field['status'] = 'mapped'
                field['requires_review'] = True
            else:
                field['status'] = 'mapped'
                field['requires_review'] = True

            # Handle select fields: check if mapped value is in options
            if field_type == 'select' and options and raw_value:
                option_values = [o.get('value', '') for o in options]
                option_labels = [o.get('label', '').lower() for o in options]
                if raw_value.lower() in option_values or raw_value.lower() in option_labels:
                    # Find exact option value
                    for o in options:
                        if raw_value.lower() == o.get('label', '').lower() or raw_value.lower() == o.get('value', '').lower():
                            field['mapped_value'] = o.get('value', raw_value)
                            break
                else:
                    # Value not in options, needs review
                    field['requires_review'] = True

        else:
            # No deterministic mapping found
            field['status'] = 'pending'
            field['requires_review'] = True
            field['confidence'] = 0.0
            field['mapping_reasoning'] = 'No pattern match found - requires AI mapping or user input'

        mapped.append(field)

    return mapped
