import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from backend.config import BROWSER_DATA_DIR, PLAYWRIGHT_HEADLESS

logger = logging.getLogger('browser_manager')


class BrowserManager:
    """Manages Playwright browser instances and contexts."""
    
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._contexts: Dict[str, BrowserContext] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """Initialize Playwright and launch browser."""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            self._playwright = await async_playwright().start()
            
            # Launch Chromium with persistent user data directory support
            # Use channel="chromium" to use system Chrome if available, otherwise bundled
            self._browser = await self._playwright.chromium.launch(
                headless=PLAYWRIGHT_HEADLESS,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
            )
            
            self._initialized = True
            logger.info('BrowserManager initialized (headless=%s)', PLAYWRIGHT_HEADLESS)
    
    async def shutdown(self):
        """Shutdown browser and Playwright."""
        async with self._lock:
            # Close all contexts
            for context_id, context in self._contexts.items():
                try:
                    await context.close()
                    logger.debug('Closed context: %s', context_id)
                except Exception as e:
                    logger.warning('Error closing context %s: %s', context_id, e)
            
            self._contexts.clear()
            
            # Close browser
            if self._browser:
                try:
                    await self._browser.close()
                except Exception as e:
                    logger.warning('Error closing browser: %s', e)
                self._browser = None
            
            # Stop Playwright
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception as e:
                    logger.warning('Error stopping Playwright: %s', e)
                self._playwright = None
            
            self._initialized = False
            logger.info('BrowserManager shutdown complete')
    
    def is_initialized(self) -> bool:
        return self._initialized
    
    @asynccontextmanager
    async def persistent_context(
        self,
        user_id: int,
        platform: str,
        **context_options
    ):
        """
        Create or reuse a persistent browser context for a user/platform.
        
        The context is stored in a user-specific directory to maintain
        login sessions, cookies, and local storage across runs.
        """
        if not self._initialized:
            await self.initialize()
        
        context_id = f'{user_id}:{platform}'
        
        # Check if context already exists
        if context_id in self._contexts:
            context = self._contexts[context_id]
            # Verify context is still valid
            try:
                _ = context.pages
                logger.debug('Reusing existing context: %s', context_id)
                yield context
                return
            except Exception:
                logger.warning('Existing context invalid, creating new: %s', context_id)
                try:
                    await context.close()
                except Exception:
                    pass
                del self._contexts[context_id]
        
        # Create persistent context directory
        user_data_dir = Path(BROWSER_DATA_DIR) / str(user_id) / platform
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Launch persistent context
        context = await self._browser.new_context(
            user_data_dir=str(user_data_dir),
            viewport={'width': 1366, 'height': 768},
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            locale='en-US',
            timezone_id='Asia/Kolkata',
            **context_options
        )
        
        # Add stealth scripts to avoid detection
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """)
        
        self._contexts[context_id] = context
        logger.info('Created persistent context: %s at %s', context_id, user_data_dir)
        
        try:
            yield context
        finally:
            # Don't close context here - keep it persistent
            # Context will be closed on shutdown or explicit cleanup
            pass
    
    @asynccontextmanager
    async def ephemeral_context(self, **context_options):
        """Create a temporary non-persistent context for one-off tasks."""
        if not self._initialized:
            await self.initialize()
        
        context = await self._browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            locale='en-US',
            timezone_id='Asia/Kolkata',
            **context_options
        )
        
        try:
            yield context
        finally:
            await context.close()
    
    async def get_context(self, user_id: int, platform: str) -> Optional[BrowserContext]:
        """Get existing context if available."""
        context_id = f'{user_id}:{platform}'
        return self._contexts.get(context_id)
    
    async def close_context(self, user_id: int, platform: str) -> bool:
        """Close and remove a specific context."""
        context_id = f'{user_id}:{platform}'
        context = self._contexts.pop(context_id, None)
        if context:
            try:
                await context.close()
                logger.info('Closed context: %s', context_id)
                return True
            except Exception as e:
                logger.error('Error closing context %s: %s', context_id, e)
                return False
        return False
    
    async def close_all_user_contexts(self, user_id: int) -> int:
        """Close all contexts for a specific user."""
        closed = 0
        to_remove = [
            cid for cid in self._contexts.keys()
            if cid.startswith(f'{user_id}:')
        ]
        for context_id in to_remove:
            context = self._contexts.pop(context_id, None)
            if context:
                try:
                    await context.close()
                    closed += 1
                except Exception as e:
                    logger.error('Error closing context %s: %s', context_id, e)
        return closed
    
    async def clear_user_data(self, user_id: int, platform: str) -> bool:
        """Clear browser data directory for a user/platform."""
        context_id = f'{user_id}:{platform}'
        await self.close_context(user_id, platform)
        
        user_data_dir = Path(BROWSER_DATA_DIR) / str(user_id) / platform
        if user_data_dir.exists():
            import shutil
            try:
                shutil.rmtree(user_data_dir)
                logger.info('Cleared browser data: %s', user_data_dir)
                return True
            except Exception as e:
                logger.error('Error clearing browser data %s: %s', user_data_dir, e)
                return False
        return True


_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """Get or create the global BrowserManager instance."""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager