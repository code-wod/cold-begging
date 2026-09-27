import base64
import json
import logging
import os
import re
import smtplib
import time
from email.mime.text import MIMEText

try:
    import anthropic
    HAVE_ANTHROPIC = True
except ImportError:
    HAVE_ANTHROPIC = False

try:
    import openpyxl
    HAVE_OPENPYXL = True
except ImportError:
    HAVE_OPENPYXL = False

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    HAVE_GMAIL_API = True
except ImportError:
    HAVE_GMAIL_API = False

logger = logging.getLogger('cold_email_agent')

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ColdEmailAgent:
    def __init__(
        self,
        excel_path,
        sender_email=None,
        smtp_password=None,
        gmail_credentials=None,
        token_path='token.json',
        rate_limit=2,
        ai_model='claude-3.5',
        tone='professional',
        subject_style='personalized',
        email_length='medium',
        use_company_research=True,
        custom_prompt=None,
        max_tokens=1000,
        ai_provider=None,
        sender_context=None,
    ):
        self.excel_path = excel_path
        self.sender_email = sender_email or os.getenv('SENDER_EMAIL')
        self.smtp_password = smtp_password or os.getenv('GMAIL_APP_PASSWORD')
        self.gmail_credentials = gmail_credentials or os.getenv('GOOGLE_CREDENTIALS_PATH')
        self.token_path = token_path
        self.rate_limit = rate_limit
        self.sent_count = 0
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.anthropic_client = self._init_anthropic()
        self.gmail_service = None
        self.ai_model = ai_model
        self.tone = tone
        self.subject_style = subject_style
        self.email_length = email_length
        self.use_company_research = use_company_research
        self.custom_prompt = custom_prompt
        self.max_tokens = max_tokens
        self.ai_provider = ai_provider
        self.sender_context = sender_context

        if self.gmail_credentials and HAVE_GMAIL_API:
            self.gmail_service = self._init_gmail_api()

    def _init_anthropic(self):
        if not HAVE_ANTHROPIC or not self.anthropic_key:
            return None

        try:
            return anthropic.Client(api_key=self.anthropic_key)
        except Exception as exc:
            logger.warning('Anthropic client unavailable: %s', exc)
            return None

    def _init_gmail_api(self):
        if not HAVE_GMAIL_API:
            logger.warning('Google Gmail API libraries are not installed. Gmail API sending will be disabled.')
            return None

        if not self.gmail_credentials or not os.path.exists(self.gmail_credentials):
            logger.warning('Gmail credentials file not found at %s', self.gmail_credentials)
            return None

        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.gmail_credentials, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_path, 'w', encoding='utf-8') as token_file:
                token_file.write(creds.to_json())

        try:
            return build('gmail', 'v1', credentials=creds)
        except Exception as exc:
            logger.error('Failed to initialize Gmail API client: %s', exc)
            return None

    def read_excel(self):
        if not HAVE_OPENPYXL:
            raise RuntimeError('openpyxl is required to read Excel files. Install with pip install openpyxl')

        workbook = openpyxl.load_workbook(self.excel_path)
        worksheet = workbook.active
        rows = list(worksheet.iter_rows(values_only=True))

        if not rows:
            return []

        headers = [str(cell).strip().lower() if cell else '' for cell in rows[0]]
        required = ['email', 'company name', 'industry', 'company website', 'job role', 'position level']

        for column in required:
            if column not in headers:
                raise ValueError(f'Missing required column: {column}')

        result = []
        for raw_row in rows[1:]:
            row = {headers[i]: raw_row[i] if i < len(raw_row) else None for i in range(len(headers))}
            email = (row.get('email') or '').strip()
            if not email or not EMAIL_REGEX.match(email):
                continue

            result.append({
                'email': email,
                'company_name': str(row.get('company name') or '').strip(),
                'industry': str(row.get('industry') or '').strip(),
                'website': str(row.get('company website') or '').strip(),
                'job_role': str(row.get('job role') or '').strip(),
                'position_level': str(row.get('position level') or '').strip(),
                'linkedin_url': str(row.get('company linkedin url') or '').strip(),
                'employee_count': str(row.get('employee count') or '').strip(),
                'funding_status': str(row.get('funding status') or '').strip(),
                'recent_news': str(row.get('recent news/updates') or '').strip(),
                'contact_person_name': str(row.get('contact person name') or '').strip()
            })

        return result

    def _anthropic_completion(self, prompt, max_tokens=400, model='claude-3.5'):
        if self.ai_provider:
            return self.ai_provider.complete(prompt, model, max_tokens, 0.7)

        if not self.anthropic_client:
            return ''

        try:
            if hasattr(self.anthropic_client, 'responses'):
                response = self.anthropic_client.responses.create(
                    model=model,
                    input=prompt,
                    max_tokens_to_sample=max_tokens
                )
                return response.output[0].contents[0].text

            if hasattr(self.anthropic_client, 'completions'):
                response = self.anthropic_client.completions.create(
                    model=model,
                    prompt=prompt,
                    max_tokens_to_sample=max_tokens
                )
                return getattr(response, 'completion', '')

            if hasattr(self.anthropic_client, 'messages'):
                response = self.anthropic_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[{'role': 'user', 'content': prompt}],
                )
                return response.content[0].text

            return ''
        except Exception as exc:
            logger.warning('Anthropic completion failed: %s', exc)
            return ''

    def research_company(self, company_data):
        if not self.use_company_research or not (self.anthropic_client or self.ai_provider):
            return {
                'company_pain_points': [],
                'growth_stage': 'unknown',
                'target_for_hiring': True,
                'company_culture': 'Innovative and team-oriented',
                'key_keywords': [company_data['industry'], company_data['company_name']]
            }

        prompt = (
            f"Research and provide a brief company profile for:\n"
            f"- Company: {company_data['company_name']}\n"
            f"- Website: {company_data['website']}\n"
            f"- Industry: {company_data['industry']}\n\n"
            f"Provide ONLY JSON format with these fields:\n"
            f"{{\n"
            f"  \"company_pain_points\": [\"issue1\", \"issue2\"],\n"
            f"  \"growth_stage\": \"early/growth/mature\",\n"
            f"  \"target_for_hiring\": true/false,\n"
            f"  \"company_culture\": \"brief description\",\n"
            f"  \"key_keywords\": [\"keyword1\", \"keyword2\"]\n"
            f"}}\n\n"
            f"Be realistic and specific. If you don't know details, make educated guesses based on industry."
        )

        raw = self._anthropic_completion(prompt, max_tokens=500)
        if not raw:
            logger.warning('Empty AI profile response for %s', company_data['company_name'])
            return {
                'company_pain_points': [],
                'growth_stage': 'unknown',
                'target_for_hiring': True,
                'company_culture': '',
                'key_keywords': []
            }

        cleaned = raw.replace('```json', '').replace('```', '').strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning('Failed to parse AI profile JSON, returning defaults for %s', company_data['company_name'])
            return {
                'company_pain_points': [],
                'growth_stage': 'unknown',
                'target_for_hiring': True,
                'company_culture': '',
                'key_keywords': []
            }

    def _parse_email_response(self, raw):
        """Robustly parse SUBJECT:/BODY: from AI response. Returns (subject, body) or (None, None)."""
        if not raw:
            return None, None
        cleaned = raw.replace('```', '').strip()

        # Try case-insensitive split on BODY:
        match = re.search(r'(?:SUBJECT|Subject)\s*:\s*(.+?)(?:\n|$)', cleaned)
        body_match = re.search(r'(?:BODY|Body)\s*:\s*(.*)', cleaned, re.DOTALL)
        if match and body_match:
            subject = match.group(1).strip()
            body = body_match.group(1).strip()
            if subject and body and len(body) > 20:
                return subject, body

        # Fallback: split on first newline — line before is subject, rest is body
        lines = [l.strip() for l in cleaned.split('\n') if l.strip()]
        if len(lines) >= 2:
            subject = lines[0].lstrip('SUBJECT:').lstrip('Subject:').strip().strip('"').strip("'")
            body = '\n'.join(lines[1:]).lstrip('BODY:').lstrip('Body:').strip()
            if subject and body and len(body) > 20:
                return subject, body

        return None, None

    def generate_personalized_email(self, company_data, company_profile):
        tone_map = {
            'professional': 'Professional but conversational — like a real person writing, not a template',
            'conversational': 'Conversational and approachable — write like you are texting a colleague',
            'friendly': 'Friendly and warm — genuine, not salesy',
            'formal': 'Formal and respectful — corporate but not stiff',
        }
        subject_map = {
            'personalized': f'Write a subject line that mentions {company_data["company_name"]} specifically',
            'curiosity': 'Write a curiosity-driven subject line that makes them want to open',
            'benefit': 'Write a subject line that hints at a specific benefit',
        }
        length_map = {
            'short': 'Keep it to 2-3 short paragraphs (under 100 words)',
            'medium': 'Keep it to 3-4 short paragraphs (100-180 words)',
            'long': 'Keep it to 4-5 paragraphs (180-250 words)',
        }

        tone_instruction = tone_map.get(self.tone, tone_map['professional'])
        subject_instruction = subject_map.get(self.subject_style, subject_map['personalized'])
        length_instruction = length_map.get(self.email_length, length_map['medium'])

        sender_block = ''
        if self.sender_context:
            sender_block = (
                f"\nAbout the sender (use these REAL details — do not invent anything):\n"
                f"{self.sender_context}\n"
            )

        custom_block = ''
        if self.custom_prompt:
            custom_block = f"\nAdditional instructions from the user: {self.custom_prompt}\n"

        prompt = (
            f"You are writing a cold outreach email. Write ONLY the email — no explanations, no notes, no commentary.\n\n"
            f"RECIPIENT:\n"
            f"- Company: {company_data['company_name']}\n"
            f"- Role they hire for: {company_data['job_role']}\n"
            f"- Seniority: {company_data['position_level']}\n"
            f"- Contact: {company_data.get('contact_person_name') or 'the hiring manager'}\n"
            f"- Industry: {company_data['industry']}\n\n"
            f"COMPANY CONTEXT:\n"
            f"- Likely pain points: {', '.join(company_profile.get('company_pain_points', ['hiring needs']))}\n"
            f"- Stage: {company_profile.get('growth_stage', 'growth')}\n"
            f"- Culture vibe: {company_profile.get('company_culture', 'fast-paced team')}\n"
            f"{sender_block}"
            f"WRITING RULES:\n"
            f"- Tone: {tone_instruction}\n"
            f"- Length: {length_instruction}\n"
            f"- Subject: {subject_instruction}\n"
            f"- Open with something specific about {company_data['company_name']} (their product, news, or industry move)\n"
            f"- Connect their need to the sender's relevant experience\n"
            f"- CTA: low-friction ask (15-min call, quick chat)\n"
            f"- NEVER use placeholders like [Your Name], [Company], [Role]\n"
            f"- NEVER start with 'I hope this email finds you well' or 'I am writing to'\n"
            f"- Write as if you are a real person who did 2 minutes of research\n"
            f"{custom_block}"
            f"RESPOND IN THIS EXACT FORMAT (nothing else):\n"
            f"SUBJECT: your subject line here\n"
            f"BODY:\n"
            f"your email body here\n"
        )

        # Attempt 1: generate with full context
        raw = self._anthropic_completion(prompt, max_tokens=self.max_tokens, model=self.ai_model) if (self.anthropic_client or self.ai_provider) else ''
        subject, body = self._parse_email_response(raw)

        # Attempt 2: if parsing failed, retry with even stricter format instruction
        if not subject or not body:
            logger.info('Retrying email generation for %s with stricter format', company_data['company_name'])
            retry_prompt = (
                f"Write a cold email. Output ONLY two lines — nothing else:\n"
                f"Line 1: SUBJECT: <subject>\n"
                f"Line 2: BODY: <email body>\n\n"
                f"Company: {company_data['company_name']}\n"
                f"Role: {company_data['job_role']}\n"
                f"Industry: {company_data['industry']}\n"
                f"Contact: {company_data.get('contact_person_name') or 'there'}\n"
                f"Tone: {tone_instruction}\n"
                f"Make it specific to {company_data['company_name']}. No placeholders.\n"
            )
            raw = self._anthropic_completion(retry_prompt, max_tokens=self.max_tokens, model=self.ai_model) if (self.anthropic_client or self.ai_provider) else ''
            subject, body = self._parse_email_response(raw)

        if subject and body:
            return subject, body

        # Last resort: improved fallback (never uses [Your Name])
        logger.warning('All generation attempts failed for %s, using improved fallback', company_data['company_name'])
        contact = company_data.get('contact_person_name') or 'there'
        company = company_data['company_name']
        role = company_data['job_role']
        industry = company_data['industry']
        stage = company_profile.get('growth_stage', 'growth')

        subject = f"{company} + {role} — quick question"
        body = (
            f"Hi {contact},\n\n"
            f"Noticed {company} is building in {industry} — {stage} stage companies like yours "
            f"usually need strong {role} leadership to scale without breaking processes.\n\n"
            f"I have helped similar teams hire faster by aligning the role requirements with "
            f"candidates who have shipped results in comparable environments. Happy to share a "
            f"couple of examples if useful.\n\n"
            f"Would a 15-minute call this week work? No pitch — just want to learn about "
            f"your hiring priorities.\n\n"
            f"Best,\n"
            f"{{sender_name}}"
        )
        return subject, body

    def _build_raw_message(self, recipient_email, subject, body):
        message = MIMEText(body)
        message['to'] = recipient_email
        message['subject'] = subject
        if self.sender_email:
            message['from'] = self.sender_email

        return base64.urlsafe_b64encode(message.as_bytes()).decode()

    def send_email_via_gmail_api(self, recipient_email, subject, body):
        if not self.gmail_service:
            raise RuntimeError('Gmail API client is not initialized')

        raw_message = self._build_raw_message(recipient_email, subject, body)
        try:
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            return True
        except Exception as exc:
            logger.error('Gmail API send failed: %s', exc)
            return False

    def send_email_via_smtp(self, recipient_email, subject, body):
        if not self.sender_email or not self.smtp_password:
            raise RuntimeError('SMTP sender email and app password are required')

        message = MIMEText(body)
        message['From'] = self.sender_email
        message['To'] = recipient_email
        message['Subject'] = subject

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(self.sender_email, self.smtp_password)
                smtp.sendmail(self.sender_email, recipient_email, message.as_string())
            return True
        except Exception as exc:
            logger.error('SMTP send failed for %s: %s', recipient_email, exc)
            return False

    def process_and_send_emails(self, max_emails=None, dry_run=True, use_gmail_api=False, review_queue_path=None):
        email_rows = self.read_excel()
        if max_emails:
            email_rows = email_rows[:max_emails]

        review_queue = []
        for index, row in enumerate(email_rows, start=1):
            logger.info('\n[%d/%d] %s (%s)', index, len(email_rows), row['company_name'], row['email'])
            company_profile = self.research_company(row)
            subject, body = self.generate_personalized_email(row, company_profile)

            if dry_run:
                logger.info('DRY RUN: %s', row['email'])
                logger.info('SUBJECT: %s', subject)
                logger.info('BODY:\n%s', body)
                status = 'dry_run'
            else:
                if use_gmail_api:
                    success = self.send_email_via_gmail_api(row['email'], subject, body)
                else:
                    success = self.send_email_via_smtp(row['email'], subject, body)
                status = 'sent' if success else 'failed'
                if success:
                    self.sent_count += 1

            review_queue.append({
                'email': row['email'],
                'company_name': row['company_name'],
                'subject': subject,
                'body': body,
                'status': status,
                'company_profile': company_profile
            })
            time.sleep(self.rate_limit)

        if review_queue_path:
            with open(review_queue_path, 'w', encoding='utf-8') as handle:
                json.dump(review_queue, handle, indent=2)
            logger.info('Review queue written to %s', review_queue_path)

        logger.info('\nCompleted: %d emails processed, %d messages sent', len(review_queue), self.sent_count)
        return review_queue
