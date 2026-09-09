import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from playwright.async_api import Page, BrowserContext

from backend.config import BROWSER_DATA_DIR
from backend.browser.manager import get_browser_manager

logger = logging.getLogger('session_manager')


class SessionStatus(Enum):
    UNKNOWN = 'unknown'
    CONNECTED = 'connected'
    EXPIRED = 'expired'
    LOGIN_REQUIRED = 'login_required'
    ERROR = 'error'


@dataclass
class SessionInfo:
    user_id: int
    platform: str
    status: str
    last_verified: Optional[str] = None
    login_url: Optional[str] = None
    home_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionInfo':
        return cls(**data)


class SessionManager:
    """Manages persistent browser sessions for job portals."""
    
    # Platform configurations
    PLATFORM_CONFIG = {
        'linkedin': {
            'login_url': 'https://www.linkedin.com/login',
            'home_url': 'https://www.linkedin.com/feed',
            'login_selectors': [
                'input#username',
                'input[name="session_key"]',
            ],
            'password_selectors': [
                'input#password',
                'input[name="session_password"]',
            ],
            'logged_in_selectors': [
                '.global-nav',
                '[data-test-global-nav]',
                '.feed-identity-module',
            ],
        },
        'naukri': {
            'login_url': 'https://www.naukri.com/nlogin/login',
            'home_url': 'https://www.naukri.com/mnjuser/homepage',
            'login_selectors': [
                'input#usernameField',
                'input[placeholder="Email ID / Username"]',
            ],
            'password_selectors': [
                'input#passwordField',
                'input[placeholder="Password"]',
                'input[type="password"]',
            ],
            'logged_in_selectors': [
                '.mnj-header',
                '.user-name',
                '#usernameField[disabled]',
            ],
        },
        'wellfound': {
            'login_url': 'https://wellfound.com/login',
            'home_url': 'https://wellfound.com/jobs',
            'login_selectors': [
                'input[name="email"]',
                'input[type="email"]',
            ],
            'password_selectors': [
                'input[name="password"]',
                'input[type="password"]',
            ],
            'logged_in_selectors': [
                '[data-test="user-menu"]',
                '.user-avatar',
            ],
        },
        'hirist': {
            'login_url': 'https://www.hirist.com/login',
            'home_url': 'https://www.hirist.com/candidate/dashboard',
            'login_selectors': [
                'input[name="email"]',
                'input[type="email"]',
            ],
            'password_selectors': [
                'input[name="password"]',
                'input[type="password"]',
            ],
            'logged_in_selectors': [
                '.user-profile',
                '.candidate-dashboard',
            ],
        },
        'instahyre': {
            'login_url': 'https://instahyre.com/login',
            'home_url': 'https://instahyre.com/candidate/dashboard',
            'login_selectors': [
                'input[name="email"]',
                'input[type="email"]',
            ],
            'password_selectors': [
                'input[name="password"]',
                'input[type="password"]',
            ],
            'logged_in_selectors': [
                '.user-menu',
                '.candidate-dashboard',
            ],
        },
    }
    
    def __init__(self):
        self._browser_manager = get_browser_manager()
        self._session_cache: Dict[str, SessionInfo] = {}
        self._lock = asyncio.Lock()
    
    def _get_cache_key(self, user_id: int, platform: str) -> str:
        return f'{user_id}:{platform}'
    
    def _get_session_file(self, user_id: int, platform: str) -> Path:
        return Path(BROWSER_DATA_DIR) / str(user_id) / platform / 'session.json'
    
    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        return self.PLATFORM_CONFIG.get(platform, {})
    
    async def get_session_info(self, user_id: int, platform: str) -> SessionInfo:
        """Get session info from cache or disk."""
        cache_key = self._get_cache_key(user_id, platform)
        
        if cache_key in self._session_cache:
            return self._session_cache[cache_key]
        
        session_file = self._get_session_file(user_id, platform)
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                info = SessionInfo.from_dict(data)
                self._session_cache[cache_key] = info
                return info
            except Exception as e:
                logger.warning('Error loading session file %s: %s', session_file, e)
        
        # Return default unknown session
        return SessionInfo(
            user_id=user_id,
            platform=platform,
            status=SessionStatus.UNKNOWN.value,
            created_at=datetime.now(timezone.utc).isoformat()
        )
    
    async def save_session_info(self, info: SessionInfo):
        """Save session info to disk and cache."""
        info.updated_at = datetime.now(timezone.utc).isoformat()
        if info.created_at is None:
            info.created_at = info.updated_at
        
        cache_key = self._get_cache_key(info.user_id, info.platform)
        self._session_cache[cache_key] = info
        
        session_file = self._get_session_file(info.user_id, info.platform)
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(session_file, 'w') as f:
                json.dump(info.to_dict(), f, indent=2)
        except Exception as e:
            logger.error('Error saving session file %s: %s', session_file, e)
    
    async def verify_session(self, user_id: int, platform: str) -> SessionStatus:
        """Verify if the browser session is still valid by checking login status."""
        config = self.get_platform_config(platform)
        if not config:
            logger.warning('Unknown platform: %s', platform)
            return SessionStatus.ERROR
        
        try:
            async with self._browser_manager.persistent_context(user_id, platform) as context:
                page = await context.new_page()
                
                # Navigate to home page to check login status
                home_url = config.get('home_url')
                if not home_url:
                    logger.warning('No home_url configured for platform: %s', platform)
                    return SessionStatus.ERROR
                
                try:
                    await page.goto(home_url, wait_until='domcontentloaded', timeout=30000)
                except Exception as e:
                    logger.warning('Navigation to home failed for %s: %s', platform, e)
                    return SessionStatus.ERROR
                
                # Wait a bit for page to settle
                await page.wait_for_timeout(2000)
                
                # Check for logged-in indicators
                logged_in_selectors = config.get('logged_in_selectors', [])
                is_logged_in = False
                
                for selector in logged_in_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            is_logged_in = True
                            logger.debug('Found logged-in indicator: %s', selector)
                            break
                    except Exception:
                        continue
                
                # Also check if we were redirected to login page
                current_url = page.url
                login_url = config.get('login_url', '')
                if login_url and login_url in current_url:
                    is_logged_in = False
                
                if is_logged_in:
                    info = SessionInfo(
                        user_id=user_id,
                        platform=platform,
                        status=SessionStatus.CONNECTED.value,
                        last_verified=datetime.now(timezone.utc).isoformat(),
                        login_url=login_url,
                        home_url=home_url,
                    )
                    await self.save_session_info(info)
                    return SessionStatus.CONNECTED
                else:
                    info = SessionInfo(
                        user_id=user_id,
                        platform=platform,
                        status=SessionStatus.LOGIN_REQUIRED.value,
                        login_url=login_url,
                        home_url=home_url,
                    )
                    await self.save_session_info(info)
                    return SessionStatus.LOGIN_REQUIRED
                    
        except Exception as e:
            logger.error('Error verifying session for %s:%s: %s', user_id, platform, e)
            info = SessionInfo(
                user_id=user_id,
                platform=platform,
                status=SessionStatus.ERROR.value,
            )
            await self.save_session_info(info)
            return SessionStatus.ERROR
    async def ensure_login(self, user_id: int, platform: str, headless: bool = False, credentials: Optional[Dict[str, str]] = None) -> bool:
        """
        Ensure user is logged in. Opens browser for manual login if needed.
        
        Returns True if login successful (or already logged in), False otherwise.
        
        Args:
            user_id: User ID
            platform: Platform name (linkedin, naukri, etc.)
            headless: Whether to run browser in headless mode
            credentials: Optional dict with 'email' and 'password' for auto-login
        """
        status = await self.verify_session(user_id, platform)
        
        if status == SessionStatus.CONNECTED:
            logger.info('Session already connected for %s:%s', user_id, platform)
            return True
        
        config = self.get_platform_config(platform)
        login_url = config.get('login_url')
        if not login_url:
            logger.error('No login_url configured for platform: %s', platform)
            return False
        
        logger.info('Login required for %s:%s, opening browser (headless=%s)', user_id, platform, headless)
        
        try:
            # Launch a separate browser for login (non-headless for manual login)
            from playwright.async_api import async_playwright
            
            async with async_playwright() as playwright:
                # Create persistent context for this user/platform (uses launch_persistent_context for persistent storage)
                user_data_dir = Path(BROWSER_DATA_DIR) / str(user_id) / platform
                user_data_dir.mkdir(parents=True, exist_ok=True)
                
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir / 'playwright'),
                    headless=headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                    ],
                    viewport={'width': 1366, 'height': 768},
                    user_agent=(
                        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/120.0.0.0 Safari/537.36'
                    ),
                    locale='en-US',
                    timezone_id='Asia/Kolkata',
                )
                
                # Add stealth scripts
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                page = await context.new_page()
                
                await page.goto(login_url, wait_until='domcontentloaded', timeout=30000)
                
                # Auto-fill credentials if provided
                if credentials and credentials.get('email') and credentials.get('password'):
                    logger.info('Auto-filling login credentials for %s:%s', user_id, platform)
                    try:
                        # Fill email
                        login_selectors = config.get('login_selectors', [])
                        for selector in login_selectors:
                            try:
                                await page.fill(selector, credentials['email'], timeout=5000)
                                logger.info('Filled email using selector: %s', selector)
                                break
                            except Exception:
                                continue
                        
                        # Fill password
                        password_selectors = config.get('password_selectors', [])
                        for selector in password_selectors:
                            try:
                                await page.fill(selector, credentials['password'], timeout=5000)
                                logger.info('Filled password using selector: %s', selector)
                                break
                            except Exception:
                                continue
                        
                        # Submit login form
                        try:
                            # Try to find and click submit button
                            submit_selectors = [
                                'button[type="submit"]',
                                'input[type="submit"]',
                                'button:has-text("Sign in")',
                                'button:has-text("Login")',
                                'button:has-text("Sign In")',
                            ]
                            for selector in submit_selectors:
                                try:
                                    await page.click(selector, timeout=3000)
                                    logger.info('Clicked submit button: %s', selector)
                                    break
                                except Exception:
                                    continue
                        except Exception as e:
                            logger.warning('Error submitting login form: %s', e)
                            # Fall through to manual login
                    except Exception as e:
                        logger.warning('Error auto-filling credentials: %s', e)
                        # Fall through to manual login
                
                # Wait for user to complete login (including CAPTCHA/2FA)
                logged_in_selectors = config.get('logged_in_selectors', [])
                home_url = config.get('home_url', '')
                
                # Wait up to 5 minutes for login
                max_wait = 300000  # 5 minutes
                poll_interval = 3000  # 3 seconds
                elapsed = 0
                
                while elapsed < max_wait:
                    await page.wait_for_timeout(poll_interval)
                    elapsed += poll_interval
                    
                    # Check for logged-in indicators
                    for selector in logged_in_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element and await element.is_visible():
                                logger.info('Login successful for %s:%s', user_id, platform)
                                info = SessionInfo(
                                    user_id=user_id,
                                    platform=platform,
                                    status=SessionStatus.CONNECTED.value,
                                    last_verified=datetime.now(timezone.utc).isoformat(),
                                    login_url=config.get('login_url'),
                                    home_url=config.get('home_url'),
                                )
                                await self.save_session_info(info)
                                await context.close()
                                return True
                        except Exception:
                            continue
                        
                        # Check if redirected to home page
                        if home_url and page.url.startswith(home_url):
                            logger.info('Login successful (redirected to home) for %s:%s', user_id, platform)
                            info = SessionInfo(
                                user_id=user_id,
                                platform=platform,
                                status=SessionStatus.CONNECTED.value,
                                last_verified=datetime.now(timezone.utc).isoformat(),
                                login_url=config.get('login_url'),
                                home_url=config.get('home_url'),
                            )
                            await self.save_session_info(info)
                            await context.close()
                            return True
                    
                    await page.wait_for_timeout(poll_interval)
                    elapsed += poll_interval
                
                logger.warning('Login timeout for %s:%s', user_id, platform)
                await context.close()
                return False
        
        except Exception as e:
            logger.error('Error during login for %s:%s: %s', user_id, platform, e)
            return False

        """Disconnect and clear session for a platform."""
        # Close browser context
        await self._browser_manager.close_context(user_id, platform)
        
        # Clear browser data directory
        await self._browser_manager.clear_user_data(user_id, platform)
        
        # Remove session info
        cache_key = self._get_cache_key(user_id, platform)
        self._session_cache.pop(cache_key, None)
        
        session_file = self._get_session_file(user_id, platform)
        if session_file.exists():
            try:
                session_file.unlink()
            except Exception:
                pass
        
        logger.info('Disconnected %s:%s', user_id, platform)
        return True

        async def get_all_sessions(self, user_id: int) -> List[SessionInfo]:
            """Get all session info for a user."""
        sessions = []
        for platform in self.PLATFORM_CONFIG.keys():
            info = await self.get_session_info(user_id, platform)
            sessions.append(info)
        return sessions

        """
        Open a managed browser page for user interaction.
        Returns the page for the caller to use.
        Caller is responsible for using the page within the context manager.
        """
        config = self.get_platform_config(platform)
        target_url = url or config.get('home_url') or config.get('login_url')
        
        if not target_url:
            raise ValueError(f'No target URL for platform: {platform}')
        
        context = await self._browser_manager.persistent_context(user_id, platform).__aenter__()
        page = await context.new_page()
        await page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
        return page


def get_session_manager() -> SessionManager:
    """Get or create the global SessionManager instance."""
    if not hasattr(get_session_manager, '_instance'):
        get_session_manager._instance = SessionManager()
    return get_session_manager._instance