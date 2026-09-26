import React from 'react';
import type { AutofillState, Platform } from '../../types';

interface Props {
  state: AutofillState;
  platform: Platform;
}

const STATE_CONFIG: Record<AutofillState, { label: string; color: string; icon: string }> = {
  idle: { label: 'Waiting for application page...', color: '#6c757d', icon: '○' },
  application_detected: { label: 'Application detected!', color: '#28a745', icon: '●' },
  analyzing: { label: 'Analyzing fields...', color: '#007bff', icon: '◎' },
  ready: { label: 'Ready to fill', color: '#28a745', icon: '✓' },
  review_required: { label: 'Review needed', color: '#ffc107', icon: '⚠' },
  filling: { label: 'Filling form...', color: '#007bff', icon: '⟳' },
  completed: { label: 'Form filled!', color: '#28a745', icon: '✓' },
  login_required: { label: 'Login required', color: '#dc3545', icon: '🔒' },
  captcha_required: { label: 'CAPTCHA detected', color: '#dc3545', icon: '🤖' },
  error: { label: 'Error occurred', color: '#dc3545', icon: '✗' },
};

const PLATFORM_LABELS: Record<Platform, string> = {
  greenhouse: 'Greenhouse',
  workday: 'Workday',
  lever: 'Lever',
  ashby: 'Ashby',
  smartrecruiters: 'SmartRecruiters',
  generic: 'Career Page',
  unknown: '',
};

export function StateIndicator({ state, platform }: Props) {
  const config = STATE_CONFIG[state];
  const platformLabel = PLATFORM_LABELS[platform];

  return (
    <div style={styles.container}>
      <span style={{ ...styles.dot, background: config.color }} />
      <span style={styles.label}>{config.label}</span>
      {platformLabel && (
        <span style={styles.platform}>{platformLabel}</span>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginTop: '8px',
  },
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  label: {
    fontSize: '12px',
    opacity: 0.9,
  },
  platform: {
    fontSize: '10px',
    padding: '2px 6px',
    background: 'rgba(255,255,255,0.2)',
    borderRadius: '4px',
    marginLeft: 'auto',
  },
};
