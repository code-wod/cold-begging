import React, { useState } from 'react';
import type { FormField, FieldSuggestion } from '../../types';

interface Props {
  field: FormField;
  suggestion: FieldSuggestion;
  onUpdate: (fieldId: string, value: string) => void;
  onReject: (fieldId: string) => void;
  onSaveAnswer: (question: string, answer: string, scope: string) => void;
}

export function FieldRow({ field, suggestion, onUpdate, onReject, onSaveAnswer }: Props) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(suggestion.value || '');
  const [showSaveAnswer, setShowSaveAnswer] = useState(false);
  const [saveScope, setSaveScope] = useState('global');

  const hasValue = !!suggestion.value;
  const confidence = suggestion.confidence;
  const confidenceColor = confidence >= 0.9 ? '#28a745' : confidence >= 0.7 ? '#ffc107' : '#dc3545';

  function handleSave() {
    onUpdate(field.id, editValue);
    setEditing(false);

    // Also save as learned answer if it's a question-type field
    if (field.label && editValue) {
      onSaveAnswer(field.label, editValue, saveScope);
    }
  }

  function handleReject() {
    onReject(field.id);
    setShowSaveAnswer(false);
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.labelSection}>
          <span style={styles.label}>{field.label || field.name || 'Unknown field'}</span>
          {field.required && <span style={styles.required}>*</span>}
          {field.section && <span style={styles.section}>{field.section}</span>}
        </div>
        <div style={styles.confidenceSection}>
          <span style={{ ...styles.confidenceDot, background: confidenceColor }} />
          <span style={styles.confidenceText}>{Math.round(confidence * 100)}%</span>
          <span style={styles.source}>{suggestion.source}</span>
        </div>
      </div>

      {editing ? (
        <div style={styles.editRow}>
          {field.elementType === 'select' && field.options ? (
            <select
              value={editValue}
              onChange={e => setEditValue(e.target.value)}
              style={styles.select}
            >
              <option value="">Select...</option>
              {field.options.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          ) : (
            <input
              type={field.inputType === 'email' ? 'email' : field.inputType === 'tel' ? 'tel' : 'text'}
              value={editValue}
              onChange={e => setEditValue(e.target.value)}
              style={styles.input}
              autoFocus
            />
          )}
          <button onClick={handleSave} style={styles.saveButton}>✓</button>
          <button onClick={() => setEditing(false)} style={styles.cancelButton}>✗</button>
        </div>
      ) : (
        <div style={styles.valueRow}>
          {hasValue ? (
            <>
              <span style={styles.value}>{suggestion.value}</span>
              <button onClick={() => { setEditing(true); setEditValue(suggestion.value || ''); }} style={styles.editButton}>
                Edit
              </button>
              <button onClick={handleReject} style={styles.rejectButton}>
                Skip
              </button>
            </>
          ) : (
            <span style={styles.skipped}>Skipped</span>
          )}
        </div>
      )}

      {showSaveAnswer && (
        <div style={styles.saveAnswerRow}>
          <span style={styles.saveLabel}>Save as learned answer:</span>
          <select value={saveScope} onChange={e => setSaveScope(e.target.value)} style={styles.scopeSelect}>
            <option value="global">Always</option>
            <option value="company">This company</option>
            <option value="job">This job</option>
          </select>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '10px 12px',
    background: 'white',
    borderRadius: '8px',
    border: '1px solid #eee',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
  },
  labelSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flex: 1,
    minWidth: 0,
  },
  label: {
    fontSize: '13px',
    fontWeight: 500,
    color: '#333',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  required: {
    color: '#dc3545',
    fontSize: '12px',
  },
  section: {
    fontSize: '10px',
    color: '#999',
    padding: '1px 4px',
    background: '#f0f0f0',
    borderRadius: '3px',
  },
  confidenceSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    flexShrink: 0,
  },
  confidenceDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
  },
  confidenceText: {
    fontSize: '10px',
    color: '#666',
  },
  source: {
    fontSize: '9px',
    color: '#999',
    textTransform: 'uppercase',
  },
  valueRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  value: {
    fontSize: '13px',
    color: '#1a1a2e',
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  skipped: {
    fontSize: '12px',
    color: '#999',
    fontStyle: 'italic',
  },
  editButton: {
    padding: '2px 8px',
    border: '1px solid #ddd',
    background: 'white',
    borderRadius: '4px',
    fontSize: '11px',
    cursor: 'pointer',
  },
  rejectButton: {
    padding: '2px 8px',
    border: '1px solid #eee',
    background: '#f8f9fa',
    borderRadius: '4px',
    fontSize: '11px',
    cursor: 'pointer',
    color: '#666',
  },
  editRow: {
    display: 'flex',
    gap: '6px',
    alignItems: 'center',
  },
  input: {
    flex: 1,
    padding: '6px 10px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '13px',
    outline: 'none',
  },
  select: {
    flex: 1,
    padding: '6px 10px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '13px',
    outline: 'none',
    background: 'white',
  },
  saveButton: {
    padding: '4px 8px',
    background: '#28a745',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  cancelButton: {
    padding: '4px 8px',
    background: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  saveAnswerRow: {
    marginTop: '6px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  saveLabel: {
    fontSize: '11px',
    color: '#666',
  },
  scopeSelect: {
    fontSize: '11px',
    padding: '2px 4px',
    border: '1px solid #ddd',
    borderRadius: '4px',
  },
};
