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


class WellfoundProvider(JobPortalProvider):
    """Wellfound (AngelList) provider."""
    
    name = 'wellfound'
    platform_name = 'wellfound'
    
    BASE_URL = 'https://wellfound.com'
    LOGIN_URL = 'https://wellfound.com/login'
    HOME_URL = 'https://wellfound.com/jobs'
    SEARCH_URL = 'https://wellfound.com/jobs'
    
    capabilities = PortalCapabilities(
        job_search=True,
        easy_apply=True,
        resume_upload=True,
    )
    
    SELECTORS = {
        'logged_in_indicators': [
            '[data-test="user-menu"]',
            '.user-avatar',
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
            message='Wellfound provider not yet implemented',
        )
    
    async def detect_application_result(self, page: Page) -> ApplicationResult:
        return ApplicationResult(
            success=False,
            status='not_implemented',
            message='Wellfound provider not yet implemented',
        )


wellfound_provider = WellfoundProvider()
provider_registry.register(wellfound_provider)