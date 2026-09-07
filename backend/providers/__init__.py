from .base import (
    JobPortalProvider,
    ProviderRegistry,
    PortalCapabilities,
    PortalCapability,
    SearchConfig,
    JobCard,
    JobDetail,
    ApplicationResult,
    CandidateProfile,
    provider_registry,
)

# Import providers to trigger registration
from .linkedin import LinkedInProvider
from .naukri import NaukriProvider
from .wellfound import WellfoundProvider
from .hirist import HiristProvider
from .instahyre import InstahyreProvider

__all__ = [
    'JobPortalProvider',
    'ProviderRegistry',
    'PortalCapabilities',
    'PortalCapability',
    'SearchConfig',
    'JobCard',
    'JobDetail',
    'ApplicationResult',
    'CandidateProfile',
    'provider_registry',
    'LinkedInProvider',
    'NaukriProvider',
    'WellfoundProvider',
    'HiristProvider',
    'InstahyreProvider',
]