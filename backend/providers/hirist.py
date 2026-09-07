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


class HiristProvider(JobPortalProvider):
    """Hirist provider."""
    
    name = 'hirist'
    platform_name = 'hirist'
    
    BASE_URL = 'https://www.hirist.com'
    LOGIN_URL = 'https://www.hirist.com/login'
    HOME_URL = 'https://www.hirist.com/candidate/dashboard'
    SEARCH_URL = 'https://www.hirist.com/jobs'
    
    capabilities = PortalCapabilities(
        job_search=True,
        easy_apply=True,
    )
    
    SELECTORS = {
        'logged_in_indicators': [
            '.user-profile',
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
            message='Hirist provider not yet implemented',
        )
    
    async def detect_application_result(self, page: Page) -> ApplicationResult:
        return ApplicationResult(
            success=False,
            status='not_implemented',
            message='Hirist provider not yet implemented',
        )


hirist_provider = HiristProvider()
provider_registry.register(hirist_provider)