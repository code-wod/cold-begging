"""
Email Verification Service

Provides email verification using:
1. Syntax validation (regex)
2. MX record lookup (DNS)
3. SMTP verification via Go email-verifier API (optional, falls back to UNKNOWN)

Verification results:
- VALID: syntax OK, domain has MX records, SMTP verification succeeds
- INVALID: syntax invalid, domain has no MX records, or SMTP confirms mailbox doesn't exist
- UNKNOWN: SMTP timeout, DNS failure, provider blocking, or verifier unavailable
"""

import datetime as dt
import dns.resolver
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from .config import EMAIL_VERIFIER_URL, EMAIL_VERIFIER_TIMEOUT

logger = logging.getLogger('email_verification')

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Re-verification interval: 30 days
REVERIFY_INTERVAL_DAYS = 30


@dataclass
class VerificationResult:
    status: str  # 'valid', 'invalid', 'unknown'
    reason: str
    smtp_result: Optional[dict] = None


class EmailVerificationService:
    """Service for verifying email addresses."""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=EMAIL_VERIFIER_TIMEOUT)
        return self._client

    def close(self):
        if self._client and not self._client.is_closed:
            self._client.close()

    def verify(self, email: str) -> VerificationResult:
        """
        Verify an email address through multiple checks.

        Returns VerificationResult with status: 'valid', 'invalid', or 'unknown'.
        """
        # Step 1: Syntax validation
        syntax_result = self._check_syntax(email)
        if syntax_result:
            return syntax_result

        # Step 2: MX record validation
        mx_result = self._check_mx_records(email)
        if mx_result:
            return mx_result

        # Step 3: SMTP verification via Go API (optional)
        smtp_result = self._check_smtp(email)
        if smtp_result:
            return smtp_result

        # If Go API unavailable, domain has MX but we can't verify mailbox
        return VerificationResult(
            status='unknown',
            reason='Domain has MX records but SMTP verification not available'
        )

    def _check_syntax(self, email: str) -> Optional[VerificationResult]:
        """Validate email syntax."""
        if not email or not isinstance(email, str):
            return VerificationResult(status='invalid', reason='Empty or invalid email')

        email = email.strip().lower()
        if len(email) > 254:
            return VerificationResult(status='invalid', reason='Email too long')

        if not EMAIL_REGEX.match(email):
            return VerificationResult(status='invalid', reason='Invalid email syntax')

        return None

    def _check_mx_records(self, email: str) -> Optional[VerificationResult]:
        """Check if the domain has MX records."""
        try:
            domain = email.split('@')[1]
            mx_records = dns.resolver.resolve(domain, 'MX')
            if not mx_records:
                return VerificationResult(status='invalid', reason='Domain has no MX records')
        except dns.resolver.NXDOMAIN:
            return VerificationResult(status='invalid', reason='Domain does not exist')
        except dns.resolver.NoAnswer:
            return VerificationResult(status='invalid', reason='Domain has no MX records')
        except dns.resolver.LifetimeTimeout:
            return VerificationResult(status='unknown', reason='DNS lookup timed out')
        except Exception as e:
            logger.warning(f'DNS lookup failed for {email}: {e}')
            return VerificationResult(status='unknown', reason=f'DNS lookup failed: {str(e)}')

        return None

    def _check_smtp(self, email: str) -> Optional[VerificationResult]:
        """Check email via SMTP using Go email-verifier API."""
        if not EMAIL_VERIFIER_URL:
            return None

        try:
            response = self.client.get(
                f'{EMAIL_VERIFIER_URL}/v1/{email}/verification'
            )
            response.raise_for_status()
            data = response.json()

            reachable = data.get('reachable', 'unknown')
            smtp_data = data.get('smtp')

            if reachable == 'true':
                return VerificationResult(
                    status='valid',
                    reason='SMTP verification successful',
                    smtp_result=data
                )
            elif reachable == 'false':
                reason = 'SMTP verification failed'
                if smtp_data and smtp_data.get('error'):
                    reason = f'SMTP error: {smtp_data["error"]}'
                return VerificationResult(
                    status='invalid',
                    reason=reason,
                    smtp_result=data
                )
            else:
                # reachable == 'unknown'
                reason = 'SMTP verification returned unknown'
                if smtp_data and smtp_data.get('error'):
                    reason = f'SMTP error: {smtp_data["error"]}'
                return VerificationResult(
                    status='unknown',
                    reason=reason,
                    smtp_result=data
                )

        except httpx.TimeoutException:
            logger.warning(f'SMTP verification timed out for {email}')
            return VerificationResult(status='unknown', reason='SMTP verification timed out')
        except httpx.ConnectError as e:
            logger.warning(f'Cannot connect to email verifier: {e}')
            return None  # Service unavailable, don't block
        except Exception as e:
            logger.warning(f'SMTP verification failed for {email}: {e}')
            return VerificationResult(status='unknown', reason=f'SMTP verification error: {str(e)}')

    def should_reverify(self, recipient) -> bool:
        """Check if a recipient should be re-verified."""
        # Never verified
        if not recipient.verified_at:
            return True

        # Was marked unknown - re-verify after 7 days
        if recipient.verification_status == 'unknown':
            days_since = (dt.datetime.now(dt.timezone.utc) - recipient.verified_at).days
            return days_since >= 7

        # Was marked invalid - re-verify after 30 days
        if recipient.verification_status == 'invalid':
            days_since = (dt.datetime.now(dt.timezone.utc) - recipient.verified_at).days
            return days_since >= REVERIFY_INTERVAL_DAYS

        # Valid - re-verify after 30 days
        days_since = (dt.datetime.now(dt.timezone.utc) - recipient.verified_at).days
        return days_since >= REVERIFY_INTERVAL_DAYS

    def persist_result(self, db, recipient, result: VerificationResult):
        """Persist verification result to the recipient record."""
        recipient.verification_status = result.status
        recipient.verification_reason = result.reason
        recipient.verified_at = dt.datetime.now(dt.timezone.utc)
        db.flush()


# Singleton instance
_verification_service = None


def get_verification_service() -> EmailVerificationService:
    """Get or create the singleton verification service."""
    global _verification_service
    if _verification_service is None:
        _verification_service = EmailVerificationService()
    return _verification_service
