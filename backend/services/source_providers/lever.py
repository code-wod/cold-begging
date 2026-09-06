import httpx
from typing import List, Optional
import re

from .base import JobSourceProvider, JobListing, JobSearchParams, JobSourceCapabilities


class LeverProvider(JobSourceProvider):
    """Lever job board provider - uses public job board API."""
    
    name = 'lever'
    capabilities = JobSourceCapabilities(
        search=True,
        job_details=True,
        application_api=True,  # Lever has partner API
        candidate_apply_api=False
    )
    
    BASE_URL = 'https://api.lever.co/v0/postings'
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_jobs(self, params: JobSearchParams) -> List[JobListing]:
        """Search jobs on Lever. Requires company subdomain."""
        return []
    
    async def get_job(self, job_url: str) -> Optional[JobListing]:
        """Fetch job from Lever API."""
        try:
            # Parse company and job ID from URL
            # Typical: https://jobs.lever.co/{company}/{job_id}
            # Or: https://{company}.lever.co/{job_id}
            match = re.search(r'jobs\.lever\.co/([^/]+)/([^/?#]+)', job_url)
            if not match:
                match = re.search(r'([^.]+)\.lever\.co/([^/?#]+)', job_url)
            
            if not match:
                return None
            
            company, job_id = match.groups()
            
            url = f'{self.BASE_URL}/{company}/{job_id}'
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_job(data, company, job_url)
            
        except Exception:
            return None
    
    def _parse_job(self, data: dict, company: str, source_url: str) -> JobListing:
        """Parse Lever job data."""
        # Location
        location = ''
        if data.get('categories', {}).get('location'):
            location = data['categories']['location']
        
        # Remote type
        remote_type = None
        if data.get('categories', {}).get('remote'):
            remote_val = data['categories']['remote'].lower()
            if 'remote' in remote_val:
                remote_type = 'remote'
            elif 'hybrid' in remote_val:
                remote_type = 'hybrid'
            else:
                remote_type = 'onsite'
        
        # Employment type
        employment_type = 'full_time'
        if data.get('categories', {}).get('commitment'):
            commitment = data['categories']['commitment'].lower()
            if 'full' in commitment:
                employment_type = 'full_time'
            elif 'part' in commitment:
                employment_type = 'part_time'
            elif 'contract' in commitment:
                employment_type = 'contract'
            elif 'intern' in commitment:
                employment_type = 'internship'
        
        # Description
        description = data.get('description', '') or data.get('descriptionPlain', '')
        
        # Skills
        skills = self._extract_skills(description)
        
        return JobListing(
            external_id=data.get('id', ''),
            title=data.get('text', ''),
            company_name=data.get('company', company),
            company_url=f'https://jobs.lever.co/{company}',
            location=location,
            remote_type=remote_type,
            employment_type=employment_type,
            description=description,
            skills=skills,
            application_url=data.get('hostedUrl', source_url),
            posted_at=self._parse_date(data.get('createdAt')),
            source_data=data
        )
    
    def _extract_skills(self, text: str) -> list:
        common_skills = [
            'Python', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'Java', 'C++', 'C#',
            'React', 'Vue', 'Angular', 'Next.js', 'Node.js', 'Django', 'Flask', 'FastAPI',
            'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch', 'DynamoDB',
            'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes', 'Terraform', 'Ansible',
            'Git', 'CI/CD', 'Jenkins', 'GitHub Actions', 'GitLab CI',
            'GraphQL', 'REST', 'gRPC', 'Kafka', 'RabbitMQ',
        ]
        found = []
        text_lower = text.lower()
        for skill in common_skills:
            if skill.lower() in text_lower:
                found.append(skill)
        return found
    
    def _parse_date(self, timestamp: Optional[int]) -> Optional[object]:
        if not timestamp:
            return None
        try:
            from datetime import datetime, timezone
            return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        except Exception:
            return None
    
    async def close(self):
        await self.client.aclose()


lever_provider = LeverProvider()