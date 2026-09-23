"""Base ATS adapter interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class ATSAdapter(ABC):
    """Abstract base class for ATS-specific form handling."""

    name: str = 'base'
    supported_domains: List[str] = []

    @abstractmethod
    async def can_handle(self, url: str, page) -> bool:
        """Check if this adapter can handle the given URL/page."""
        ...

    @abstractmethod
    async def extract_fields(self, page) -> List[Dict[str, Any]]:
        """Extract all application form fields from the page."""
        ...

    @abstractmethod
    async def fill_field(self, page, field: Dict[str, Any], value: str) -> bool:
        """Fill a single field. Returns True if successful."""
        ...

    @abstractmethod
    async def upload_resume(self, page, file_path: str) -> bool:
        """Upload a resume file. Returns True if successful."""
        ...

    @abstractmethod
    async def validate(self, page) -> Dict[str, Any]:
        """Validate the form. Returns {valid: bool, errors: [...]}"""
        ...

    @abstractmethod
    async def submit(self, page) -> Dict[str, Any]:
        """Submit the form. Returns {success: bool, message: str}"""
        ...
