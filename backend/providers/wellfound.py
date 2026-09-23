import re
import logging
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

logger = logging.getLogger(__name__)


class WellfoundProvider(JobPortalProvider):
    """Wellfound (AngelList) provider with job search and Easy Apply."""

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
        cover_letter=True,
    )

    SELECTORS = {
        'logged_in_indicators': [
            '[data-test="user-menu"]',
            '.user-avatar',
            'nav .profile',
            '[class*="UserMenu"]',
        ],
        'search_keywords': 'input[placeholder*="Search"], input[name="query"], input[type="search"]',
        'search_location': 'input[placeholder*="Location"], input[name="location"]',
        'search_button': 'button[type="submit"], button:has-text("Search")',
        'job_cards': '[data-test="JobCard"], .job-listing, [class*="JobCard"], a[href*="/jobs/"]',
        'job_title': 'h2, h3, [class*="title"], [data-test="job-title"]',
        'job_company': '[class*="company"], [data-test="company-name"]',
        'job_location': '[class*="location"], [data-test="location"]',
        'job_link': 'a[href*="/jobs/"]',
        'job_detail_title': 'h1, [class*="JobTitle"], [data-test="job-title"]',
        'job_detail_company': '[class*="company-name"], [data-test="company-name"]',
        'job_detail_location': '[class*="location"], [data-test="location"]',
        'job_detail_description': '[class*="job-description"], [data-test="job-description"], .job-description',
        'apply_button': 'button:has-text("Apply"), a:has-text("Apply"), button:has-text("Quick Apply")',
        'easy_apply_button': 'button:has-text("Easy Apply"), button:has-text("Apply Now")',
    }

    async def search_jobs(self, page: Page, config: SearchConfig) -> List[JobCard]:
        try:
            from urllib.parse import urlencode

            params = {
                'q': ' '.join(config.keywords[:3]) if config.keywords else '',
                'l': config.locations[0] if config.locations else '',
            }
            if config.remote:
                params['remote'] = 'true'
            params = {k: v for k, v in params.items() if v}

            search_url = f'{self.SEARCH_URL}?{urlencode(params)}'
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)

            # Scroll to load more
            for _ in range(3):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(1500)

            cards = await page.query_selector_all(self.SELECTORS['job_cards'])
            jobs = []

            for card in cards[:config.max_results]:
                try:
                    job = await self.extract_job_card(page, card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug('Failed to extract Wellfound job card: %s', e)
                    continue

            return jobs
        except Exception as e:
            logger.error('Error searching Wellfound: %s', e)
            return []

    async def extract_job_card(self, page: Page, card_element) -> Optional[JobCard]:
        try:
            title_elem = await card_element.query_selector(self.SELECTORS['job_title'])
            if not title_elem:
                return None

            title = await title_elem.inner_text()
            link = await card_element.query_selector(self.SELECTORS['job_link'])
            url = await link.get_attribute('href') if link else None
            if url and not url.startswith('http'):
                url = f'{self.BASE_URL}{url}'

            company_elem = await card_element.query_selector(self.SELECTORS['job_company'])
            company = await company_elem.inner_text() if company_elem else ''

            location_elem = await card_element.query_selector(self.SELECTORS['job_location'])
            location = await location_elem.inner_text() if location_elem else ''

            external_id = ''
            if url:
                match = re.search(r'/jobs/(\d+)', url)
                if match:
                    external_id = match.group(1)

            return JobCard(
                external_id=external_id or url or '',
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                url=url,
            )
        except Exception as e:
            logger.debug('Failed to extract Wellfound card: %s', e)
            return None

    async def extract_job_detail(self, page: Page, job_url: str) -> JobDetail:
        await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)

        title = ''
        company = ''
        location = ''
        description = ''
        skills = []

        for sel in self.SELECTORS['job_detail_title'].split(', '):
            elem = await page.query_selector(sel.strip())
            if elem:
                title = await elem.inner_text()
                break

        for sel in self.SELECTORS['job_detail_company'].split(', '):
            elem = await page.query_selector(sel.strip())
            if elem:
                company = await elem.inner_text()
                break

        for sel in self.SELECTORS['job_detail_location'].split(', '):
            elem = await page.query_selector(sel.strip())
            if elem:
                location = await elem.inner_text()
                break

        for sel in self.SELECTORS['job_detail_description'].split(', '):
            elem = await page.query_selector(sel.strip())
            if elem:
                description = await elem.inner_text()
                break

        if description:
            skill_keywords = [
                'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'React', 'Vue', 'Angular',
                'Node.js', 'Django', 'Flask', 'FastAPI', 'PostgreSQL', 'MySQL', 'MongoDB',
                'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Git',
            ]
            desc_lower = description.lower()
            for skill in skill_keywords:
                if skill.lower() in desc_lower:
                    skills.append(skill)

        external_id = ''
        match = re.search(r'/jobs/(\d+)', job_url)
        if match:
            external_id = match.group(1)

        return JobDetail(
            external_id=external_id,
            title=title.strip(),
            company=company.strip(),
            location=location.strip(),
            description=description.strip(),
            skills=skills,
            application_url=job_url,
        )

    async def can_apply(self, page: Page, job: JobDetail) -> bool:
        try:
            for sel in ['apply_button', 'easy_apply_button']:
                btn = await page.query_selector(self.SELECTORS[sel])
                if btn and await btn.is_visible():
                    return True
            return False
        except Exception:
            return False

    async def prepare_application(self, page: Page, job: JobDetail, candidate: CandidateProfile) -> bool:
        try:
            for sel in ['easy_apply_button', 'apply_button']:
                btn = await page.query_selector(self.SELECTORS[sel])
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    return True
            return False
        except Exception as e:
            logger.error('Error preparing Wellfound application: %s', e)
            return False

    async def submit_application(self, page: Page) -> ApplicationResult:
        from backend.config import DRY_RUN

        if DRY_RUN:
            return ApplicationResult(
                success=True,
                status='dry_run',
                message='DRY_RUN mode - application not submitted',
            )

        try:
            submit_selectors = [
                'button:has-text("Submit")',
                'button:has-text("Send Application")',
                'button:has-text("Apply")',
                'button[type="submit"]',
            ]

            for selector in submit_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click()
                        break
                except Exception:
                    continue

            await page.wait_for_timeout(3000)
            return await self.detect_application_result(page)

        except Exception as e:
            return ApplicationResult(
                success=False,
                status='failed',
                message=str(e),
            )

    async def detect_application_result(self, page: Page) -> ApplicationResult:
        success_selectors = [
            'text=Application submitted',
            'text=Applied successfully',
            'text=Your application has been sent',
            '.success-message',
        ]
        for sel in success_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem and await elem.is_visible():
                    return ApplicationResult(
                        success=True,
                        status='submitted',
                        message='Application submitted successfully',
                    )
            except Exception:
                continue

        already_selectors = [
            'text=Already applied',
            '.already-applied',
        ]
        for sel in already_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem and await elem.is_visible():
                    return ApplicationResult(
                        success=False,
                        status='already_applied',
                        message='Already applied to this job',
                    )
            except Exception:
                continue

        return ApplicationResult(
            success=False,
            status='unknown',
            message='Could not determine application result',
        )


wellfound_provider = WellfoundProvider()
provider_registry.register(wellfound_provider)
