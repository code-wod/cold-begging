import React, { useState } from 'react';
import type { FormField, FieldSuggestion, AutofillState } from '../../types';
import { FieldRow } from './FieldRow';

interface Props {
  state: AutofillState;
  fields: FormField[];
  suggestions: FieldSuggestion[];
  loading: boolean;
  error: string | null;
  onExtract: () => void;
  onAutoFill: () => void;
  onUpdateSuggestion: (fieldId: string, value: string) => void;
  onRejectSuggestion: (fieldId: string) => void;
  onSaveAnswer: (question: string, answer: string, scope: string) => void;
  onClickNext: () => void;
}

export function ReviewPanel({
  state,
  fields,
  suggestions,
  loading,
  error,
  onExtract,
  onAutoFill,
  onUpdateSuggestion,
  onRejectSuggestion,
  onSaveAnswer,
  onClickNext,
}: Props) {
  const [filter, setFilter] = useState<'all' | 'auto' | 'review' | 'skipped'>('all');

  const autoFillable = suggestions.filter(s => s.value && !s.requiresReview);
  const needsReview = suggestions.filter(s => s.value && s.requiresReview);
  const skipped = suggestions.filter(s => !s.value);

  const filteredSuggestions = suggestions.filter(s => {
    if (filter === 'auto') return s.value && !s.requiresReview;
    if (filter === 'review') return s.value && s.requiresReview;
    if (filter === 'skipped') return !s.value;
    return true;
  });

  return (
    <div style={styles.container}>
      {/* Action buttons */}
      <div style={styles.actions}>
        {state === 'idle' || state === 'application_detected' ? (
          <button
            onClick={onExtract}
            disabled={loading}
            style={styles.primaryButton}
          >
            {loading ? 'Analyzing...' : 'Extract Fields'}
          </button>
        ) : state === 'ready' || state === 'review_required' ? (
          <>
            <button
              onClick={onAutoFill}
              disabled={loading || autoFillable.length === 0}
              style={styles.primaryButton}
            >
              {loading ? 'Filling...' : `Auto-fill (${autoFillable.length})`}
            </button>
            <button onClick={onClickNext} style={styles.secondaryButton}>
              Next Step →
            </button>
          </>
        ) : state === 'completed' ? (
          <div style={styles.completedMessage}>
            <span style={styles.checkmark}>✓</span>
            <span>Form filled successfully!</span>
            <button onClick={onClickNext} style={styles.secondaryButton}>
              Continue to Next Step →
            </button>
          </div>
        ) : null}
      </div>

      {/* Error */}
      {error && <div style={styles.error}>{error}</div>}

      {/* Stats */}
      {suggestions.length > 0 && (
        <div style={styles.stats}>
          <span style={styles.stat}>
            <span style={{ color: '#28a745' }}>●</span> {autoFillable.length} auto
          </span>
          <span style={styles.stat}>
            <span style={{ color: '#ffc107' }}>●</span> {needsReview.length} review
          </span>
          <span style={styles.stat}>
            <span style={{ color: '#dc3545' }}>●</span> {skipped.length} skipped
          </span>
        </div>
      )}

      {/* Filter tabs */}
      {suggestions.length > 0 && (
        <div style={styles.filterTabs}>
          {(['all', 'auto', 'review', 'skipped'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={filter === f ? styles.activeFilterTab : styles.filterTab}
            >
              {f === 'all' ? 'All' : f === 'auto' ? 'Auto' : f === 'review' ? 'Review' : 'Skipped'}
            </button>
          ))}
        </div>
      )}

      {/* Field list */}
      <div style={styles.fieldList}>
        {filteredSuggestions.length === 0 ? (
          <div style={styles.empty}>
            {state === 'idle'
              ? 'Navigate to a job application and click "Extract Fields"'
              : 'No fields detected on this page'}
          </div>
        ) : (
          filteredSuggestions.map(suggestion => {
            const field = fields.find(f => f.id === suggestion.fieldId);
            if (!field) return null;
            return (
              <FieldRow
                key={suggestion.fieldId}
                field={field}
                suggestion={suggestion}
                onUpdate={onUpdateSuggestion}
                onReject={onRejectSuggestion}
                onSaveAnswer={onSaveAnswer}
              />
            );
          })
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  actions: {
    display: 'flex',
    gap: '8px',
  },
  primaryButton: {
    flex: 1,
    padding: '12px',
    background: '#ff9900',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  secondaryButton: {
    padding: '12px',
    background: 'white',
    color: '#1a1a2e',
    border: '1px solid #ddd',
    borderRadius: '8px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  error: {
    padding: '8px 12px',
    background: '#fee',
    color: '#dc3545',
    borderRadius: '6px',
    fontSize: '12px',
  },
  stats: {
    display: 'flex',
    gap: '12px',
    padding: '8px 0',
  },
  stat: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '12px',
    color: '#666',
  },
  filterTabs: {
    display: 'flex',
    gap: '4px',
    borderBottom: '1px solid #eee',
    paddingBottom: '8px',
  },
  filterTab: {
    padding: '6px 12px',
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    fontSize: '12px',
    color: '#666',
    borderRadius: '4px',
  },
  activeFilterTab: {
    padding: '6px 12px',
    border: 'none',
    background: '#e9ecef',
    cursor: 'pointer',
    fontSize: '12px',
    color: '#1a1a2e',
    borderRadius: '4px',
    fontWeight: 600,
  },
  fieldList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  empty: {
    textAlign: 'center',
    padding: '24px',
    color: '#999',
    fontSize: '13px',
  },
  completedMessage: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '8px',
    padding: '12px',
    background: '#d4edda',
    borderRadius: '8px',
    color: '#155724',
    width: '100%',
  },
  checkmark: {
    fontSize: '24px',
  },
};
