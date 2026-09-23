from typing import Dict, List, Optional
from .base import JobSourceProvider, JobSourceCapabilities
from .manual import manual_provider
from .greenhouse import greenhouse_provider
from .lever import lever_provider
from .ashby import ashby_provider
from .generic import generic_provider


class ProviderRegistry:
    """Registry for job source providers."""
    
    def __init__(self):
        self._providers: Dict[str, JobSourceProvider] = {
            'manual': manual_provider,
            'greenhouse': greenhouse_provider,
            'lever': lever_provider,
            'ashby': ashby_provider,
            'company': generic_provider,
        }
    
    def get_provider(self, name: str) -> Optional[JobSourceProvider]:
        return self._providers.get(name)
    
    def get_all_providers(self) -> List[JobSourceProvider]:
        return list(self._providers.values())
    
    def get_provider_names(self) -> List[str]:
        return list(self._providers.keys())
    
    def detect_provider(self, url: str) -> str:
        """Detect provider from URL."""
        url_lower = url.lower()
        
        if 'greenhouse.io' in url_lower:
            return 'greenhouse'
        if 'lever.co' in url_lower:
            return 'lever'
        if 'ashbyhq.com' in url_lower:
            return 'ashby'
        
        # Check for known ATS
        ats_domains = {
            'workday': 'company',
            'myworkdayjobs': 'company',
            'bamboohr': 'company',
            'icims': 'company',
            'jobvite': 'company',
            'smartrecruiters': 'company',
            'recruitee': 'company',
            'personio': 'company',
            'teamtailor': 'company',
        }
        
        for domain, provider in ats_domains.items():
            if domain in url_lower:
                return provider
        
        return 'manual'
    
    def get_capabilities(self, name: str) -> Optional[JobSourceCapabilities]:
        provider = self.get_provider(name)
        if provider:
            return provider.get_capabilities()
        return None


provider_registry = ProviderRegistry()