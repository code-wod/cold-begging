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


class InstahyreProvider(JobPortalProvider):
    """Instahyre provider."""
    
    name = 'instahyre'
    platform_name = 'instahyre'
    
    BASE_URL = 'https://instahyre.com'
    LOGIN_URL = 'https://instahyre.com/login'
    HOME_URL = 'https://instahyre.com/candidate/dashboard'
    SEARCH_URL = 'https://instahyre.com/jobs'
    
    capabilities = PortalCapabilities(
        job_search=True,
        easy_apply=True,
    )
    
    SELECTORS = {
        'logged_in_indicators': [
            '.user-menu',
            '.candidate-dashboard',
        ],
    }
    
    async def search_jobs(self, page: Page, config: SearchConfig) -> List[JobCard]:
        return []
    
    async def extract_job_card(self, page: Page, card_element) -> Optional[JobCard]:
        return None
    
    async def extract_job_detail(self, page: Page, job_url: str) -> JobDetail:
        return JobDetail(external_id=job_url, application_url=job_url)
    
    async def can_apply(self, page: Page, job: JobDetail) -> bool:
        return False
    
    async def prepare_application(self, page: Page, job: JobDetail, candidate: CandidateProfile) -> bool:
        return False
    
    async def submit_application(self, page: Page) -> ApplicationResult:
        return ApplicationResult(
            success=False,
            status='not_implemented',
            message='Instahyre provider not yet implemented',
        )
    
    async def detect_application_result(self, page: Page) -> ApplicationResult:
        return ApplicationResult(
            success=False,
            status='not_implemented',
            message='Instahyre provider not yet implemented',
        )


instahyre_provider = InstahyreProvider()
provider_registry.register(instahyre_provider)