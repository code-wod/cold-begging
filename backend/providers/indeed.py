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


class IndeedProvider(JobPortalProvider):
    """Indeed provider with job search and Easy Apply."""

    name = 'indeed'
    platform_name = 'indeed'

    BASE_URL = 'https://www.indeed.com'
    LOGIN_URL = 'https://secure.indeed.com/auth'
    HOME_URL = 'https://www.indeed.com'
    SEARCH_URL = 'https://www.indeed.com/jobs'

    capabilities = PortalCapabilities(
        job_search=True,
        easy_apply=True,
        resume_upload=True,
        cover_letter=True,
        screening_questions=True,
    )

    SELECTORS = {
        'logged_in_indicators': [
            '#gnav-user-link',
            '[data-testid="user-menu"]',
            '.gnav-LoggedOut',
            'a[href*="logout"]',
        ],
        'search_keywords': 'input#text-input-what, input[name="q"], input[placeholder*="Job title"]',
        'search_location': 'input#text-input-where, input[name="l"], input[placeholder*="Location"]',
        'search_button': 'button[type="submit"], button:has-text("Find jobs"), button.primary',
        'job_cards': '.job_seen_beacon, .jobsearch-ResultsList > li, [data-testid="jobCard"], .resultContent',
        'job_title': 'h2.jobTitle a, h2 a, [data-testid="jobTitle"] a, .jobTitle > a',
        'job_company': '[data-testid="company-name"], .companyName, .company',
        'job_location': '[data-testid="text-location"], .companyLocation, .location',
        'job_link': 'h2.jobTitle a, h2 a, [data-testid="jobTitle"] a, .jobTitle > a',
        'job_detail_title': 'h1.jobsearch-JobInfoHeader-title, h1[data-testid="jobTitle"], h1',
        'job_detail_company': '[data-testid="inlineHeader-companyName"] a, .jobsearch-InlineHeader-companyName a',
        'job_detail_location': '[data-testid="inlineHeader-companyLocation"], .jobsearch-InlineHeader-companyLocation',
        'job_detail_description': '#jobDescriptionText, .jobsearch-jobDescriptionText, [data-testid="jobDescription"]',
        'apply_button': 'button:has-text("Apply now"), button:has-text("Apply"), a:has-text("Apply now"), #indeedApplyButton',
        'easy_apply_button': 'button:has-text("Apply now"), button:has-text("Quick Apply"), #indeedApplyButton',
        'resume_upload': 'input[type="file"][accept*="pdf"], input[name="resume"]',
        'cover_letter_textarea': 'textarea[name="coverLetter"], textarea[aria-label*="cover letter"]',
        'phone_input': 'input[name="phoneNumber"], input[autocomplete="tel"]',
        'email_input': 'input[name="email"], input[autocomplete="email"]',
        'submitted_confirmation': '.ia-continueButton, text=Application submitted, text=Your application has been submitted',
        'already_applied': 'text=You have already applied, .already-applied',
    }

    async def search_jobs(self, page: Page, config: SearchConfig) -> List[JobCard]:
        try:
            from urllib.parse import urlencode

            params = {
                'q': ' '.join(config.keywords[:3]) if config.keywords else '',
                'l': config.locations[0] if config.locations else '',
            }
            if config.remote:
                params['remotejob'] = '032b3046-06a3-4876-8dfd-474eb5e7ed11'
            if config.job_types:
                type_map = {'full_time': 'fulltime', 'part_time': 'parttime', 'contract': 'contract', 'internship': 'internship'}
                for jt in config.job_types:
                    mapped = type_map.get(jt, jt)
                    params[f'jt={mapped}'] = ''
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
                    logger.debug('Failed to extract Indeed card: %s', e)
                    continue

            return jobs
        except Exception as e:
            logger.error('Error searching Indeed: %s', e)
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
                match = re.search(r'clk\?jk=([a-f0-9]+)', link) or re.search(r'/viewjob\?jk=([a-f0-9]+)', link)
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
            logger.debug('Failed to extract Indeed card: %s', e)
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
        match = re.search(r'jk=([a-f0-9]+)', job_url)
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
                    break

            # Fill resume upload if present
            resume_inputs = await page.query_selector_all(self.SELECTORS['resume_upload'])
            for resume_input in resume_inputs:
                if candidate.resume_files:
                    resume_path = list(candidate.resume_files.values())[0]
                    await resume_input.set_input_files(resume_path)
                    await page.wait_for_timeout(1000)

            # Fill phone
            phone_inputs = await page.query_selector_all(self.SELECTORS['phone_input'])
            for inp in phone_inputs:
                if await inp.is_visible() and candidate.phone:
                    await inp.fill(candidate.phone)

            # Fill email
            email_inputs = await page.query_selector_all(self.SELECTORS['email_input'])
            for inp in email_inputs:
                if await inp.is_visible() and candidate.email:
                    await inp.fill(candidate.email)

            # Fill cover letter if present
            cover_letter = await page.query_selector(self.SELECTORS['cover_letter_textarea'])
            if cover_letter and await cover_letter.is_visible():
                await cover_letter.fill('I am interested in this position and believe my skills are a strong match.')

            return True
        except Exception as e:
            logger.error('Error preparing Indeed application: %s', e)
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
                'button:has-text("Submit application")',
                'button:has-text("Apply now")',
                '#form-submit-button',
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
            'text=Your application has been submitted',
            'text=Application complete',
            '.ia-continueButton',
            '.jobsearch-ApplyJobResultContent',
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
            'text=You have already applied',
            'text=Already applied',
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

        error_selectors = [
            '.ia-ErrorDisplay',
            '.error',
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


indeed_provider = IndeedProvider()
provider_registry.register(indeed_provider)
