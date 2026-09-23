import httpx
from typing import List, Optional
from urllib.parse import urljoin

from .base import JobSourceProvider, JobListing, JobSearchParams, JobSourceCapabilities


class GreenhouseProvider(JobSourceProvider):
    """Greenhouse job board provider - uses public job board API."""
    
    name = 'greenhouse'
    capabilities = JobSourceCapabilities(
        search=True,
        job_details=True,
        application_api=True,  # Greenhouse has partner API for applications
        candidate_apply_api=False  # No public candidate API
    )
    
    BASE_URL = 'https://boards-api.greenhouse.io/v1/boards'
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_jobs(self, params: JobSearchParams) -> List[JobListing]:
        """Search jobs on Greenhouse. Requires board token."""
        # This would require a specific board token
        # For now, return empty - would be configured per company
        return []
    
    async def get_job(self, job_url: str) -> Optional[JobListing]:
        """Fetch job from Greenhouse board API."""
        try:
            # Parse board and job ID from URL
            # Typical URL: https://boards.greenhouse.io/{board}/jobs/{job_id}
            import re
            match = re.search(r'boards\.greenhouse\.io/([^/]+)/jobs/(\d+)', job_url)
            if not match:
                # Try alternate format: https://{company}.greenhouse.io/jobs/{job_id}
                match = re.search(r'([^.]+)\.greenhouse\.io/jobs/(\d+)', job_url)
            
            if not match:
                return None
            
            board_token, job_id = match.groups()
            
            # Fetch from API
            url = f'{self.BASE_URL}/{board_token}/jobs/{job_id}'
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_job(data, job_url)
            
        except Exception:
            return None
    
    def _parse_job(self, data: dict, source_url: str) -> JobListing:
        """Parse Greenhouse job data."""
        # Extract location
        location = ''
        if data.get('location'):
            location = data['location'].get('name', '')
        
        # Extract salary
        salary_min = salary_max = None
        if data.get('metadata') and isinstance(data['metadata'], list):
            for item in data['metadata']:
                if item.get('name') == 'Salary Range':
                    value = item.get('value', '')
                    # Parse salary range
                    import re
                    m = re.search(r'\$?(\d[\d,]*)\s*[-–]\s*\$?(\d[\d,]*)', value)
                    if m:
                        salary_min = int(m.group(1).replace(',', ''))
                        salary_max = int(m.group(2).replace(',', ''))
        
        # Determine remote type
        remote_type = None
        if data.get('metadata'):
            for item in data['metadata']:
                if item.get('name', '').lower() == 'remote':
                    remote_type = 'remote' if item.get('value') == 'yes' else 'onsite'
        
        # Skills from content
        content = data.get('content', '') or ''
        skills = self._extract_skills(content)
        
        return JobListing(
            external_id=str(data.get('id', '')),
            title=data.get('title', ''),
            company_name=data.get('company_name', '') or self._extract_company_from_url(source_url),
            company_url=f'https://boards.greenhouse.io/{self._extract_company_from_url(source_url)}',
            location=location,
            remote_type=remote_type,
            employment_type=self._parse_employment_type(data),
            description=content,
            skills=skills,
            salary_min=salary_min,
            salary_max=salary_max,
            application_url=data.get('absolute_url', source_url),
            posted_at=self._parse_date(data.get('updated_at')),
            source_data=data
        )
    
    def _extract_company_from_url(self, url: str) -> str:
        import re
        match = re.search(r'([^.]+)\.greenhouse\.io|boards\.greenhouse\.io/([^/]+)', url)
        if match:
            return match.group(1) or match.group(2)
        return ''
    
    def _parse_employment_type(self, data: dict) -> Optional[str]:
        if data.get('metadata'):
            for item in data['metadata']:
                if item.get('name', '').lower() in ('employment type', 'type'):
                    val = item.get('value', '').lower()
                    if 'full' in val:
                        return 'full_time'
                    if 'part' in val:
                        return 'part_time'
                    if 'contract' in val:
                        return 'contract'
                    if 'intern' in val:
                        return 'internship'
        return 'full_time'
    
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
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[object]:
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            return None
    
    async def close(self):
        await self.client.aclose()


greenhouse_provider = GreenhouseProvider()