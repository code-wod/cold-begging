import argparse
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

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('cold_email_agent')

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ColdEmailAgent:
    def __init__(self, excel_path, sender_email=None, smtp_password=None, gmail_credentials=None, token_path='token.json', rate_limit=2):
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
        if not self.anthropic_client:
            return ''

        try:
            if hasattr(self.anthropic_client, 'responses'):
                response = self.anthropic_client.responses.create(
                    model=model,
                    input=prompt,
                    max_tokens_to_sample=max_tokens
                )
                content = response.output[0].contents[0].text
                return content

            if hasattr(self.anthropic_client, 'completions'):
                response = self.anthropic_client.completions.create(
                    model=model,
                    prompt=prompt,
                    max_tokens_to_sample=max_tokens
                )
                return getattr(response, 'completion', '')

            return ''
        except Exception as exc:
            logger.warning('Anthropic completion failed: %s', exc)
            return ''

    def research_company(self, company_data):
        if not self.anthropic_client:
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

    def generate_personalized_email(self, company_data, company_profile):
        prompt = (
            f"Write a personalized cold email for a job opportunity. Requirements:\n\n"
            f"Recipient Context:\n"
            f"- Company: {company_data['company_name']}\n"
            f"- Recipient Email: {company_data['email']}\n"
            f"- Target Job Role: {company_data['job_role']}\n"
            f"- Position Level: {company_data['position_level']}\n\n"
            f"Company Profile:\n"
            f"- Pain Points: {', '.join(company_profile.get('company_pain_points', []))}\n"
            f"- Growth Stage: {company_profile.get('growth_stage')}\n"
            f"- Culture: {company_profile.get('company_culture')}\n\n"
            f"Email Requirements:\n"
            f"1. Subject line: SHORT, personalized, NOT generic\n"
            f"2. Body: 3-4 short paragraphs max\n"
            f"3. Tone: Professional but conversational (for job opportunity)\n"
            f"4. NEVER mention salary or benefits first\n"
            f"5. Focus on: company achievement, your interest, value proposition\n"
            f"6. CTA: Ask for a brief call/chat (low friction)\n"
            f"7. NO generic templates - MUST be specific to company\n\n"
            f"Format response EXACTLY as:\n"
            f"SUBJECT: [subject line]\n"
            f"BODY:\n"
            f"[email body]\n\n"
            f"If you have optional details such as recent news or funding status, include them naturally."
        )

        raw = self._anthropic_completion(prompt, max_tokens=500) if self.anthropic_client else ''
        if raw:
            raw = raw.replace('```', '').strip()
            parts = raw.split('BODY:')
            subject = parts[0].replace('SUBJECT:', '').strip()
            body = parts[1].strip() if len(parts) > 1 else ''
            if subject and body:
                return subject, body

        logger.info('Using built-in fallback email template for %s', company_data['company_name'])
        subject = f"Quick chat about {company_data['company_name']} and {company_data['job_role']}"
        body = (
            f"Hi {company_data.get('contact_person_name') or 'there'},\n\n"
            f"I saw the work {company_data['company_name']} is doing in {company_data['industry']} and wanted to share a quick note. "
            f"With your focus on {company_profile.get('growth_stage', 'growth')} stage challenges, I believe there is a strong fit for the {company_data['job_role']} role at the {company_data['position_level']} level.\n\n"
            f"I bring experience helping teams improve hiring velocity, align strategic goals, and land the right leadership for fast-moving companies. I would love to learn more about your current talent priorities and explore a brief call.\n\n"
            f"Would you be open to a 15-minute conversation this week?\n\n"
            f"Best regards,\n"
            f"[Your Name]"
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


def parse_args():
    parser = argparse.ArgumentParser(description='Cold Email Automation for Job Outreach')
    parser.add_argument('--excel', '-e', required=True, help='Path to the Excel file')
    parser.add_argument('--sender-email', help='Sender email address')
    parser.add_argument('--smtp-password', help='Gmail app password for SMTP')
    parser.add_argument('--gmail-credentials', help='Google OAuth credentials JSON file for Gmail API')
    parser.add_argument('--token-path', default='token.json', help='Path to store Gmail API token')
    parser.add_argument('--max-emails', type=int, default=None, help='Maximum number of emails to process')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Generate emails without sending')
    parser.add_argument('--send', action='store_true', help='Actually send the emails')
    parser.add_argument('--use-gmail-api', action='store_true', help='Use Gmail API instead of SMTP')
    parser.add_argument('--rate-limit', type=float, default=2.0, help='Seconds to wait between messages')
    parser.add_argument('--review-queue', default='review_queue.json', help='Write generated emails to JSON review queue')
    return parser.parse_args()


def main():
    args = parse_args()
    agent = ColdEmailAgent(
        excel_path=args.excel,
        sender_email=args.sender_email,
        smtp_password=args.smtp_password,
        gmail_credentials=args.gmail_credentials,
        token_path=args.token_path,
        rate_limit=args.rate_limit
    )

    if args.send and not args.dry_run:
        logger.info('Sending emails with %s', 'Gmail API' if args.use_gmail_api else 'SMTP')
        agent.process_and_send_emails(
            max_emails=args.max_emails,
            dry_run=False,
            use_gmail_api=args.use_gmail_api,
            review_queue_path=args.review_queue
        )
    else:
        logger.info('Dry run only. No emails will be sent.')
        agent.process_and_send_emails(
            max_emails=args.max_emails,
            dry_run=True,
            use_gmail_api=args.use_gmail_api,
            review_queue_path=args.review_queue
        )


if __name__ == '__main__':
    main()
