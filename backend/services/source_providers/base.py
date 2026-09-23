from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import datetime as dt


@dataclass
class JobListing:
    """Normalized job listing from a source."""
    external_id: str
    title: str
    company_name: str
    company_url: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None  # remote, hybrid, onsite
    employment_type: Optional[str] = None  # full_time, part_time, contract, internship
    experience_level: Optional[str] = None  # entry, junior, mid, senior, lead, principal
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = 'USD'
    description: str = ''
    requirements: str = ''
    skills: List[str] = None
    application_url: Optional[str] = None
    posted_at: Optional[dt.datetime] = None
    source_data: dict = None

    def __post_init__(self):
        if self.skills is None:
            self.skills = []
        if self.source_data is None:
            self.source_data = {}


@dataclass
class JobSearchParams:
    """Parameters for job search."""
    query: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[bool] = None
    experience_level: Optional[str] = None
    employment_type: Optional[str] = None
    limit: int = 50
    page: int = 1


@dataclass
class JobSourceCapabilities:
    """Capabilities of a job source provider."""
    search: bool = False
    job_details: bool = False
    application_api: bool = False
    candidate_apply_api: bool = False


class JobSourceProvider(ABC):
    """Abstract base class for job source providers."""
    
    name: str = ''
    capabilities: JobSourceCapabilities = JobSourceCapabilities()
    
    @abstractmethod
    async def search_jobs(self, params: JobSearchParams) -> List[JobListing]:
        """Search for jobs matching the given parameters."""
        pass
    
    @abstractmethod
    async def get_job(self, job_url: str) -> Optional[JobListing]:
        """Fetch detailed job information from a URL."""
        pass
    
    def get_capabilities(self) -> JobSourceCapabilities:
        return self.capabilities
    
    def compute_job_hash(self, listing: JobListing) -> str:
        """Compute a deterministic hash for deduplication."""
        import hashlib
        # Normalize fields for deduplication
        company = listing.company_name.strip().lower()
        title = listing.title.strip().lower()
        location = (listing.location or '').strip().lower()
        url = (listing.application_url or '').strip().lower()
        content = f"{company}|{title}|{location}|{url}"
        return hashlib.sha256(content.encode()).hexdigest()[:64]