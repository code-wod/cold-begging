from typing import List, Optional
from playwright.async_api import Page
import re
import asyncio

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


class HiristProvider(JobPortalProvider):
    """Hirist provider with job search and application capabilities."""
    
    name = 'hirist'
    platform_name = 'hirist'
    
    BASE_URL = 'https://www.hirist.com'
    LOGIN_URL = 'https://www.hirist.com/login'
    HOME_URL = 'https://www.hirist.com/candidate/dashboard'
    SEARCH_URL = 'https://www.hirist.com/jobs'
    
    capabilities = PortalCapabilities(
        job_search=True,
        easy_apply=True,
    )
    
    SELECTORS = {
        'logged_in_indicators': [
            '.user-profile',
            '.candidate-dashboard',
        ],
        'search_keywords': 'input[placeholder*="Skills"], input[name="keyword"]',
        'search_location': 'input[placeholder*="Location"], input[name="location"]',
        'search_button': 'button[type="submit"], button:has-text("Search")',
        'job_cards': '.job-card, .job-listing, .job-item, [class*="job-card"]',
        'job_title': 'h2 a, h3 a, .job-title a, .title a',
        'job_company': '.company-name, .company a, .company-name a',
        'job_location': '.location, .job-location, [class*="location"]',
        'job_link': 'h2 a, h3 a, .job-title a, .title a',
        'apply_button': 'button:has-text("Apply"), a:has-text("Apply"), button:has-text("Apply Now")',
        'easy_apply_button': 'button:has-text("Easy Apply"), button:has-text("Quick Apply")',
    }
    
    def __init__(self):
        super().__init__()
        self._question_handlers = {
            'phone': self._handle_phone,
            'email': self._handle_email,
            'linkedin': self._handle_linkedin,
            'github': self._handle_github,
            'portfolio': self._handle_portfolio,
            'years': self._handle_years_experience,
            'experience': self._handle_years_experience,
            'salary': self._handle_salary,
            'notice': self._handle_notice_period,
            'relocat': self._handle_relocation,
            'visa': self._handle_visa,
            'authoriz': self._handle_visa,
            'sponsor': self._handle_visa,
            'gender': self._handle_demographics,
            'race': self._handle_demographics,
            'veteran': self._handle_demographics,
            'disabilit': self._handle_demographics,
        }
    
    async def search_jobs(self, page: Page, config: SearchConfig) -> List[JobCard]:
        """Search for jobs on Hirist."""
        try:
            # Build search URL
            from urllib.parse import urlencode, quote
            
            keywords = ' '.join(config.keywords[:3]) if config.keywords else ''
            location = config.locations[0] if config.locations else ''
            
            params = {
                'keyword': keywords,
                'location': location,
            }
            params = {k: v for k, v in params.items() if v}
            
            from urllib.parse import urlencode
            search_url = f'{self.SEARCH_URL}?{urlencode(params)}'
            
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Wait for job listings to load
            try:
                await page.wait_for_selector(self.SELECTORS['job_cards'], timeout=15000)
            except Exception:
                # Try alternative selectors
                await page.wait_for_timeout(5000)
            
            # Scroll to load more jobs
            for _ in range(3):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(1500)
            
            # Extract job cards
            cards = await page.query_selector_all(self.SELECTORS['job_cards'])
            jobs = []
            
            for card in cards[:config.max_results]:
                try:
                    job = await self.extract_job_card(page, card)
                    if job:
                        jobs.append(job)
                except Exception:
                    continue
            
            return jobs
            
        except Exception as e:
            print(f"Error searching jobs on Hirist: {e}")
            return []
    
    async def extract_job_card(self, page: Page, card_element) -> Optional[JobCard]:
        """Extract job info from a search result card."""
        try:
            # Get title and link
            title_elem = await card_element.query_selector(self.SELECTORS['job_title'])
            if not title_elem:
                return None
            
            title = await title_elem.inner_text()
            link = await title_elem.get_attribute('href')
            if link and not link.startswith('http'):
                link = f'{self.BASE_URL}{link}'
            
            # Get company
            company_elem = await card_element.query_selector(self.SELECTORS['job_company'])
            company = await company_elem.inner_text() if company_elem else ''
            
            # Get location
            location_elem = await card_element.query_selector(self.SELECTORS['job_location'])
            location = await location_elem.inner_text() if location_elem else ''
            
            # Get external ID
            external_id = ''
            if link:
                import re
                match = re.search(r'/job/(\d+)', link)
                if match:
                    external_id = match.group(1)
                else:
                    external_id = link
            
            return JobCard(
                external_id=external_id or link or '',
                title=title.strip(),
                company=company.strip(),
                location=location.strip(),
                url=link,
            )
        except Exception:
            return None
    
    async def extract_job_detail(self, page: Page, job_url: str) -> JobDetail:
        """Extract full job details from a job page."""
        await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)
        
        # Extract basic info
        title = ''
        company = ''
        location = ''
        description = ''
        requirements = ''
        skills = []
        salary_min = None
        salary_max = None
        job_type = None
        experience_level = None
        remote_type = None
        
        # Try to extract title
        title_selectors = ['h1', 'h1.job-title', '.job-title', '.job-header h1']
        for sel in ['h1', '.job-title', 'h1.job-title']:
            elem = await page.query_selector(sel)
            if elem:
                title = await elem.inner_text()
                break
        
        # Try to extract company
        company_selectors = ['.company-name', '.company a', '[class*="company"]']
        for sel in company_selectors:
            elem = await page.query_selector(sel)
            if elem:
                company = await elem.inner_text()
                break
        
        # Try to extract location
        location_selectors = ['.location', '.job-location', '[class*="location"]']
        for sel in location_selectors:
            elem = await page.query_selector(sel)
            if elem:
                location = await elem.inner_text()
                break
        
        # Try to extract description
        desc_selectors = ['.job-description', '.description', '[class*="description"]', '.job-details']
        for sel in desc_selectors:
            elem = await page.query_selector(sel)
            if elem:
                description = await elem.inner_text()
                break
        
        # Extract skills from description
        if description:
            skill_keywords = [
                'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'Golang', 'React', 'Vue', 'Angular',
                'Node.js', 'Node', 'Express', 'Django', 'Flask', 'FastAPI', 'Spring', 'Spring Boot',
                'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch', 'DynamoDB',
                'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform', 'Ansible',
                'Git', 'CI/CD', 'Jenkins', 'GitHub Actions', 'GitLab CI',
                'GraphQL', 'REST', 'gRPC', 'Kafka', 'RabbitMQ', 'Microservices',
            ]
            desc_lower = description.lower()
            for skill in skill_keywords:
                if skill.lower() in desc_lower:
                    skills.append(skill)
        
        # Extract external ID
        external_id = ''
        import re
        match = re.search(r'/job/(\d+)', job_url)
        if match:
            external_id = match.group(1)
        else:
            external_id = job_url
        
        return JobDetail(
            external_id=external_id,
            title=title.strip(),
            company=company.strip(),
            location=location.strip(),
            description=description.strip(),
            requirements=requirements.strip(),
            skills=skills,
            salary_min=salary_min,
            salary_max=salary_max,
            currency='INR',
            job_type=job_type,
            experience_level=experience_level,
            remote_type=remote_type,
            application_url=job_url,
        )
    
    async def can_apply(self, page: Page, job: JobDetail) -> bool:
        """Check if we can apply to this job."""
        try:
            # Check if easy apply button exists
            apply_btn = await page.query_selector(self.SELECTORS['apply_button'])
            if apply_btn:
                return True
            
            # Check for easy apply button
            easy_apply_btn = await page.query_selector(self.SELECTORS['easy_apply_button'])
            if easy_apply_btn:
                return True
            
            return False
        except Exception:
            return False
    
    async def prepare_application(
        self,
        page: Page,
        job: JobDetail,
        candidate: CandidateProfile
    ) -> bool:
        """Prepare and fill the application form."""
        try:
            # Click apply button
            apply_btn = await page.query_selector(self.SELECTORS['apply_button'])
            if not apply_btn:
                easy_apply_btn = await page.query_selector(self.SELECTORS['easy_apply_button'])
                if easy_apply_btn:
                    await easy_apply_btn.click()
                else:
                    return False
            else:
                await apply_btn.click()
            
            await page.wait_for_timeout(2000)
            
            # Handle modal/popup
            await page.wait_for_timeout(1000)
            
            # Fill form fields
            await self._fill_form_step(page, candidate)
            
            # Upload resume if field present
            resume_inputs = await page.query_selector_all('input[type="file"][accept*="pdf"], input[name="resume"]')
            for resume_input in resume_inputs:
                if candidate.resume_files:
                    resume_path = list(candidate.resume_files.values())[0]
                    await resume_input.set_input_files(resume_path)
            
            return True
            
        except Exception as e:
            print(f"Error preparing application: {e}")
            return False
    
    async def _fill_form_step(self, page: Page, candidate: CandidateProfile):
        """Fill all visible fields in the current form step."""
        try:
            # Upload resume if field present
            resume_inputs = await page.query_selector_all('input[type="file"][accept*="pdf"], input[name="resume"]')
            for resume_input in resume_inputs:
                if candidate.resume_files:
                    resume_path = list(candidate.resume_files.values())[0]
                    await resume_input.set_input_files(resume_path)
            
            # Fill phone
            phone_inputs = await page.query_selector_all('input[name="phone"], input[autocomplete="tel"], input[placeholder*="phone" i]')
            for inp in phone_inputs:
                if await inp.is_visible() and candidate.phone:
                    await inp.fill(candidate.phone)
            
            # Fill email
            email_inputs = await page.query_selector_all('input[name="email"], input[autocomplete="email"]')
            for inp in email_inputs:
                if await inp.is_visible() and candidate.email:
                    await inp.fill(candidate.email)
            
            # Handle screening questions
            question_containers = await page.query_selector_all('div[class*="question"], div[class*="field"], .form-field, .question')
            for container in question_containers:
                await self._handle_question_container(page, container, candidate)
                
        except Exception as e:
            print(f"Error filling form step: {e}")
    
    async def _handle_question_container(self, page: Page, container, candidate: CandidateProfile):
        """Handle a single screening question."""
        try:
            # Get question text
            label_elem = await container.query_selector('label, .question-text, .question-label, [class*="label"]')
            if not label_elem:
                return
            
            question_text = await label_elem.inner_text()
            question_lower = question_text.lower()
            
            # Find input element
            input_elem = await container.query_selector('input, textarea, select')
            if not input_elem:
                return
            
            input_type = await input_elem.get_attribute('type') or ''
            tag_name = await input_elem.evaluate('el => el.tagName.toLowerCase()')
            
            # Match question to handler
            for keyword, handler in self._question_handlers.items():
                if keyword in question_lower:
                    await handler(page, input_elem, container, candidate, question_text)
                    break
        
        except Exception:
            pass
    
    # Question handlers (same as LinkedIn provider)
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
            yes_radio = await container.query_selector('input[type="radio"][value*="yes" i], input[type="radio"][value*="true" i]')
            if yes_radio:
                await yes_radio.check()
    
    async def _handle_visa(self, page, input_elem, container, candidate, question):
        if candidate.work_authorization:
            await input_elem.fill(candidate.work_authorization)
    
    async def _handle_demographics(self, page, input_elem, container, candidate, question):
        pass
    
    async def submit_application(self, page: Page) -> ApplicationResult:
        """Submit the prepared application."""
        from .base import ApplicationResult
        
        from backend.config import DRY_RUN
        
        if DRY_RUN:
            return ApplicationResult(
                success=True,
                status='dry_run',
                message='DRY_RUN mode - application not submitted',
            )
        
        try:
            # Click submit button
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("Submit")',
                'button:has-text("Submit Application")',
                'button:has-text("Apply Now")',
                'input[type="submit"]',
            ]
            
            for selector in ['button:has-text("Submit")', 'button:has-text("Submit Application")', 'button:has-text("Apply Now")', 'button[type="submit"]']:
                try:
                    btn = await page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click()
                        break
                except Exception:
                    continue
            
            await page.wait_for_timeout(3000)
            
            # Check result
            result = await self.detect_application_result(page)
            return result
            
        except Exception as e:
            return ApplicationResult(
                success=False,
                status='failed',
                message=str(e),
            )
    
    async def detect_application_result(self, page: Page) -> ApplicationResult:
        """Detect application submission result."""
        from .base import ApplicationResult
        
        # Check for success confirmation
        success_selectors = [
            '.success-message',
            '.application-submitted',
            '.application-success',
            '.toast-success',
            'text=Application submitted',
            'text=Applied successfully',
            'text=Application received',
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
            'text=Already applied',
            'text=Already applied to this job',
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
        
        # Check for error
        error_selectors = [
            '.error-message',
            '.toast-error',
            '.alert-error',
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
                        message=f'Application error: {err_text}',
                    )
            except Exception:
                continue
        
        # Unknown state
        return ApplicationResult(
            success=False,
            status='unknown',
            message='Could not determine application result',
        )


hirist_provider = HiristProvider()
provider_registry.register(hirist_provider)