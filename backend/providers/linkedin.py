import re
import logging
from typing import List, Optional, Dict, Any
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


class LinkedInProvider(JobPortalProvider):
    """LinkedIn Easy Apply provider."""

    name = "linkedin"
    platform_name = "linkedin"

    BASE_URL = "https://www.linkedin.com"
    LOGIN_URL = "https://www.linkedin.com/login"
    HOME_URL = "https://www.linkedin.com/feed"
    SEARCH_URL = "https://www.linkedin.com/jobs/search"

    capabilities = PortalCapabilities(
        job_search=True,
        easy_apply=True,
        multi_step_form=True,
        resume_upload=True,
        cover_letter=True,
        screening_questions=True,
    )

    SELECTORS = {
        "username_input": 'input#username, input[name="session_key"]',
        "password_input": 'input#password, input[name="session_password"]',
        "login_button": 'button[type="submit"], .btn__primary--large',
        "logged_in_indicators": [
            ".global-nav",
            "[data-test-global-nav]",
            ".feed-identity-module",
            ".global-nav__me",
        ],
        "search_keywords": 'input[aria-label="Search by title, skill, or company"]',
        "search_location": 'input[aria-label="City, state, or zip code"]',
        "search_button": 'button[aria-label="Search"]',
        "jobs_list": ".jobs-search-results-list, .scaffold-layout__list",
        "job_cards": ".job-card-container, .jobs-search-results__list-item",
        "job_title": "h3 a, .job-card-list__title a",
        "job_company": ".job-card-container__company-name, .artdeco-entity-lockup__subtitle",
        "job_location": ".job-card-container__metadata-item, .artdeco-entity-lockup__caption",
        "job_link": "h3 a, .job-card-list__title a",
        "job_detail_title": "h1.t-24, h1.job-title",
        "job_detail_company": ".job-details-jobs-unified-top-card__company-name a",
        "job_detail_location": ".job-details-jobs-unified-top-card__bullet",
        "job_detail_description": ".jobs-description__content, #job-details",
        "job_detail_apply_button": 'button.jobs-apply-button, button[data-control-name="jobdetails_topcard_inapply"]',
        "job_detail_easy_apply": 'button:has-text("Easy Apply"), button[data-tracking-control-name="public_jobs_topcard_inapply"]',
        "easy_apply_modal": ".jobs-easy-apply-modal, [data-test-modal]",
        "easy_apply_next": 'button[aria-label="Continue to next step"], button:has-text("Next")',
        "easy_apply_review": 'button:has-text("Review"), button[aria-label="Review your application"]',
        "easy_apply_submit": 'button:has-text("Submit application"), button[aria-label="Submit application"]',
        "easy_apply_done": 'button:has-text("Done"), button[aria-label="Done"]',
        "resume_upload": 'input[type="file"][accept*="pdf"], input[name="resume"]',
        "cover_letter_textarea": 'textarea[name="coverLetter"], textarea[aria-label="Cover letter"]',
        "phone_input": 'input[name="phoneNumber"], input[autocomplete="tel"]',
        "email_input": 'input[name="email"], input[autocomplete="email"]',
        "question_container": ".jobs-easy-apply-form-section__grouping",
        "question_label": "label, .fb-dash-form-element__label",
        "question_input": "input, textarea, select",
        "radio_option": 'input[type="radio"]',
        "checkbox_option": 'input[type="checkbox"]',
        "submitted_confirmation": ".jobs-easy-apply-confirmation, [data-test-easy-apply-success]",
        "already_applied": "text=You have already applied",
    }

    def __init__(self):
        super().__init__()
        self._question_handlers = {
            "phone": self._handle_phone,
            "email": self._handle_email,
            "linkedin": self._handle_linkedin,
            "github": self._handle_github,
            "portfolio": self._handle_portfolio,
            "years": self._handle_years_experience,
            "experience": self._handle_years_experience,
            "salary": self._handle_salary,
            "notice": self._handle_notice_period,
            "relocat": self._handle_relocation,
            "visa": self._handle_visa,
            "authoriz": self._handle_visa,
            "sponsor": self._handle_visa,
            "gender": self._handle_demographics,
            "race": self._handle_demographics,
            "veteran": self._handle_demographics,
            "disabilit": self._handle_demographics,
        }

    async def search_jobs(self, page, config):
        from urllib.parse import urlencode

        params = {
            "keywords": " ".join(config.keywords[:3]) if config.keywords else "",
            "location": config.locations[0] if config.locations else "",
            "f_WT": "2" if config.remote else "",
            "sortBy": "DD" if config.sort_by == "date" else "R",
        }
        params = {k: v for k, v in params.items() if v}

        search_url = f"{self.SEARCH_URL}?{urlencode(params)}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        await page.wait_for_selector(self.SELECTORS["jobs_list"], timeout=15000)

        for _ in range(3):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)

        cards = await page.query_selector_all(self.SELECTORS["job_cards"])
        jobs = []

        for card in cards[: config.max_results]:
            try:
                job = await self.extract_job_card(page, card)
                if job:
                    jobs.append(job)
            except Exception:
                continue

        return jobs

    async def extract_job_card(self, page, card_element):
        try:
            title_elem = await card_element.query_selector(self.SELECTORS["job_title"])
            if not title_elem:
                return None

            title = await title_elem.inner_text()
            link = await title_elem.get_attribute("href")
            if link and not link.startswith("http"):
                link = f"https://www.linkedin.com{link}"

            company_elem = await card_element.query_selector(self.SELECTORS["job_company"])
            company = await company_elem.inner_text() if company_elem else ""

            location_elem = await card_element.query_selector(self.SELECTORS["job_location"])
            location = await location_elem.inner_text() if location_elem else ""

            external_id = ""
            if link:
                import re
                match = re.search(r"/jobs/view/(\d+)", link)
                if match:
                    external_id = match.group(1)

            return JobCard(
                external_id=external_id or link or "",
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                url=link,
            )
        except Exception:
            return None

    async def extract_job_detail(self, page, job_url):
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        title = ""
        company = ""
        location = ""
        description = ""

        title_elem = await page.query_selector(self.SELECTORS["job_detail_title"])
        if title_elem:
            title = await title_elem.inner_text()

        company_elem = await page.query_selector(self.SELECTORS["job_detail_company"])
        if company_elem:
            company = await company_elem.inner_text()

        location_elem = await page.query_selector(self.SELECTORS["job_detail_location"])
        if location_elem:
            location = await location_elem.inner_text()

        desc_elem = await page.query_selector(self.SELECTORS["job_detail_description"])
        if desc_elem:
            description = await desc_elem.inner_text()

        external_id = ""
        import re
        match = re.search(r"/jobs/view/(\d+)", job_url)
        if match:
            external_id = match.group(1)

        return JobDetail(
            external_id=external_id,
            title=title.strip(),
            company=company.strip(),
            location=location.strip(),
            description=description.strip(),
            application_url=job_url,
        )

    async def can_apply(self, page, job):
        try:
            apply_btn = await page.query_selector(self.SELECTORS["job_detail_easy_apply"])
            return apply_btn is not None
        except Exception:
            return False

    async def prepare_application(self, page, job, candidate):
        try:
            apply_btn = await page.query_selector(self.SELECTORS["job_detail_easy_apply"])
            if not apply_btn:
                return False

            await apply_btn.click()
            await page.wait_for_timeout(2000)

            await page.wait_for_selector(self.SELECTORS["easy_apply_modal"], timeout=10000)

            max_steps = 10
            for step in range(max_steps):
                await page.wait_for_timeout(1000)

                await self._fill_form_step(page, candidate)

                next_btn = await page.query_selector(self.SELECTORS["easy_apply_next"])
                review_btn = await page.query_selector(self.SELECTORS["easy_apply_review"])
                submit_btn = await page.query_selector(self.SELECTORS["easy_apply_submit"])

                if submit_btn:
                    break
                elif review_btn:
                    await review_btn.click()
                    await page.wait_for_timeout(1000)
                elif next_btn:
                    await next_btn.click()
                    await page.wait_for_timeout(1500)
                else:
                    break

            return True

        except Exception:
            return False

    async def _fill_form_step(self, page, candidate):
        resume_inputs = await page.query_selector_all(self.SELECTORS["resume_upload"])
        for resume_input in resume_inputs:
            if candidate.resume_files:
                resume_path = list(candidate.resume_files.values())[0]
                await resume_input.set_input_files(resume_path)

        phone_inputs = await page.query_selector_all(self.SELECTORS["phone_input"])
        for inp in phone_inputs:
            if await inp.is_visible() and candidate.phone:
                await inp.fill(candidate.phone)

        email_inputs = await page.query_selector_all(self.SELECTORS["email_input"])
        for inp in email_inputs:
            if await inp.is_visible() and candidate.email:
                await inp.fill(candidate.email)

        question_containers = await page.query_selector_all(self.SELECTORS["question_container"])
        for container in question_containers:
            await self._handle_question_container(page, container, candidate)

    async def _handle_question_container(self, page, container, candidate):
        try:
            label_elem = await container.query_selector(self.SELECTORS["question_label"])
            if not label_elem:
                return

            question_text = await label_elem.inner_text()
            question_lower = question_text.lower()

            input_elem = await container.query_selector(self.SELECTORS["question_input"])
            if not input_elem:
                return

            for keyword, handler in self._question_handlers.items():
                if keyword in question_lower:
                    await handler(page, input_elem, container, candidate, question_text)
                    break
            else:
                pass

        except Exception:
            pass

    async def _handle_phone(self, page, input_elem, container, candidate, question):
        if candidate.phone:
            await input_elem.fill(candidate.phone)

    async def _handle_email(self, page, input_elem, container, candidate, question):
        if candidate.email:
            await input_elem.fill(candidate.email)

    async def _handle_linkedin(self, page, input_elem, container, candidate, question):
        if candidate.linkedin_url:
            await input_elem.fill(candidate.linkedin_url)

    async def _handle_github(self, page, input_elem, container, candidate, question):
        if candidate.github_url:
            await input_elem.fill(candidate.github_url)

    async def _handle_portfolio(self, page, input_elem, container, candidate, question):
        if candidate.portfolio_url:
            await input_elem.fill(candidate.portfolio_url)

    async def _handle_years_experience(self, page, input_elem, container, candidate, question):
        if candidate.years_experience:
            await input_elem.fill(str(candidate.years_experience))

    async def _handle_salary(self, page, input_elem, container, candidate, question):
        if candidate.salary_expectation:
            await input_elem.fill(str(candidate.salary_expectation))

    async def _handle_notice_period(self, page, input_elem, container, candidate, question):
        if candidate.notice_period:
            await input_elem.fill(candidate.notice_period)

    async def _handle_relocation(self, page, input_elem, container, candidate, question):
        if candidate.willing_to_relocate:
            yes_radio = await container.query_selector(
                'input[type="radio"][value*="yes" i], input[type="radio"][value*="true" i]'
            )
            if yes_radio:
                await yes_radio.check()

    async def _handle_visa(self, page, input_elem, container, candidate, question):
        if candidate.work_authorization:
            await input_elem.fill(candidate.work_authorization)

    async def _handle_demographics(self, page, input_elem, container, candidate, question):
        pass

    async def submit_application(self, page):
        from backend.config import DRY_RUN

        if DRY_RUN:
            from .base import ApplicationResult
            return ApplicationResult(
                success=True,
                status="dry_run",
                message="DRY_RUN mode - application not submitted",
            )

        try:
            submit_btn = await page.query_selector(self.SELECTORS["easy_apply_submit"])
            if not submit_btn:
                from .base import ApplicationResult
                return ApplicationResult(
                    success=False,
                    status="failed",
                    message="Submit button not found",
                )

            await submit_btn.click()
            await page.wait_for_timeout(3000)

            result = await self.detect_application_result(page)
            return result

        except Exception as e:
            from .base import ApplicationResult
            return ApplicationResult(
                success=False,
                status="failed",
                message=str(e),
            )

    async def detect_application_result(self, page):
        from .base import ApplicationResult

        success_elem = await page.query_selector(self.SELECTORS["submitted_confirmation"])
        if success_elem:
            return ApplicationResult(
                success=True,
                status="submitted",
                message="Application submitted successfully",
            )

        already_elem = await page.query_selector(self.SELECTORS["already_applied"])
        if already_elem:
            return ApplicationResult(
                success=False,
                status="already_applied",
                message="Already applied to this job",
            )

        error_selectors = [
            ".artdeco-toast--error",
            ".jobs-easy-apply-error",
            "[data-test-error]",
        ]
        for sel in error_selectors:
            err_elem = await page.query_selector(sel)
            if err_elem:
                err_text = await err_elem.inner_text()
                return ApplicationResult(
                    success=False,
                    status="failed",
                    message=f"Application error: {err_text}",
                )

        return ApplicationResult(
            success=False,
            status="unknown",
            message="Could not determine application result",
        )


linkedin_provider = LinkedInProvider()
provider_registry.register(linkedin_provider)