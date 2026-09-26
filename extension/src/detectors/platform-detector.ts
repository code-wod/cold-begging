import type { Platform } from '../types';

interface PlatformPattern {
  platform: Platform;
  urlPatterns: RegExp[];
  domPatterns: string[];
  confidence: number;
}

const PLATFORMS: PlatformPattern[] = [
  {
    platform: 'greenhouse',
    urlPatterns: [
      /boards\.greenhouse\.io/i,
      /jobs\.greenhouse\.io/i,
      /greenhouse\.io\/.*\/jobs/i,
    ],
    domPatterns: [
      '.application-form',
      '#application-form',
      '[data-controller="application"]',
      '.gh-app',
      '.greenhouse-job-board',
    ],
    confidence: 0.95,
  },
  {
    platform: 'workday',
    urlPatterns: [
      /myworkdayjobs\.com/i,
      /workday\.com\/.*\/jobs/i,
      /wd5\.myworkday\.com/i,
      /wday\.com/i,
    ],
    domPatterns: [
      '[data-automation-id]',
      '.WGAG',
      '[class*="WAP"]',
      '[class*="css-"]',
      '.job-application-form',
    ],
    confidence: 0.9,
  },
  {
    platform: 'lever',
    urlPatterns: [
      /jobs\.lever\.co/i,
      /lever\.co\/.*\/apply/i,
    ],
    domPatterns: [
      '.application-form',
      '#application-form',
      '[data-qa]',
      '.postings-wrapper',
    ],
    confidence: 0.95,
  },
  {
    platform: 'ashby',
    urlPatterns: [
      /jobs\.ashbyhq\.com/i,
      /ashbyhq\.com/i,
    ],
    domPatterns: [
      '[class*="ashby"]',
      '.application-form',
      '[data-testid]',
    ],
    confidence: 0.9,
  },
  {
    platform: 'smartrecruiters',
    urlPatterns: [
      /careers\.smartrecruiters\.com/i,
      /smartrecruiters\.com/i,
    ],
    domPatterns: [
      '.application-form',
      '[data-smartapply]',
      '.sr-application',
    ],
    confidence: 0.9,
  },
];

export function detectPlatform(url: string): Platform {
  for (const p of PLATFORMS) {
    for (const pattern of p.urlPatterns) {
      if (pattern.test(url)) return p.platform;
    }
  }
  return 'generic';
}

export function detectPlatformFromDOM(doc: Document): { platform: Platform; confidence: number } {
  const html = doc.documentElement.innerHTML;
  const body = doc.body?.className || '';
  const fullContext = html.substring(0, 5000) + ' ' + body;

  for (const p of PLATFORMS) {
    let matchCount = 0;
    for (const selector of p.domPatterns) {
      try {
        if (doc.querySelector(selector) || fullContext.toLowerCase().includes(selector.toLowerCase().replace(/[.\[#\[\]]/g, ''))) {
          matchCount++;
        }
      } catch { /* invalid selector */ }
    }
    if (matchCount > 0) {
      return { platform: p.platform, confidence: Math.min(0.95, p.confidence * (matchCount / p.domPatterns.length)) };
    }
  }
  return { platform: 'generic', confidence: 0.3 };
}

export function isApplicationPage(url: string, doc: Document): { isApplication: boolean; confidence: number; platform: Platform } {
  const urlPlatform = detectPlatform(url);
  const domResult = detectPlatformFromDOM(doc);

  // Check for explicit application indicators in URL
  const appUrlPatterns = [
    /\/apply/i,
    /\/application/i,
    /\/jobs\/.*\/apply/i,
    /\/careers\/.*\/apply/i,
    /\/submit/i,
  ];
  const urlHasApply = appUrlPatterns.some(p => p.test(url));

  // Check for application form in DOM
  const formIndicators = doc.querySelectorAll(
    'form[action*="apply"], form[class*="application"], ' +
    '[data-testid*="application"], [class*="application-form"], ' +
    'input[type="file"][name*="resume"], input[type="file"][name*="cv"]'
  );

  const hasFormIndicators = formIndicators.length > 0;

  // Determine confidence
  let confidence = 0;
  if (urlPlatform !== 'generic') confidence += 0.4;
  if (domResult.platform !== 'generic') confidence += 0.3;
  if (urlHasApply) confidence += 0.2;
  if (hasFormIndicators) confidence += 0.2;

  const platform = domResult.platform !== 'generic' ? domResult.platform : urlPlatform;

  return {
    isApplication: confidence >= 0.4,
    confidence: Math.min(0.99, confidence),
    platform,
  };
}
