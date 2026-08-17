# Cold Email Automation System - Job Opportunities Focus

## System Architecture

```
Excel Sheet (Email List)
    ↓
Email Validation & Parsing
    ↓
Company Profile Research (AI Agent)
    ↓
Email Personalization (Claude API)
    ↓
Review Queue (Optional Manual Check)
    ↓
Gmail Sending (Rate-Limited)
    ↓
Tracking & Analytics
```

---

## 1. EXCEL SHEET STRUCTURE

**Required Columns:**
```
| Email | Company Name | Industry | Company Website | Job Role | Position Level |
|-------|-------------|----------|-----------------|----------|-----------------|
| john@techstartup.io | TechStartup Inc | SaaS | techstartup.io | Founder | CEO |
| hr@designfirm.com | Design Firm Co | Design | designfirm.co | HR Manager | Manager |
```

**Optional Columns for Personalization:**
- Company LinkedIn URL
- Employee Count
- Funding Status
- Recent News/Updates
- Contact Person Name

---

## 2. CORE IMPLEMENTATION (Python + Node.js)

### Option A: Python with Gmail API + Claude

```python
import os
import base64
import json
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
import anthropic
import openpyxl
import time
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

class ColdEmailAgent:
    def __init__(self, credentials_path, excel_path):
        self.credentials_path = credentials_path
        self.excel_path = excel_path
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.gmail_service = self._init_gmail()
        self.sent_count = 0
        self.rate_limit_delay = 1  # seconds between emails

    def _init_gmail(self):
        """Initialize Gmail API connection"""
        credentials = service_account.Credentials.from_service_account_file(
            self.credentials_path, scopes=SCOPES)

        # If using personal Gmail, use this instead:
        # from google.auth.oauthlib.flow import InstalledAppFlow
        # flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        # creds = flow.run_local_server()

        from googleapiclient.discovery import build
        return build('gmail', 'v1', credentials=credentials)

    def read_excel(self):
        """Read email list from Excel"""
        wb = openpyxl.load_workbook(self.excel_path)
        ws = wb.active

        emails = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0]:  # If email exists
                emails.append({
                    'email': row[0],
                    'company_name': row[1],
                    'industry': row[2],
                    'website': row[3],
                    'job_role': row[4],
                    'position_level': row[5]
                })
        return emails

    def research_company(self, company_data):
        """Use Claude to research company profile"""
        prompt = f"""
        Research and provide a brief company profile for:
        - Company: {company_data['company_name']}
        - Website: {company_data['website']}
        - Industry: {company_data['industry']}

        Provide ONLY JSON format with these fields:
        {{
            "company_pain_points": ["issue1", "issue2"],
            "growth_stage": "early/growth/mature",
            "target_for_hiring": true/false,
            "company_culture": "brief description",
            "key_keywords": ["keyword1", "keyword2"]
        }}

        Be realistic and specific. If you don't know details, make educated guesses based on industry.
        """

        message = self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        try:
            # Extract JSON from response
            response_text = message.content[0].text
            # Remove markdown code blocks if present
            response_text = response_text.replace('```json\n', '').replace('\n```', '').replace('```', '')
            profile = json.loads(response_text)
            return profile
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse profile for {company_data['company_name']}")
            return {
                "company_pain_points": [],
                "growth_stage": "unknown",
                "target_for_hiring": True,
                "company_culture": "",
                "key_keywords": []
            }

    def generate_personalized_email(self, company_data, company_profile):
        """Generate personalized email using Claude"""
        prompt = f"""
        Write a personalized cold email for a job opportunity. Requirements:

        Recipient Context:
        - Company: {company_data['company_name']}
        - Recipient Email: {company_data['email']}
        - Target Job Role: {company_data['job_role']}
        - Position Level: {company_data['position_level']}

        Company Profile:
        - Pain Points: {', '.join(company_profile.get('company_pain_points', []))}
        - Growth Stage: {company_profile.get('growth_stage')}
        - Culture: {company_profile.get('company_culture')}

        Email Requirements:
        1. Subject line: SHORT, personalized, NOT generic
        2. Body: 3-4 short paragraphs max
        3. Tone: Professional but conversational (for job opportunity)
        4. NEVER mention salary or benefits first
        5. Focus on: company achievement, your interest, value proposition
        6. CTA: Ask for a brief call/chat (low friction)
        7. NO generic templates - MUST be specific to company

        Format response EXACTLY as:
        SUBJECT: [subject line]
        BODY:
        [email body]

        Remember: This is for attracting talent TO the company, not job hunting.
        """

        message = self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=400,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text

        # Parse response
        try:
            parts = response_text.split('BODY:')
            subject = parts[0].replace('SUBJECT:', '').strip()
            body = parts[1].strip() if len(parts) > 1 else ""
            return subject, body
        except:
            logger.error(f"Failed to parse email for {company_data['company_name']}")
            return "", ""

    def send_email(self, recipient_email, subject, body, sender_email=None):
        """Send email via Gmail API"""
        message = MIMEText(body)
        message['to'] = recipient_email
        message['subject'] = subject
        if sender_email:
            message['from'] = sender_email

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        try:
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            logger.info(f"✓ Email sent to {recipient_email}")
            self.sent_count += 1
            return True
        except Exception as e:
            logger.error(f"✗ Failed to send to {recipient_email}: {str(e)}")
            return False

    def process_and_send_emails(self, max_emails=None, dry_run=False):
        """Main automation pipeline"""
        emails = self.read_excel()
        if max_emails:
            emails = emails[:max_emails]

        results = []

        for idx, email_data in enumerate(emails, 1):
            logger.info(f"\n[{idx}/{len(emails)}] Processing {email_data['company_name']}")

            # Step 1: Research company
            logger.info("  → Researching company profile...")
            company_profile = self.research_company(email_data)

            # Step 2: Generate email
            logger.info("  → Generating personalized email...")
            subject, body = self.generate_personalized_email(email_data, company_profile)

            if not subject or not body:
                logger.error(f"  ✗ Email generation failed")
                results.append({
                    'email': email_data['email'],
                    'status': 'failed',
                    'reason': 'generation_failed'
                })
                continue

            # Step 3: Send email
            if dry_run:
                logger.info(f"  [DRY RUN] Would send email:")
                logger.info(f"    To: {email_data['email']}")
                logger.info(f"    Subject: {subject}")
                results.append({
                    'email': email_data['email'],
                    'status': 'dry_run',
                    'subject': subject
                })
            else:
                success = self.send_email(email_data['email'], subject, body)
                results.append({
                    'email': email_data['email'],
                    'status': 'sent' if success else 'failed',
                    'subject': subject
                })

            # Rate limiting
            time.sleep(self.rate_limit_delay)

        logger.info(f"\n✓ Completed: {self.sent_count} emails sent")
        return results

# USAGE
if __name__ == "__main__":
    agent = ColdEmailAgent(
        credentials_path='path/to/credentials.json',
        excel_path='cold_email_list.xlsx'
    )

    # Start with dry run first!
    results = agent.process_and_send_emails(dry_run=True)

    # Then send for real
    # results = agent.process_and_send_emails(max_emails=10)
```

---

## 3. NODE.JS ALTERNATIVE (With Web Scraping)

```javascript
const nodemailer = require('nodemailer');
const Anthropic = require('@anthropic-ai/sdk');
const ExcelJS = require('exceljs');
const axios = require('axios');
const cheerio = require('cheerio');

class ColdEmailAgent {
  constructor(gmailConfig) {
    this.client = new Anthropic();
    this.transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: gmailConfig.email,
        pass: gmailConfig.appPassword // Use App Password, not regular password
      }
    });
    this.sentCount = 0;
  }

  async readExcel(filePath) {
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.readFile(filePath);
    const worksheet = workbook.getWorksheet(1);

    const emails = [];
    worksheet.eachRow((row, rowNumber) => {
      if (rowNumber > 1 && row.values[1]) { // Skip header
        emails.push({
          email: row.values[1],
          companyName: row.values[2],
          industry: row.values[3],
          website: row.values[4],
          jobRole: row.values[5],
          positionLevel: row.values[6]
        });
      }
    });
    return emails;
  }

  async scrapeCompanyWebsite(website) {
    try {
      const response = await axios.get(`https://${website}`, { timeout: 5000 });
      const $ = cheerio.load(response.data);

      return {
        description: $('meta[name="description"]').attr('content') || '',
        aboutText: $('section[id*="about"]').text().slice(0, 200) || '',
        hasCareerPage: $('a').text().toLowerCase().includes('careers')
      };
    } catch (error) {
      console.log(`Could not scrape ${website}: ${error.message}`);
      return { description: '', aboutText: '', hasCareerPage: false };
    }
  }

  async generateEmail(emailData, companyInfo) {
    const message = await this.client.messages.create({
      model: "claude-opus-4-6",
      max_tokens: 400,
      messages: [{
        role: "user",
        content: `Create a personalized cold email for a job opportunity:

Company: ${emailData.companyName}
Target Role: ${emailData.jobRole}
Position Level: ${emailData.positionLevel}
Industry: ${emailData.industry}
Company Description: ${companyInfo.description}

Requirements:
- Subject line should be unique and NOT generic
- 3-4 short paragraphs
- Mention something specific about the company
- Clear CTA for a call
- Professional but conversational

Format:
SUBJECT: [subject]
BODY:
[body text]`
      }]
    });

    const text = message.content[0].text;
    const [subjectPart, ...bodyPart] = text.split('BODY:');
    return {
      subject: subjectPart.replace('SUBJECT:', '').trim(),
      body: bodyPart.join('BODY:').trim()
    };
  }

  async sendEmail(to, subject, body) {
    try {
      await this.transporter.sendMail({
        from: this.transporter.options.auth.user,
        to,
        subject,
        html: body.replace(/\n/g, '<br>')
      });
      console.log(`✓ Sent to ${to}`);
      this.sentCount++;
      return true;
    } catch (error) {
      console.error(`✗ Failed to send to ${to}: ${error.message}`);
      return false;
    }
  }

  async run(excelPath, dryRun = true, maxEmails = 50) {
    const emails = await this.readExcel(excelPath);
    const limited = emails.slice(0, maxEmails);

    for (let i = 0; i < limited.length; i++) {
      const emailData = limited[i];
      console.log(`\n[${i + 1}/${limited.length}] Processing ${emailData.companyName}`);

      // Scrape company website
      const companyInfo = await this.scrapeCompanyWebsite(emailData.website);

      // Generate email
      const { subject, body } = await this.generateEmail(emailData, companyInfo);

      if (dryRun) {
        console.log(`SUBJECT: ${subject}`);
        console.log(`TO: ${emailData.email}`);
        console.log(`BODY: ${body.slice(0, 100)}...`);
      } else {
        await this.sendEmail(emailData.email, subject, body);
      }

      // Rate limit
      await new Promise(r => setTimeout(r, 2000));
    }

    console.log(`\n✓ Completed: ${this.sentCount} emails sent`);
  }
}

// USAGE
const agent = new ColdEmailAgent({
  email: 'your-email@gmail.com',
  appPassword: 'your-16-char-app-password' // NOT your regular password!
});

agent.run('emails.xlsx', true, 10); // Dry run first
```

---

## 4. GMAIL SETUP (CRITICAL FOR SUCCESS)

### For Personal Gmail + Google Apps:

**Step 1: Enable 2FA**
- Go to myaccount.google.com → Security
- Enable 2-Step Verification

**Step 2: Create App Password**
```
Settings → Security → App Passwords
Select "Mail" and "Windows/Linux/Mac" (or custom)
Google generates 16-char password → Use this in code, NOT your actual password
```

**Step 3: Enable Gmail API**
```
1. Google Cloud Console (console.cloud.google.com)
2. Create new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Service Account or Desktop App)
5. Download credentials.json
```

**Step 4: Add Sender Email to Gmail**
```
Gmail Settings → Accounts → Send email as...
Add your domain email address
Verify via confirmation email
```

---

## 5. SMART PERSONALIZATION STRATEGIES

### A. Industry-Based Variations
```python
INDUSTRY_TEMPLATES = {
    'SaaS': "I noticed your [specific_product] - interesting approach to [pain_point]",
    'Fintech': "Your approach to [regulatory_challenge] caught my attention",
    'Enterprise': "Scaling [specific_team] is critical for [business_goal]",
}
```

### B. Company Stage Detection
```python
GROWTH_SIGNALS = {
    'recent_funding': "I saw your recent Series X round...",
    'new_product': "Your new feature is solving...",
    'expansion': "Expanding into [market] requires..."
}
```

### C. Job Role-Specific Openings
```python
ROLE_ANGLES = {
    'Engineering': "Scaling your tech stack requires...",
    'Sales': "Your GTM strategy should focus on...",
    'Marketing': "Positioning in your market space...",
    'HR': "Scaling from [X] to [Y] team members..."
}
```

---

## 6. DELIVERABILITY & COMPLIANCE

### Gmail Rate Limits
- **Personal Gmail**: ~500 emails/day max
- **Workspace**: Higher limits, but monitor reputation
- **Recommended**: 10-50/day to stay under radar

### Best Practices
```
✓ Use real company email (not generic@)
✓ Warm-up period: Start with 5-10/day, increase gradually
✓ Monitor bounce rate
✓ Use proper sender authentication (SPF, DKIM, DMARC)
✓ A/B test subject lines
✓ Never use "Re:" or fake reply chains
✓ Include unsubscribe link (legal requirement)
```

### Compliance
```
✓ CAN-SPAM: Include company address + unsubscribe
✓ GDPR: Only email prospects from opt-in lists
✓ Anti-spam: Don't blast identical emails
✓ ToS: Gmail ToS allows business emails, not spam
```

---

## 7. ENHANCEMENTS & EXTENSIONS

### A. Prospect Tracking
```python
class EmailTracker:
    def log_email(self, email, subject, status):
        # Log to: CSV, Database, or Webhook
        # Track: Opens, Clicks, Replies
        pass
```

### B. A/B Testing
```python
SUBJECT_VARIANTS = [
    "Quick question about {company}",
    "{company}: [Specific insight]",
    "FW: Opportunity for your {job_role} team"
]
```

### C. Reply Handling
```python
# Monitor for replies to your sending email
# Auto-mark qualified responses
# Alert you to hot leads
```

### D. Multi-Channel Follow-up
```
Email 1 (Day 1): Initial outreach
Email 2 (Day 3): Light follow-up
Email 3 (Day 7): Value-add (article/insight)
Email 4 (Day 14): Final attempt
LinkedIn: Send connection request on Day 2
```

---

## 8. SETUP CHECKLIST

```
☐ Create credentials.json for Gmail API
☐ Set up app password (not regular password)
☐ Create Excel file with company list
☐ Add test row to verify email format
☐ Run code in DRY_RUN mode first
☐ Check generated emails manually
☐ Start with 10 test emails
☐ Monitor Gmail for bounces
☐ Gradually increase volume (10→20→50)
☐ Track which emails get replies
☐ Adjust templates based on response rate
```

---

## 9. EXPECTED METRICS

- **Delivery Rate**: 95%+ (watch for spam folder)
- **Open Rate**: 15-30% (job opportunities get higher engagement)
- **Reply Rate**: 5-15% (depending on targeting)
- **Positive Responses**: 2-5% will be interested

---

## 10. TROUBLESHOOTING

| Issue | Solution |
|-------|----------|
| "535 5.7.8 Username and password not accepted" | Use app password, not regular password |
| Emails in spam folder | Warm up gradually, vary subject lines, include real company address |
| API rate limit exceeded | Add delay between emails, reduce batch size |
| Claude API errors | Check API key, validate prompt format |
| "Gmail not found" | Ensure 2FA enabled + app password created |

---

## RECOMMENDED TECH STACK

**Production Setup:**
- **Backend**: Python + FastAPI (for API endpoints)
- **Queue**: Celery + Redis (for async processing)
- **Database**: PostgreSQL (track emails, clicks, replies)
- **Monitoring**: Sentry (error tracking)
- **Webhooks**: Zapier or Make (integrate with CRM)
- **Email Tracking**: Mailgun or SendGrid (better analytics)

## server start backend
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# then, from the repo root:
- backend/.venv/bin/uvicorn backend.main:app --port 8000
- The server starts at http://localhost:8000 (health check: curl http://localhost:8000/health). It auto-creates backend/cold_email.db and the SECRET_KEY/FERNET_KEY files on first boot.
