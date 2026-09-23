"""AI-powered field mapping for job application autofill."""
import logging
import json
from typing import List, Dict, Any, Optional

logger = logging.getLogger('ai_field_mapper')


class AIFieldMapper:
    """Uses LLM to map extracted form fields to profile data.

    Handles ambiguous questions, cover letter prompts, and complex
    multi-select fields that deterministic rules can't handle.
    """

    def __init__(self, api_key: Optional[str] = None, provider: str = 'gemini'):
        self.api_key = api_key
        self.provider = provider

    async def map_fields(
        self,
        fields: List[Dict[str, Any]],
        profile: Dict[str, Any],
        job_info: Dict[str, Any] = None,
        resume_text: str = '',
    ) -> List[Dict[str, Any]]:
        """Use AI to map fields that need intelligent handling."""
        unmapped = [f for f in fields if f.get('confidence', 1.0) < 0.7 and not f.get('user_value')]
        if not unmapped:
            return fields

        if not self.api_key:
            logger.warning('No API key for AI field mapping, skipping')
            return fields

        prompt = self._build_mapping_prompt(fields, profile, job_info, resume_text)
        try:
            response = await self._call_llm(prompt)
            return self._apply_ai_mapping(fields, response)
        except Exception as e:
            logger.error('AI field mapping failed: %s', e)
            return fields

    def _build_mapping_prompt(
        self,
        fields: List[Dict[str, Any]],
        profile: Dict[str, Any],
        job_info: Dict[str, Any] = None,
        resume_text: str = '',
    ) -> str:
        profile_summary = {
            'full_name': profile.get('full_name'),
            'email': profile.get('email'),
            'phone': profile.get('phone'),
            'location': profile.get('location'),
            'city': profile.get('city'),
            'state': profile.get('state'),
            'linkedin': profile.get('linkedin'),
            'github': profile.get('github'),
            'portfolio': profile.get('portfolio'),
            'years_experience': profile.get('years_experience'),
            'current_company': profile.get('current_company'),
            'current_title': profile.get('current_title'),
            'desired_salary': profile.get('desired_salary'),
            'desired_salary_min': profile.get('desired_salary_min'),
            'desired_salary_max': profile.get('desired_salary_max'),
            'work_authorization': profile.get('work_authorization'),
            'requires_sponsorship': profile.get('requires_sponsorship'),
            'gender': profile.get('gender'),
            'ethnicity': profile.get('ethnicity'),
            'veteran_status': profile.get('veteran_status'),
            'disability_status': profile.get('disability_status'),
            'pronouns': profile.get('pronouns'),
            'cover_letter_template': profile.get('cover_letter_template'),
            'custom_answers': profile.get('custom_answers', {}),
        }

        field_descriptions = []
        for f in fields:
            if f.get('confidence', 1.0) >= 0.9:
                continue
            field_descriptions.append({
                'label': f.get('field_label'),
                'type': f.get('field_type'),
                'options': f.get('options'),
                'required': f.get('required'),
                'section': f.get('section'),
                'placeholder': f.get('placeholder'),
                'current_mapping': f.get('profile_field'),
                'current_confidence': f.get('confidence'),
            })

        prompt = f"""You are a job application assistant. Map form fields to profile values.

Profile:
{json.dumps(profile_summary, indent=2, default=str)}

Job Info:
{json.dumps(job_info or {}, indent=2, default=str)}

Resume excerpt (first 2000 chars):
{resume_text[:2000]}

Form fields that need intelligent mapping:
{json.dumps(field_descriptions, indent=2, default=str)}

For each field, provide:
- field_label: the field label (copy exactly)
- mapped_value: the value to fill
- profile_field: which profile field this maps to (or "custom")
- confidence: 0.0-1.0
- reasoning: why this value

Return JSON array. For fields you can't map, set confidence=0.1 and mapped_value=''.
For cover letter / open-ended questions, generate a concise professional response.
For salary fields, use the profile's salary range or a reasonable estimate.
For yes/no questions (sponsorship, work auth), use the profile values.
For unknown fields, leave mapped_value empty with low confidence."""

        return prompt

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        if self.provider == 'gemini':
            return await self._call_gemini(prompt)
        elif self.provider == 'openai':
            return await self._call_openai(prompt)
        raise ValueError(f'Unknown provider: {self.provider}')

    async def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        import aiohttp
        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}'
        payload = {
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': 0.3, 'maxOutputTokens': 4096},
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f'Gemini API error {resp.status}: {text[:200]}')
                data = await resp.json()
                text = data['candidates'][0]['content']['parts'][0]['text']
                text = text.strip().strip('`')
                if text.startswith('json'):
                    text = text[4:]
                return json.loads(text)

    async def _call_openai(self, prompt: str) -> Dict[str, Any]:
        import aiohttp
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}
        payload = {
            'model': 'gpt-4o-mini',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.3,
            'max_tokens': 4096,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f'OpenAI API error {resp.status}: {text[:200]}')
                data = await resp.json()
                text = data['choices'][0]['message']['content']
                text = text.strip().strip('`')
                if text.startswith('json'):
                    text = text[4:]
                return json.loads(text)

    def _apply_ai_mapping(
        self,
        fields: List[Dict[str, Any]],
        ai_response: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        if not isinstance(ai_response, list):
            return fields

        ai_map = {item.get('field_label'): item for item in ai_response if item.get('field_label')}

        for field in fields:
            label = field.get('field_label')
            if label in ai_map:
                ai_data = ai_map[label]
                if ai_data.get('confidence', 0) > field.get('confidence', 0):
                    field['mapped_value'] = ai_data.get('mapped_value', '')
                    field['profile_field'] = ai_data.get('profile_field', 'custom')
                    field['confidence'] = ai_data.get('confidence', 0)
                    field['mapping_reasoning'] = ai_data.get('reasoning', '')
                    if ai_data.get('confidence', 0) >= 0.7:
                        field['status'] = 'auto_filled'
                    else:
                        field['status'] = 'needs_review'
                        field['requires_review'] = True

        return fields


def create_ai_mapper(api_key: Optional[str] = None, provider: str = 'gemini') -> AIFieldMapper:
    return AIFieldMapper(api_key=api_key, provider=provider)
