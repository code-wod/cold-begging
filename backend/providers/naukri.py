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


class NaukriProvider(JobPortalProvider):
    """Naukri.com provider with job search and One Click Apply."""

    name = 'naukri'
    platform_name = 'naukri'

    BASE_URL = 'https://www.naukri.com'
    LOGIN_URL = 'https://www.naukri.com/nlogin/login'
    HOME_URL = 'https://www.naukri.com/mnjuser/homepage'
    SEARCH_URL = 'https://www.naukri.com/jobs'

    capabilities = PortalCapabilities(
        job_search=True,
        one_click_apply=True,
        easy_apply=True,
        resume_upload=True,
    )

    SELECTORS = {
        'logged_in_indicators': [
            '.mnj-header',
            '.user-name',
            '#usernameField[disabled]',
            '.naukri-clone',
            'nav[data-trk-id="header"]',
        ],
        'search_keywords': 'input[placeholder*="Skills"], input[name="qp"], input#keywordSearchBox',
        'search_location': 'input[placeholder*="Location"], input[name="ql"], input#locationSearchBox',
        'search_button': 'button[type="submit"], button[data-trk-id="search-button"]',
        'job_cards': '.jobTuple, .srp-jobtuple-wrapper, .jobTupleWrapper',
        'job_title': '.title a, .jobTupleHeader a, a.title',
        'job_company': '.subTitle, .companyInfo a, .company-name',
        'job_location': '.location, .locWdth, .job-location',
        'job_link': '.title a, .jobTupleHeader a, a.title',
        'job_detail_title': 'h1, .job-header h1, .jd-header h1',
        'job_detail_company': '.company-name, .jd-header .company-name',
        'job_detail_location': '.job-location, .jd-header .location',
        'job_detail_description': '.job-description, .jd-desc, #jobDescription',
        'job_detail_apply': 'button:has-text("Apply"), a:has-text("Apply"), .apply-button, button[data-trk-id="apply-button"]',
        'one_click_apply': 'button:has-text("One Click Apply"), button:has-text("Apply using Naukri")',
        'resume_selector': '.resumeSelector, [name="resume"], select.resumeDropdown',
        'apply_confirm': '.applyConfirmation, .successMessage, text=Your application has been submitted',
        'already_applied': 'text=You have already applied, .already-applied',
    }

    async def search_jobs(self, page: Page, config: SearchConfig) -> List[JobCard]:
        try:
            from urllib.parse import urlencode

            params = {
                'qp': ' '.join(config.keywords[:3]) if config.keywords else '',
                'ql': config.locations[0] if config.locations else '',
            }
            if config.remote:
                params['remote'] = '3'  # Naukri remote filter
            params = {k: v for k, v in params.items() if v}

            search_url = f'{self.SEARCH_URL}?{urlencode(params)}'
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)

            # Scroll to load more jobs
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
                    logger.debug('Failed to extract job card: %s', e)
                    continue

            return jobs
        except Exception as e:
            logger.error('Error searching Naukri: %s', e)
            return []

    async def extract_job_card(self, page: Page, card_element) -> Optional[JobCard]:
        try:
            title_elem = await card_element.query_selector(self.SELECTORS['job_title'])
            if not title_elem:
                return None

            title = await title_elem.inner_text()
            link = await title_elem.get_attribute('href')
            if link and not link.startswith('http'):
                link = f'{self.BASE_URL}{link}'

            company_elem = await card_element.query_selector(self.SELECTORS['job_company'])
            company = await company_elem.inner_text() if company_elem else ''

            location_elem = await card_element.query_selector(self.SELECTORS['job_location'])
            location = await location_elem.inner_text() if location_elem else ''

            external_id = ''
            if link:
                match = re.search(r'/job/(\d+)', link)
                if match:
                    external_id = match.group(1)

            return JobCard(
                external_id=external_id or link or '',
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                url=link,
            )
        except Exception as e:
            logger.debug('Failed to extract Naukri job card: %s', e)
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

        # Extract skills from description
        if description:
            skill_keywords = [
                'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'Golang', 'React', 'Vue', 'Angular',
                'Node.js', 'Django', 'Flask', 'FastAPI', 'Spring', 'Spring Boot',
                'PostgreSQL', 'MySQL', 'MongoDB', 'Redis',
                'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform',
                'Git', 'CI/CD', 'Jenkins', 'GraphQL', 'REST',
            ]
            desc_lower = description.lower()
            for skill in skill_keywords:
                if skill.lower() in desc_lower:
                    skills.append(skill)

        external_id = ''
        match = re.search(r'/job/(\d+)', job_url)
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
            apply_btn = await page.query_selector(self.SELECTORS['job_detail_apply'])
            if apply_btn and await apply_btn.is_visible():
                return True
            easy_apply = await page.query_selector(self.SELECTORS['one_click_apply'])
            if easy_apply and await easy_apply.is_visible():
                return True
            return False
        except Exception:
            return False

    async def prepare_application(self, page: Page, job: JobDetail, candidate: CandidateProfile) -> bool:
        try:
            # Try One Click Apply first
            easy_apply = await page.query_selector(self.SELECTORS['one_click_apply'])
            if easy_apply and await easy_apply.is_visible():
                await easy_apply.click()
                await page.wait_for_timeout(2000)
                return True

            # Try regular apply button
            apply_btn = await page.query_selector(self.SELECTORS['job_detail_apply'])
            if apply_btn:
                await apply_btn.click()
                await page.wait_for_timeout(2000)

                # Handle resume selection if present
                resume_select = await page.query_selector(self.SELECTORS['resume_selector'])
                if resume_select:
                    # Select first available resume option
                    try:
                        options = await resume_select.query_selector_all('option')
                        if len(options) > 1:
                            await resume_select.select_option(index=1)
                            await page.wait_for_timeout(500)
                    except Exception:
                        pass

                return True

            return False
        except Exception as e:
            logger.error('Error preparing Naukri application: %s', e)
            return False

    async def submit_application(self, page: Page) -> ApplicationResult:
        if DRY_RUN:
            return ApplicationResult(
                success=True,
                status='dry_run',
                message='DRY_RUN mode - application not submitted',
            )

        try:
            submit_selectors = [
                'button:has-text("Apply")',
                'button:has-text("Submit")',
                'button:has-text("Send Application")',
                'button[type="submit"]',
                '.apply-button',
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
            result = await self.detect_application_result(page)
            return result

        except Exception as e:
            return ApplicationResult(
                success=False,
                status='failed',
                message=str(e),
            )

    async def detect_application_result(self, page: Page) -> ApplicationResult:
        # Check for success
        success_selectors = [
            '.applyConfirmation',
            '.successMessage',
            'text=Your application has been submitted',
            'text=Application submitted successfully',
            'text=Applied successfully',
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

        # Check for already applied
        already_selectors = [
            'text=You have already applied',
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

        # Check for errors
        error_selectors = [
            '.error-message',
            '.toast-error',
            '[class*="error"]',
        ]
        for sel in error_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem and await elem.is_visible():
                    err_text = await elem.inner_text()
                    return ApplicationResult(
                        success=False,
                        status='failed',
                        message=f'Error: {err_text}',
                    )
            except Exception:
                continue

        return ApplicationResult(
            success=False,
            status='unknown',
            message='Could not determine application result',
        )


from backend.config import DRY_RUN

naukri_provider = NaukriProvider()
provider_registry.register(naukri_provider)
