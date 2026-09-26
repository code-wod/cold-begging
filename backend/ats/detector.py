"""ATS platform detection from URL and page content."""
import re
from typing import Optional


ATS_PATTERNS = {
    'greenhouse': [
        r'boards\.greenhouse\.io',
        r'\.greenhouse\.io/jobs',
    ],
    'lever': [
        r'jobs\.lever\.co',
        r'\.lever\.co/',
    ],
    'ashby': [
        r'jobs\.ashbyhq\.com',
        r'\.ashbyhq\.com/',
    ],
    'workday': [
        r'myworkdayjobs\.com',
        r'workday\.com',
        r'wd5\.myworkdayjobs\.com',
    ],
    'bamboohr': [
        r'\.bamboohr\.com',
    ],
    'icims': [
        r'\.icims\.com',
    ],
    'jobvite': [
        r'\.jobvite\.com',
    ],
    'smartrecruiters': [
        r'\.smartrecruiters\.com',
    ],
}


async def detect_ats(url: str, page=None) -> str:
    """Detect ATS platform from URL pattern and optional page content."""
    url_lower = url.lower()

    # Check URL patterns first
    for platform, patterns in ATS_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url_lower):
                return platform

    # If page is available, check meta tags and page content
    if page:
        try:
            content = await page.content()
            content_lower = content.lower()

            if 'greenhouse' in content_lower and 'application' in content_lower:
                return 'greenhouse'
            if 'lever' in content_lower and 'application-form' in content_lower:
                return 'lever'
            if 'ashby' in content_lower:
                return 'ashby'
            if 'workday' in content_lower:
                return 'workday'
        except Exception:
            pass

    return 'unknown'


def get_adapter(platform: str):
    """Get the ATS adapter for a detected platform."""
    from . import ADAPTERS
    return ADAPTERS.get(platform)
