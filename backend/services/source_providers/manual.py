import re
import httpx
from typing import Optional
from urllib.parse import urlparse

from .base import JobSourceProvider, JobListing, JobSearchParams, JobSourceCapabilities


class ManualProvider(JobSourceProvider):
    """Provider for manual job URL import - fetches and extracts job data from any URL."""
    
    name = 'manual'
    capabilities = JobSourceCapabilities(
        search=False,
        job_details=True,
        application_api=False,
        candidate_apply_api=False
    )
    
    # Common job board patterns for better extraction
    JOB_BOARD_SELECTORS = {
        'greenhouse.io': {
            'title': 'h1.app-title, h1[data-qa="job-title"]',
            'company': '.company-name, [data-qa="company-name"]',
            'location': '.location, [data-qa="job-location"]',
            'description': '#content, .job-description, [data-qa="job-description"]',
        },
        'lever.co': {
            'title': 'h1.posting-headline, h2.posting-title',
            'company': '.posting-company, .company-name',
            'location': '.posting-categories .location, .location',
            'description': '.section.description, .content',
        },
        'ashbyhq.com': {
            'title': 'h1[data-testid="job-title"]',
            'company': '[data-testid="company-name"]',
            'location': '[data-testid="job-location"]',
            'description': '[data-testid="job-description"]',
        },
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; ColdBeggingBot/1.0)'}
        )
    
    async def search_jobs(self, params: JobSearchParams) -> list:
        """Manual provider doesn't support search."""
        return []
    
    async def get_job(self, job_url: str) -> Optional[JobListing]:
        """Fetch and extract job data from a URL."""
        try:
            response = await self.client.get(job_url)
            response.raise_for_status()
            html = response.text
            
            # Try board-specific extraction first
            domain = urlparse(job_url).netloc.lower()
            for board_domain, selectors in self.JOB_BOARD_SELECTORS.items():
                if board_domain in domain:
                    return self._extract_with_selectors(html, job_url, selectors)
            
            # Fallback to generic extraction
            return self._extract_generic(html, job_url)
            
        except Exception as e:
            # Return minimal listing with just the URL
            return JobListing(
                external_id=job_url,
                title='Unknown Position',
                company_name='Unknown Company',
                application_url=job_url,
                source_data={'error': str(e), 'url': job_url}
            )
    
    def _extract_with_selectors(self, html: str, url: str, selectors: dict) -> JobListing:
        """Extract using board-specific CSS selectors."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        def get_text(selector: str) -> str:
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else ''
        
        title = get_text(selectors.get('title', ''))
        company = get_text(selectors.get('company', ''))
        location = get_text(selectors.get('location', ''))
        description = get_text(selectors.get('description', ''))
        
        # Try to find application URL
        apply_url = url
        apply_link = soup.select_one('a[href*="apply"], a[href*="application"], button[data-apply]')
        if apply_link and apply_link.get('href'):
            apply_url = apply_link['href']
        
        # Extract skills from description
        skills = self._extract_skills(description)
        
        return JobListing(
            external_id=url,
            title=title or 'Unknown Position',
            company_name=company or 'Unknown Company',
            location=location,
            description=description,
            skills=skills,
            application_url=apply_url,
            source_data={'url': url, 'extracted': True}
        )
    
    def _extract_generic(self, html: str, url: str) -> JobListing:
        """Generic extraction using common patterns."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try to find title
        title = ''
        for selector in ['h1', 'h2.job-title', '[class*="job-title"]', '[class*="position-title"]']:
            el = soup.select_one(selector)
            if el:
                title = el.get_text(strip=True)
                break
        
        # Try to find company
        company = ''
        for selector in ['[class*="company"]', '[class*="employer"]', 'meta[property="og:site_name"]']:
            el = soup.select_one(selector)
            if el:
                company = el.get('content') or el.get_text(strip=True)
                break
        
        # Get all text for description
        description = soup.get_text(separator=' ', strip=True)[:10000]
        
        # Extract location
        location = ''
        location_patterns = [
            r'(?:location|based in|office in)\s*:?\s*([^,\n]+)',
            r'\b(?:remote|hybrid|onsite)\b',
        ]
        for pattern in location_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                location = match.group(1).strip() if match.groups() else match.group(0)
                break
        
        # Extract salary
        salary_min, salary_max = self._extract_salary(description)
        
        # Extract skills
        skills = self._extract_skills(description)
        
        # Detect remote type
        remote_type = 'remote' if re.search(r'\bremote\b', description, re.IGNORECASE) else None
        if not remote_type and re.search(r'\bhybrid\b', description, re.IGNORECASE):
            remote_type = 'hybrid'
        if not remote_type and re.search(r'\bonsite\b|\bin.office\b', description, re.IGNORECASE):
            remote_type = 'onsite'
        
        return JobListing(
            external_id=url,
            title=title or 'Unknown Position',
            company_name=company or 'Unknown Company',
            location=location,
            remote_type=remote_type,
            description=description,
            skills=skills,
            salary_min=salary_min,
            salary_max=salary_max,
            application_url=url,
            source_data={'url': url, 'extracted': True, 'method': 'generic'}
        )
    
    def _extract_skills(self, text: str) -> list:
        """Extract common tech skills from text."""
        common_skills = [
            'Python', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'Java', 'C++', 'C#',
            'React', 'Vue', 'Angular', 'Next.js', 'Node.js', 'Django', 'Flask', 'FastAPI',
            'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch', 'DynamoDB',
            'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes', 'Terraform', 'Ansible',
            'Git', 'CI/CD', 'Jenkins', 'GitHub Actions', 'GitLab CI',
            'GraphQL', 'REST', 'gRPC', 'Kafka', 'RabbitMQ', 'Redis',
            'Machine Learning', 'AI', 'LLM', 'NLP', 'Computer Vision',
            'System Design', 'Microservices', 'Distributed Systems',
        ]
        
        found = []
        text_lower = text.lower()
        for skill in common_skills:
            if skill.lower() in text_lower:
                found.append(skill)
        return found
    
    def _extract_salary(self, text: str) -> tuple:
        """Extract salary range from text."""
        import re
        # Patterns like $100k-$200k, $100,000 - $200,000, etc.
        patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*[kK]?\s*[-–]\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*[kK]?',
            r'(\d{1,3}(?:,\d{3})*)\s*[-–]\s*(\d{1,3}(?:,\d{3})*)\s*(?:USD|per year|annually)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    min_val = int(match.group(1).replace(',', '').replace('k', '000').replace('K', '000'))
                    max_val = int(match.group(2).replace(',', '').replace('k', '000').replace('K', '000'))
                    if 'k' in match.group(1).lower() or 'k' in match.group(2).lower():
                        min_val *= 1000
                        max_val *= 1000
                    return min_val, max_val
                except ValueError:
                    pass
        return None, None
    
    async def close(self):
        await self.client.aclose()


# Singleton instance
manual_provider = ManualProvider()