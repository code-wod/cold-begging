import httpx
from typing import List, Optional
import re

from .base import JobSourceProvider, JobListing, JobSearchParams, JobSourceCapabilities


class AshbyProvider(JobSourceProvider):
    """Ashby job board provider - uses public GraphQL API."""
    
    name = 'ashby'
    capabilities = JobSourceCapabilities(
        search=True,
        job_details=True,
        application_api=True,  # Ashby has application API
        candidate_apply_api=False
    )
    
    GRAPHQL_URL = 'https://jobs.ashbyhq.com/api/non-user-graphql'
    
    # GraphQL query for job details
    JOB_QUERY = """
    query Job($id: ID!) {
        job(id: $id) {
            id
            title
            teamName
            locationName
            isRemote
            employmentType
            description
            descriptionHtml
            applyUrl
            publishedAt
            updatedAt
        }
    }
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_jobs(self, params: JobSearchParams) -> List[JobListing]:
        """Search jobs on Ashby. Requires organization name."""
        return []
    
    async def get_job(self, job_url: str) -> Optional[JobListing]:
        """Fetch job from Ashby GraphQL API."""
        try:
            # Parse organization and job ID from URL
            # Typical: https://jobs.ashbyhq.com/{org}/{job_id}
            match = re.search(r'jobs\.ashbyhq\.com/([^/]+)/([^/?#]+)', job_url)
            if not match:
                # Try: https://{org}.ashbyhq.com/{job_id}
                match = re.search(r'([^.]+)\.ashbyhq\.com/([^/?#]+)', job_url)
            
            if not match:
                return None
            
            org, job_id = match.groups()
            
            # Ashby uses organization-specific GraphQL endpoints
            graphql_url = f'https://jobs.ashbyhq.com/api/non-user-graphql?org={org}'
            
            response = await self.client.post(
                graphql_url,
                json={'query': self.JOB_QUERY, 'variables': {'id': job_id}}
            )
            response.raise_for_status()
            data = response.json()
            
            job_data = data.get('data', {}).get('job')
            if not job_data:
                return None
            
            return self._parse_job(job_data, org, job_url)
            
        except Exception:
            return None
    
    def _parse_job(self, data: dict, org: str, source_url: str) -> JobListing:
        """Parse Ashby job data."""
        # Location
        location = data.get('locationName', '')
        
        # Remote type
        remote_type = 'remote' if data.get('isRemote') else 'onsite'
        
        # Employment type
        employment_type = 'full_time'
        emp_type = data.get('employmentType', '').lower()
        if 'part' in emp_type:
            employment_type = 'part_time'
        elif 'contract' in emp_type:
            employment_type = 'contract'
        elif 'intern' in emp_type:
            employment_type = 'internship'
        
        # Description
        description = data.get('description', '') or data.get('descriptionHtml', '')
        
        # Skills
        skills = self._extract_skills(description)
        
        return JobListing(
            external_id=data.get('id', ''),
            title=data.get('title', ''),
            company_name=data.get('teamName', org),
            company_url=f'https://jobs.ashbyhq.com/{org}',
            location=location,
            remote_type=remote_type,
            employment_type=employment_type,
            description=description,
            skills=skills,
            application_url=data.get('applyUrl', source_url),
            posted_at=self._parse_date(data.get('publishedAt')),
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


ashby_provider = AshbyProvider()