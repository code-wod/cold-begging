from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class PortalCapability(Enum):
    JOB_SEARCH = 'job_search'
    EASY_APPLY = 'easy_apply'
    ONE_CLICK_APPLY = 'one_click_apply'
    MULTI_STEP_FORM = 'multi_step_form'
    RESUME_UPLOAD = 'resume_upload'
    COVER_LETTER = 'cover_letter'
    SCREENING_QUESTIONS = 'screening_questions'
    EXTERNAL_REDIRECT = 'external_redirect'


@dataclass
class PortalCapabilities:
    """Capabilities of a job portal."""
    job_search: bool = True
    easy_apply: bool = False
    one_click_apply: bool = False
    multi_step_form: bool = False
    resume_upload: bool = False
    cover_letter: bool = False
    screening_questions: bool = False
    external_redirect: bool = False
    
    def to_list(self) -> List[str]:
        caps = []
        for cap in PortalCapability:
            if getattr(self, cap.value, False):
                caps.append(cap.value)
        return caps


@dataclass
class SearchConfig:
    """Configuration for job search."""
    keywords: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    remote: bool = False
    job_types: List[str] = field(default_factory=list)
    salary_min: Optional[int] = None
    companies: List[str] = field(default_factory=list)
    excluded_companies: List[str] = field(default_factory=list)
    excluded_keywords: List[str] = field(default_factory=list)
    max_results: int = 50
    sort_by: str = 'relevance'  # relevance, date, salary


@dataclass
class JobCard:
    """Basic job info from search results."""
    external_id: str
    title: str
    company: str
    location: Optional[str] = None
    url: Optional[str] = None
    posted_date: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None
    remote: bool = False
    snippet: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobDetail:
    """Full job details after extraction."""
    external_id: str
    title: str
    company: str
    location: Optional[str] = None
    description: str = ''
    requirements: str = ''
    responsibilities: str = ''
    skills: List[str] = field(default_factory=list)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = 'USD'
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    remote_type: Optional[str] = None
    application_url: Optional[str] = None
    posted_date: Optional[str] = None
    company_url: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    benefits: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApplicationResult:
    """Result of an application attempt."""
    success: bool
    status: str  # submitted, already_applied, failed, requires_input, dry_run
    message: str
    application_id: Optional[str] = None
    submitted_at: Optional[str] = None
    error: Optional[str] = None
    requires_user_input: Optional[Dict[str, Any]] = None
    screenshot: Optional[bytes] = None


@dataclass
class CandidateProfile:
    """Candidate profile for application filling."""
    full_name: str
    email: str
    phone: str
    location: str
    linkedin_url: str = ''
    github_url: str = ''
    portfolio_url: str = ''
    years_experience: int = 0
    skills: List[str] = field(default_factory=list)
    current_company: str = ''
    current_role: str = ''
    notice_period: str = ''
    work_authorization: str = ''
    willing_to_relocate: bool = False
    salary_expectation: Optional[int] = None
    preferred_locations: List[str] = field(default_factory=list)
    resume_files: Dict[str, str] = field(default_factory=dict)  # variant -> path


class JobPortalProvider(ABC):
    """Abstract base class for job portal providers."""
    
    name: str = ''
    capabilities: PortalCapabilities = PortalCapabilities()
    
    # Platform URLs
    BASE_URL: str = ''
    LOGIN_URL: str = ''
    HOME_URL: str = ''
    SEARCH_URL: str = ''
    
    # Selectors (to be overridden)
    SELECTORS: Dict[str, Any] = {}
    
    def __init__(self):
        self._session_manager = None
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name (e.g., 'linkedin')."""
        pass
    
    def get_session_manager(self):
        """Lazy load session manager to avoid circular imports."""
        if self._session_manager is None:
            from backend.browser.session import get_session_manager
            self._session_manager = get_session_manager()
        return self._session_manager
    
    # ==================== Session Management ====================
    
    async def verify_session(self, page, user_id: int) -> bool:
        """Check if the current page/session is logged in."""
        return await self._check_logged_in(page)
    
    async def ensure_login(self, user_id: int, headless: bool = False) -> bool:
        """Ensure user is logged in, opening browser for manual login if needed."""
        session_manager = self.get_session_manager()
        return await session_manager.ensure_login(user_id, self.platform_name, headless)
    
    async def _check_logged_in(self, page) -> bool:
        """Check if page indicates logged-in state."""
        for selector in self.SELECTORS.get('logged_in_indicators', []):
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    return True
            except Exception:
                continue
        return False
    
    # ==================== Job Search ====================
    
    @abstractmethod
    async def search_jobs(self, page, config: SearchConfig) -> List[JobCard]:
        """Search for jobs matching the config."""
        pass
    
    async def extract_job_card(self, page, card_element) -> Optional[JobCard]:
        """Extract job info from a search result card."""
        return None
    
    # ==================== Job Detail ====================
    
    @abstractmethod
    async def extract_job_detail(self, page, job_url: str) -> JobDetail:
        """Extract full job details from a job page."""
        pass
    
    # ==================== Application ====================
    
    @abstractmethod
    async def can_apply(self, page, job: JobDetail) -> bool:
        """Check if this job can be applied to via this portal."""
        pass
    
    @abstractmethod
    async def prepare_application(
        self,
        page,
        job: JobDetail,
        candidate: CandidateProfile
    ) -> bool:
        """Prepare application form (fill fields, upload resume, etc.)."""
        pass
    
    @abstractmethod
    async def submit_application(self, page) -> ApplicationResult:
        """Submit the prepared application."""
        pass
    
    @abstractmethod
    async def detect_application_result(self, page) -> ApplicationResult:
        """Detect the result after submission attempt."""
        pass
    
    # ==================== Helper Methods ====================
    
    async def navigate_to_job(self, page, job_url: str) -> bool:
        """Navigate to a job page."""
        try:
            await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(2000)
            return True
        except Exception as e:
            return False
    
    async def fill_field(self, page, selector: str, value: str) -> bool:
        """Fill a form field."""
        try:
            await page.fill(selector, value)
            return True
        except Exception:
            return False
    
    async def click_element(self, page, selector: str) -> bool:
        """Click an element."""
        try:
            await page.click(selector)
            return True
        except Exception:
            return False
    
    async def upload_file(self, page, selector: str, file_path: str) -> bool:
        """Upload a file."""
        try:
            await page.set_input_files(selector, file_path)
            return True
        except Exception:
            return False
    
    async def wait_for_selector(self, page, selector: str, timeout: int = 10000) -> bool:
        """Wait for an element to appear."""
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False
    
    def get_capabilities(self) -> PortalCapabilities:
        return self.capabilities


class ProviderRegistry:
    """Registry for job portal providers."""
    
    def __init__(self):
        self._providers: Dict[str, JobPortalProvider] = {}
    
    def register(self, provider: JobPortalProvider):
        self._providers[provider.platform_name] = provider
    
    def get(self, platform: str) -> Optional[JobPortalProvider]:
        return self._providers.get(platform)
    
    def get_all(self) -> List[JobPortalProvider]:
        return list(self._providers.values())
    
    def get_names(self) -> List[str]:
        return list(self._providers.keys())
    
    def get_capabilities(self, platform: str) -> Optional[PortalCapabilities]:
        provider = self.get(platform)
        return provider.get_capabilities() if provider else None


provider_registry = ProviderRegistry()