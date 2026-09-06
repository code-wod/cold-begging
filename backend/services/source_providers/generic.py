import httpx
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from .base import JobSourceProvider, JobListing, JobSearchParams, JobSourceCapabilities
from .manual import ManualProvider


class GenericCompanyProvider(JobSourceProvider):
    """Generic company career page provider - uses HTML scraping and common patterns."""
    
    name = 'company'
    capabilities = JobSourceCapabilities(
        search=False,
        job_details=True,
        application_api=False,
        candidate_apply_api=False
    )
    
    # Common career page paths
    CAREER_PATHS = [
        '/careers', '/jobs', '/join-us', '/work-with-us', '/positions',
        '/openings', '/opportunities', '/team', '/hiring'
    ]
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; ColdBeggingBot/1.0)'}
        )
        self.manual_provider = ManualProvider()
    
    async def search_jobs(self, params: JobSearchParams) -> List[JobListing]:
        """Generic provider doesn't support search across companies."""
        return []
    
    async def get_job(self, job_url: str) -> Optional[JobListing]:
        """Fetch job from a company career page."""
        # First try manual extraction (handles known boards)
        result = await self.manual_provider.get_job(job_url)
        if result and result.title != 'Unknown Position':
            result.source = self.name
            return result
        
        # Try to discover if it's a known ATS
        parsed = urlparse(job_url)
        domain = parsed.netloc.lower()
        
        # Check for common ATS subdomains
        ats_patterns = {
            'workday': ['workday', 'myworkdayjobs'],
            'bamboohr': ['bamboohr'],
            'icims': ['icims'],
            'jobvite': ['jobvite'],
            'smartrecruiters': ['smartrecruiters'],
            'recruitee': ['recruitee'],
            'personio': ['personio'],
            'teamtailor': ['teamtailor'],
        }
        
        for ats, patterns in ats_patterns.items():
            if any(p in domain for p in patterns):
                return await self._extract_ats_job(job_url, ats)
        
        # Fallback to manual provider result
        return result
    
    async def _extract_ats_job(self, url: str, ats: str) -> Optional[JobListing]:
        """Extract job from known ATS platforms."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            html = response.text
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # ATS-specific selectors
            selectors = {
                'workday': {
                    'title': '[data-automation-id="jobTitle"], h1[data-automation-id]',
                    'company': '[data-automation-id="companyName"]',
                    'location': '[data-automation-id="location"], [data-automation-id="locations"]',
                    'description': '[data-automation-id="jobDescription"]',
                },
                'bamboohr': {
                    'title': 'h1.job-title, .job-title',
                    'company': '.company-name',
                    'location': '.location, .job-location',
                    'description': '.job-description, .description',
                },
                'icims': {
                    'title': '.iCIMS_JobHeader h1, .job-title',
                    'company': '.company-name',
                    'location': '.location, .job-location',
                    'description': '.job-description, .iCIMS_Description',
                },
            }
            
            ats_selectors = selectors.get(ats, {})
            if ats_selectors:
                return self._extract_with_selectors(soup, url, ats_selectors, ats)
            
            return self._extract_generic(soup, url, ats)
            
        except Exception:
            return None
    
    def _extract_with_selectors(self, soup, url: str, selectors: dict, ats: str) -> JobListing:
        def get_text(selector: str) -> str:
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else ''
        
        title = get_text(selectors.get('title', ''))
        company = get_text(selectors.get('company', ''))
        location = get_text(selectors.get('location', ''))
        description = get_text(selectors.get('description', ''))
        
        # Try to get apply URL
        apply_url = url
        apply_link = soup.select_one('a[href*="apply"], button[data-apply], [data-automation-id="applyButton"]')
        if apply_link and apply_link.get('href'):
            apply_url = urljoin(url, apply_link['href'])
        
        skills = self._extract_skills(description)
        
        return JobListing(
            external_id=url,
            title=title or 'Unknown Position',
            company_name=company or 'Unknown Company',
            location=location,
            description=description,
            skills=skills,
            application_url=apply_url,
            source_data={'url': url, 'ats': ats, 'extracted': True}
        )
    
    def _extract_generic(self, soup, url: str, ats: str) -> JobListing:
        """Generic extraction for unknown ATS."""
        title = ''
        for selector in ['h1', 'h2', '[class*="title"]', '[class*="position"]']:
            el = soup.select_one(selector)
            if el and len(el.get_text(strip=True)) > 5:
                title = el.get_text(strip=True)
                break
        
        description = soup.get_text(separator=' ', strip=True)[:10000]
        skills = self._extract_skills(description)
        
        return JobListing(
            external_id=url,
            title=title or 'Unknown Position',
            company_name='Unknown Company',
            description=description,
            skills=skills,
            application_url=url,
            source_data={'url': url, 'ats': ats, 'extracted': True, 'method': 'generic'}
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
    
    async def close(self):
        await self.client.aclose()
        await self.manual_provider.close()


generic_provider = GenericCompanyProvider()