from typing import List, Optional
from playwright.async_api import Page

from .base import (
    JobPortalProvider,
    PortalCapabilities,
    SearchConfig,
    JobCard,
    JobDetail,
    ApplicationResult,
    CandidateProfile,
    provider_registry,
)


class NaukriProvider(JobPortalProvider):
    """Naukri.com One Click Apply provider."""
    
    name = 'naukri'
    platform_name = 'naukri'
    
    BASE_URL = 'https://www.naukri.com'
    LOGIN_URL = 'https://www.naukri.com/nlogin/login'
    HOME_URL = 'https://www.naukri.com/mnjuser/homepage'
    SEARCH_URL = 'https://www.naukri.com/jobs'
    
    capabilities = PortalCapabilities(
        job_search=True,
        one_click_apply=True,
        resume_upload=True,
    )
    
    SELECTORS = {
        'logged_in_indicators': [
            '.mnj-header',
            '.user-name',
            '#usernameField[disabled]',
        ],
        'search_keywords': 'input[placeholder*="Skills"], input[name="qp"]',
        'search_location': 'input[placeholder*="Location"], input[name="ql"]',
        'search_button': 'button[type="submit"]',
        'job_cards': '.jobTuple, .srp-jobtuple-wrapper',
        'job_title': '.title a, .jobTupleHeader a',
        'job_company': '.subTitle, .companyInfo a',
        'job_location': '.location, .locWdth',
        'job_link': '.title a, .jobTupleHeader a',
        'job_detail_apply': 'button:has-text("Apply"), .apply-button',
        'one_click_apply': 'button:has-text("One Click Apply")',
        'resume_selector': '.resumeSelector, [name="resume"]',
        'apply_confirm': '.applyConfirmation, .successMessage',
    }
    
    async def search_jobs(self, page: Page, config: SearchConfig) -> List[JobCard]:
        """Search for jobs on Naukri."""
        try:
            from urllib.parse import urlencode
            
            params = {
                'qp': ' '.join(config.keywords[:3]) if config.keywords else '',
                'ql': config.locations[0] if config.locations else '',
            }
            params = {k: v for k, v in params.items() if v}
            
            search_url = f'{self.SEARCH_URL}?{urlencode(params)}'
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            
            cards = await page.query_selector_all(self.SELECTORS['job_cards'])
            jobs = []
            
            for card in cards[:config.max_results]:
                try:
                    job = await self.extract_job_card(page, card)
                    if job:
                        jobs.append(job)
                except Exception:
                    continue
            
            return jobs
        except Exception:
            return []
    
    async def extract_job_card(self, page: Page, card_element) -> Optional[JobCard]:
        try:
            title_elem = await card_element.query_selector(self.SELECTORS['job_title'])
            if not title_elem:
                return None
            
            title = await title_elem.inner_text()
            link = await title_elem.get_attribute('href')
            
            company_elem = await card_element.query_selector(self.SELECTORS['job_company'])
            company = await company_elem.inner_text() if company_elem else ''
            
            location_elem = await card_element.query_selector(self.SELECTORS['job_location'])
            location = await location_elem.inner_text() if location_elem else ''
            
            external_id = ''
            if link:
                import re
                match = re.search(r'/job/(\d+)', link)
                if match:
                    external_id = match.group(1)
            
            return JobCard(
                external_id=external_id or link or '',
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                url=link,
            )
        except Exception:
            return None
    
    async def extract_job_detail(self, page: Page, job_url: str) -> JobDetail:
        await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)
        
        return JobDetail(
            external_id=job_url,
            title='',
            company='',
            location='',
            application_url=job_url,
        )
    
    async def can_apply(self, page: Page, job: JobDetail) -> bool:
        apply_btn = await page.query_selector(self.SELECTORS['job_detail_apply'])
        return apply_btn is not None
    
    async def prepare_application(
        self,
        page: Page,
        job: JobDetail,
        candidate: CandidateProfile
    ) -> bool:
        # Naukri typically uses One Click Apply with resume selection
        return True
    
    async def submit_application(self, page: Page) -> ApplicationResult:
        from backend.config import DRY_RUN
        
        if DRY_RUN:
            return ApplicationResult(
                success=True,
                status='dry_run',
                message='DRY_RUN mode - application not submitted',
            )
        
        return ApplicationResult(
            success=False,
            status='not_implemented',
            message='Naukri apply not yet implemented',
        )
    
    async def detect_application_result(self, page: Page) -> ApplicationResult:
        return ApplicationResult(
            success=False,
            status='not_implemented',
            message='Naukri result detection not yet implemented',
        )


naukri_provider = NaukriProvider()
provider_registry.register(naukri_provider)