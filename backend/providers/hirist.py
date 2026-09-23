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


class HiristProvider(JobPortalProvider):
    """Hirist provider — search jobfeed, single-click apply."""

    name = 'hirist'
    platform_name = 'hirist'

    BASE_URL = 'https://www.hirist.tech'
    LOGIN_URL = 'https://www.hirist.tech/login'
    PROFILE_URL = 'https://www.hirist.tech/myprofile'
    SEARCH_URL = 'https://www.hirist.tech/jobfeed'

    capabilities = PortalCapabilities(
        job_search=True,
        easy_apply=True,
        one_click_apply=True,
        resume_upload=False,
        cover_letter=False,
        screening_questions=False,
    )

    async def search_jobs(self, page: Page, config: SearchConfig) -> List[JobCard]:
        """Search Hirist jobfeed using correct URL params."""
        try:
            # Build search URL matching the working format
            params = {
                'minexp': '0',
                'maxexp': '5',
                'sort': 'date',
                'loc': 'Anywhere-in-India',
                'posting': '3',
            }

            # Override with user preferences
            if config.experience_min:
                params['minexp'] = str(config.experience_min)
            if config.experience_max:
                params['maxexp'] = str(config.experience_max)
            if config.locations:
                # Hirist uses hyphenated location format
                loc = config.locations[0].replace(' ', '-').replace(',', '_')
                params['loc'] = loc

            # Add keyword as separate param if supported
            if config.keywords:
                params['keyword'] = ' '.join(config.keywords[:3])

            search_url = f'{self.SEARCH_URL}?{urlencode(params)}'
            logger.info('Hirist search URL: %s', search_url)

            await page.goto(search_url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(3000)

            # Check if redirected to login
            if '/login' in page.url.lower():
                logger.warning('Hirist redirected to login — session expired')
                return []

            # Scroll to load jobs
            for _ in range(5):
                await page.evaluate('window.scrollBy(0, 800)')
                await page.wait_for_timeout(1500)

            # Find job cards — Hirist uses various patterns
            cards = []
            selectors = [
                '[class*="job-card"]',
                '[class*="JobCard"]',
                '[class*="job-item"]',
                '[class*="feed-item"]',
                '[class*="card"]',
            ]
            for sel in selectors:
                cards = await page.query_selector_all(sel)
                if cards:
                    logger.info('Found %d cards with: %s', len(cards), sel)
                    break

            # Fallback: find all job links
            if not cards:
                links = await page.query_selector_all('a[href*="/job/"]')
                logger.info('Found %d job links as fallback', len(links))

            jobs = []
            seen_urls = set()

            # Extract from links directly
            links = await page.query_selector_all('a[href*="/job/"]')
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
                        # Try getting text from parent
                        parent = await link.evaluate_handle('el => el.parentElement')
                        if parent:
                            title = (await parent.inner_text()).strip()
                    if not title or len(title) < 3:
                        continue

                    # Get company from nearby elements
                    company = ''
                    parent = await link.evaluate_handle('el => el.closest("[class]") || el.parentElement')
                    if parent:
                        company_elem = await parent.as_element().query_selector('[class*="company"], [class*="recruiter"], span')
                        if company_elem:
                            company = (await company_elem.inner_text()).strip()

                    jobs.append(JobCard(
                        external_id=url,
                        title=title[:200],
                        company=company[:100],
                        location='',
                        url=url,
                    ))
                except Exception as e:
                    logger.debug('Failed to extract link: %s', e)
                    continue

            # If still no jobs, try extracting from cards
            if not jobs and cards:
                for card in cards[:config.max_results]:
                    try:
                        job = await self._extract_card(card)
                        if job and job.url not in seen_urls:
                            seen_urls.add(job.url)
                            jobs.append(job)
                    except Exception as e:
                        logger.debug('Failed to extract card: %s', e)
                        continue

            logger.info('Hirist search found %d jobs', len(jobs))
            return jobs

        except Exception as e:
            logger.error('Hirist search error: %s', e)
            return []

    async def _extract_card(self, card) -> Optional[JobCard]:
        """Extract from a card element."""
        url = ''
        link = await card.query_selector('a[href*="/job/"]')
        if not link:
            link = await card.query_selector('a[href]')
        if link:
            href = await link.get_attribute('href')
            if href:
                url = href if href.startswith('http') else f'{self.BASE_URL}{href}'

        if not url:
            return None

        title = ''
        for sel in ['h2', 'h3', '[class*="title"]', 'strong', 'b']:
            elem = await card.query_selector(sel)
            if elem:
                title = (await elem.inner_text()).strip()
                if title:
                    break

        if not title or len(title) < 3:
            return None

        company = ''
        for sel in ['[class*="company"]', '[class*="recruiter"]']:
            elem = await card.query_selector(sel)
            if elem:
                company = (await elem.inner_text()).strip()
                if company:
                    break

        return JobCard(external_id=url, title=title, company=company, location='', url=url)

    async def extract_job_detail(self, page: Page, job_url: str) -> JobDetail:
        await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(3000)

        title = await self._text(page, 'h1, [class*="title"]')
        company = await self._text(page, '[class*="company"]')
        location = await self._text(page, '[class*="location"]')
        description = await self._text(page, '[class*="description"], [class*="about"]')

        skills = []
        skill_elems = await page.query_selector_all('[class*="skill"], [class*="tag"]')
        for elem in skill_elems:
            text = (await elem.inner_text()).strip()
            if text and len(text) < 50:
                skills.append(text)

        return JobDetail(
            external_id=job_url, title=title, company=company, location=location,
            description=description, skills=skills, application_url=job_url,
        )

    async def _text(self, page: Page, selectors: str) -> str:
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
        btn = await self._find_apply_button(page)
        return btn is not None

    async def prepare_application(self, page: Page, job: JobDetail, candidate: CandidateProfile) -> bool:
        if '/job/' not in page.url and job.application_url:
            await page.goto(job.application_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
        return True

    async def submit_application(self, page: Page) -> ApplicationResult:
        from backend.config import DRY_RUN

        btn = await self._find_apply_button(page)
        if not btn:
            return ApplicationResult(success=False, status='no_button', message='No apply button found')

        btn_text = (await btn.inner_text()).strip()

        if DRY_RUN:
            return ApplicationResult(success=True, status='dry_run', message=f'DRY_RUN — would click "{btn_text}"')

        try:
            await btn.click()
            await page.wait_for_timeout(3000)
        except Exception as e:
            return ApplicationResult(success=False, status='click_failed', message=str(e))

        return await self._detect_result(page, btn_text)

    async def _find_apply_button(self, page: Page):
        selectors = [
            'button:has-text("Apply")',
            'button:has-text("Easy Apply")',
            'a:has-text("Apply")',
            '[class*="apply"]',
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
        success_sels = [
            'text=Applied successfully', 'text=Application submitted',
            'text=Interest shown', '[class*="success"]',
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
                return ApplicationResult(success=True, status='submitted', message='Button changed to Applied')
        else:
            return ApplicationResult(success=True, status='submitted', message=f'Clicked "{button_text}" — button gone')

        return ApplicationResult(success=False, status='unknown', message=f'Clicked "{button_text}" — unconfirmed')

    async def detect_application_result(self, page: Page) -> ApplicationResult:
        return await self._detect_result(page, '')


hirist_provider = HiristProvider()
provider_registry.register(hirist_provider)
