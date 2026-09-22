import re
import json
import logging
from typing import List, Optional
from urllib.parse import urlencode
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


class InstahyreProvider(JobPortalProvider):
    """Instahyre provider — search via opportunities page, single-click 'Interested' apply."""

    name = 'instahyre'
    platform_name = 'instahyre'

    BASE_URL = 'https://www.instahyre.com'
    LOGIN_URL = 'https://www.instahyre.com/login'
    DASHBOARD_URL = 'https://www.instahyre.com/candidate/profile/'
    SEARCH_URL = 'https://www.instahyre.com/candidate/opportunities/'

    capabilities = PortalCapabilities(
        job_search=True,
        easy_apply=True,
        one_click_apply=True,
        resume_upload=False,
        cover_letter=False,
        screening_questions=False,
    )

    async def search_jobs(self, page: Page, config: SearchConfig) -> List[JobCard]:
        """Search Instahyre using the full opportunities URL with all required params."""
        try:
            # Instahyre requires these params or it redirects to ?matching=true
            params = {
                'company_size': '0',
                'industry_types': '13',
                'job_functions': '/api/v1/job_category/1',
                'job_type': '0',
                'location': 'Anywhere in India',
                'search': 'true',
                'skills': 'Software engineer',
                'years': '1',
            }

            # Override with user preferences
            if config.keywords:
                params['skills'] = ','.join(config.keywords[:5])
            if config.locations:
                params['location'] = config.locations[0]
            if config.experience_min:
                params['years'] = str(config.experience_min)

            search_url = f'{self.SEARCH_URL}?{urlencode(params)}'
            logger.info('Instahyre search URL: %s', search_url)

            await page.goto(search_url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(5000)

            # Check if redirected to login — session expired
            if '/login' in page.url.lower():
                logger.warning('Instahyre redirected to login — session expired for this user')
                return []

            # Scroll slowly to trigger lazy loading
            for i in range(5):
                await page.evaluate('window.scrollBy(0, 800)')
                await page.wait_for_timeout(2000)

            # Try multiple selector strategies for job cards
            cards = []

            # Strategy 1: Look for opportunity cards by common patterns
            selectors = [
                '[class*="opportunity"]',
                '[class*="OpportunityCard"]',
                '[class*="job-card"]',
                '[class*="JobCard"]',
                '[data-testid*="opportunity"]',
                '[data-testid*="job"]',
                '.card',
            ]
            for sel in selectors:
                cards = await page.query_selector_all(sel)
                if cards:
                    logger.info('Found %d cards with selector: %s', len(cards), sel)
                    break

            # Strategy 2: Find all links that go to job detail pages
            if not cards:
                links = await page.query_selector_all('a[href*="/candidate/job/"]')
                if links:
                    logger.info('Found %d job links', len(links))
                    # Use parent containers of job links
                    for link in links:
                        parent = await link.evaluate_handle('el => el.closest("div[class]") || el.parentElement')
                        if parent:
                            cards.append(parent.as_element())

            # Strategy 3: Just grab all visible card-like elements
            if not cards:
                all_divs = await page.query_selector_all('div')
                for div in all_divs:
                    try:
                        text = await div.inner_text()
                        if text and len(text) > 50 and len(text) < 2000:
                            has_link = await div.query_selector('a[href]')
                            if has_link:
                                classes = await div.get_attribute('class') or ''
                                if any(k in classes.lower() for k in ['card', 'item', 'opportunity', 'job']):
                                    cards.append(div)
                    except Exception:
                        continue

            logger.info('Total candidate elements: %d', len(cards))

            jobs = []
            seen_urls = set()

            # Extract jobs from links if cards approach failed
            if not cards:
                links = await page.query_selector_all('a[href*="/candidate/job/"]')
                for link in links[:config.max_results]:
                    try:
                        href = await link.get_attribute('href')
                        if not href:
                            continue
                        url = href if href.startswith('http') else f'{self.BASE_URL}{href}'
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)

                        title = (await link.inner_text()).strip()
                        if not title or len(title) < 3:
                            continue

                        jobs.append(JobCard(
                            external_id=url,
                            title=title,
                            company='',
                            location='',
                            url=url,
                        ))
                    except Exception as e:
                        logger.debug('Failed to extract link: %s', e)
                        continue
            else:
                for card in cards[:config.max_results]:
                    try:
                        job = await self._extract_card(card)
                        if job and job.url not in seen_urls:
                            seen_urls.add(job.url)
                            jobs.append(job)
                    except Exception as e:
                        logger.debug('Failed to extract card: %s', e)
                        continue

            logger.info('Instahyre search found %d jobs', len(jobs))
            return jobs

        except Exception as e:
            logger.error('Instahyre search error: %s', e)
            return []

    async def _extract_card(self, card) -> Optional[JobCard]:
        """Extract a single job card element into a JobCard."""
        # Get link first
        url = ''
        link = await card.query_selector('a[href*="/candidate/job/"]')
        if not link:
            link = await card.query_selector('a[href]')
        if link:
            href = await link.get_attribute('href')
            if href:
                url = href if href.startswith('http') else f'{self.BASE_URL}{href}'

        if not url:
            return None

        # Get title from link or card
        title = ''
        if link:
            title = (await link.inner_text()).strip()
        if not title:
            for sel in ['h2', 'h3', '[class*="title"]', 'strong', 'b']:
                elem = await card.query_selector(sel)
                if elem:
                    title = (await elem.inner_text()).strip()
                    if title:
                        break

        if not title or len(title) < 3:
            return None

        # Company
        company = ''
        for sel in ['[class*="company"]', '[class*="recruiter"]', 'span']:
            elem = await card.query_selector(sel)
            if elem:
                text = (await elem.inner_text()).strip()
                if text and text != title and len(text) < 100:
                    company = text
                    break

        # Location
        location = ''
        for sel in ['[class*="location"]', '[class*="meta"]']:
            elem = await card.query_selector(sel)
            if elem:
                location = (await elem.inner_text()).strip()
                if location:
                    break

        return JobCard(
            external_id=url,
            title=title,
            company=company,
            location=location,
            url=url,
        )

    async def extract_job_detail(self, page: Page, job_url: str) -> JobDetail:
        """Navigate to job page and extract details."""
        await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(3000)

        title = await self._text(page, 'h1, [class*="title"], [class*="role"]')
        company = await self._text(page, '[class*="company"]')
        location = await self._text(page, '[class*="location"]')
        description = await self._text(page, '[class*="description"], [class*="about"], .job-description')

        skills = []
        skill_elems = await page.query_selector_all('[class*="skill"], [class*="tag"], [class*="badge"]')
        for elem in skill_elems:
            text = (await elem.inner_text()).strip()
            if text and len(text) < 50:
                skills.append(text)

        return JobDetail(
            external_id=job_url,
            title=title,
            company=company,
            location=location,
            description=description,
            skills=skills,
            application_url=job_url,
        )

    async def _text(self, page: Page, selectors: str) -> str:
        """Get text from first matching selector."""
        for sel in selectors.split(', '):
            try:
                elem = await page.query_selector(sel.strip())
                if elem:
                    text = (await elem.inner_text()).strip()
                    if text:
                        return text
            except Exception:
                continue
        return ''

    async def can_apply(self, page: Page, job: JobDetail) -> bool:
        """Check if the 'Interested' or 'Apply' button is visible."""
        btn = await self._find_apply_button(page)
        return btn is not None

    async def prepare_application(self, page: Page, job: JobDetail, candidate: CandidateProfile) -> bool:
        """Navigate to job page and find the apply button."""
        if '/candidate/job/' not in page.url and job.application_url:
            await page.goto(job.application_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
        return True

    async def submit_application(self, page: Page) -> ApplicationResult:
        """Single-click 'Interested' / 'Apply' button."""
        from backend.config import DRY_RUN

        btn = await self._find_apply_button(page)
        if not btn:
            return ApplicationResult(
                success=False,
                status='no_button',
                message='No apply/interested button found',
            )

        btn_text = (await btn.inner_text()).strip()

        if DRY_RUN:
            return ApplicationResult(
                success=True,
                status='dry_run',
                message=f'DRY_RUN — would click "{btn_text}"',
            )

        try:
            await btn.click()
            await page.wait_for_timeout(3000)
        except Exception as e:
            return ApplicationResult(
                success=False,
                status='click_failed',
                message=f'Failed to click button: {e}',
            )

        return await self._detect_result(page, btn_text)

    async def _find_apply_button(self, page: Page):
        """Find the Interested/Apply button on a job detail page."""
        selectors = [
            'button:has-text("Interested")',
            'button:has-text("Apply")',
            'button:has-text("Easy Apply")',
            "button:has-text(\"I'm Interested\")",
            '[class*="interested"]',
            '[class*="apply-btn"]',
            'div[class*="apply"]',
        ]
        for sel in selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    text = (await btn.inner_text()).strip().lower()
                    if 'applied' in text:
                        return None
                    return btn
            except Exception:
                continue
        return None

    async def _detect_result(self, page: Page, button_text: str) -> ApplicationResult:
        """Detect if the application was successful after clicking."""
        success_sels = [
            'text=Interest shown',
            'text=Applied successfully',
            'text=Application submitted',
            "text=You've already shown interest",
            '[class*="success"]',
            '.toast-success',
        ]
        for sel in success_sels:
            try:
                elem = await page.query_selector(sel)
                if elem and await elem.is_visible():
                    msg = (await elem.inner_text()).strip()
                    if 'already' in msg.lower():
                        return ApplicationResult(success=False, status='already_applied', message=msg)
                    return ApplicationResult(success=True, status='submitted', message=msg or f'Clicked "{button_text}"')
            except Exception:
                continue

        btn = await self._find_apply_button(page)
        if btn:
            new_text = (await btn.inner_text()).strip().lower()
            if 'applied' in new_text:
                return ApplicationResult(success=True, status='submitted', message='Button changed to Applied state')
        else:
            return ApplicationResult(success=True, status='submitted', message=f'Clicked "{button_text}" — button gone')

        return ApplicationResult(success=False, status='unknown', message=f'Clicked "{button_text}" but could not confirm')

    async def detect_application_result(self, page: Page) -> ApplicationResult:
        return await self._detect_result(page, '')


instahyre_provider = InstahyreProvider()
provider_registry.register(instahyre_provider)
