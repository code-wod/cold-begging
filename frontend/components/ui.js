import { createContext, useContext, useState } from 'react';

/* ---------- Icons (inline SVG) ---------- */
const P = ({ d, ...rest }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...rest}>
    <path d={d} />
  </svg>
);

export const Icons = {
  dashboard: <P d="M3 3h8v8H3zM13 3h8v5h-8zM13 10h8v11h-8zM3 13h8v8H3z" />,
  campaigns: <P d="M3 5h18M3 12h18M3 19h12M17 19l2 2 3-4" />,
  recipients: <P d="M12 12a4 4 0 100-8 4 4 0 000 8zM4 21v-1a8 8 0 0116 0v1" />,
  agents: <P d="M12 3v3m0 12v3m-6.4-15.6l2.1 2.1M16.3 16.3l2.1 2.1m0-12.4l-2.1 2.1M7.7 16.3l-2.1 2.1M4 12h3m10 0h3M12 9a3 3 0 110 6 3 3 0 010-6z" />,
  email: <P d="M4 5h16a1 1 0 011 1v12a1 1 0 01-1 1H4a1 1 0 01-1-1V6a1 1 0 011-1zM3 7l9 6 9-6" />,
  history: <P d="M3 12a9 9 0 109-9M3 3v6h6M12 7v5l3 2" />,
  analytics: <P d="M4 20V10M10 20V4M16 20v-7M21 20H3" />,
  settings: <P d="M12 8a4 4 0 100 8 4 4 0 000-8zm8.94 4a8 8 0 01-.16 1.88l1.94 1.51-2 3.46-2.29-.92a8 8 0 01-3.28 1.9L14 21h-4l-.15-2.17a8 8 0 01-3.28-1.9l-2.29.92-2-3.46 1.94-1.51A8 8 0 014 12a8 8 0 01.15-1.88L2.2 8.61l2-3.46 2.3.92a8 8 0 013.27-1.9L10 3h4l.15 2.17a8 8 0 013.28 1.9l2.29-.92 2 3.46-1.94 1.51A8 8 0 0120.94 12z" />,
  billing: <P d="M3 5h18v14H3zM3 10h18M6 15h4" />,
  profile: <P d="M12 12a4 4 0 100-8 4 4 0 000 8zm-8 9a8 8 0 0116 0" />,
  logout: <P d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />,
  plus: <P d="M12 5v14M5 12h14" />,
  search: <P d="M11 4a7 7 0 100 14 7 7 0 000-14zm5.5 12.5L21 21" />,
  up: <P d="M12 19V5M5 12l7-7 7 7" />,
  check: <P d="M5 13l4 4L19 7" />,
  x: <P d="M6 6l12 12M18 6L6 18" />,
  duplicate: <P d="M9 9h11v11H9zM5 15H4a1 1 0 01-1-1V4a1 1 0 011-1h10a1 1 0 011 1v1" />,
  play: <P d="M6 4l14 8-14 8z" />,
  pause: <P d="M8 5v14M16 5v14" />,
  refresh: <P d="M20 12a8 8 0 11-2.34-5.66M20 4v6h-6" />,
  send: <P d="M22 2L11 13M22 2l-7 20-4-9-9-4z" />,
  edit: <P d="M4 20h4L18.5 9.5a2.1 2.1 0 00-3-3L5 17zM13.5 6.5l3 3" />,
  trash: <P d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6" />,
  eye: <P d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7zM12 9a3 3 0 110 6 3 3 0 010-6z" />,
  google: (
    <svg width="16" height="16" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M23.5 12.27c0-.85-.08-1.66-.22-2.45H12v4.64h6.45a5.52 5.52 0 01-2.39 3.62v3h3.87c2.26-2.08 3.57-5.15 3.57-8.81z" />
      <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.92l-3.87-3c-1.07.72-2.45 1.14-4.06 1.14-3.12 0-5.77-2.11-6.71-4.95H1.29v3.1A12 12 0 0012 24z" />
      <path fill="#FBBC05" d="M5.29 14.27a7.19 7.19 0 010-4.54v-3.1H1.29a12 12 0 000 10.74z" />
      <path fill="#EA4335" d="M12 4.78c1.76 0 3.34.6 4.59 1.79l3.44-3.44A12 12 0 001.29 6.63l4 3.1C6.23 6.89 8.88 4.78 12 4.78z" />
    </svg>
  ),
};

/* ---------- Toast ---------- */
const ToastContext = createContext(() => {});
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const push = (message, type = 'info') => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, message, type }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  };
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toast-wrap">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* ---------- Form primitives ---------- */
export function Field({ label, help, children, hint }) {
  return (
    <div className="field">
      <label className="label">
        {label}
        {hint && <span className="muted" style={{ fontWeight: 400 }}> — {hint}</span>}
      </label>
      {children}
      {help && <div className="help">{help}</div>}
    </div>
  );
}

export const Input = (props) => <input className="input" {...props} />;
export const Select = ({ options, children, ...props }) => (
  <select className="select" {...props}>
    {options
      ? options.map((o) =>
          typeof o === 'string' ? (
            <option key={o} value={o}>
              {o}
            </option>
          ) : (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          )
        )
      : children}
  </select>
);
export const TextArea = (props) => <textarea className="input" {...props} />;

/* ---------- Surfaces ---------- */
export const Panel = ({ title, actions, children, bodyClassName }) => (
  <div className="panel">
    {(title || actions) && (
      <div className="panel-header">
        <div className="panel-title">{title}</div>
        <div className="flex">{actions}</div>
      </div>
    )}
    <div className={bodyClassName || 'panel-body'}>{children}</div>
  </div>
);

export const Button = ({ variant = 'primary', className = '', ...props }) => (
  <button className={`btn ${variant} ${className}`} {...props} />
);

/* ---------- Status badges ---------- */
const CAMPAIGN_TONES = {
  draft: 'gray', generating: 'blue', review_required: 'amber', scheduled: 'teal',
  running: 'blue', paused: 'orange', completed: 'green', failed: 'red', cancelled: 'gray',
};
const EMAIL_TONES = {
  generated: 'gray', approved: 'teal', scheduled: 'teal', sending: 'blue',
  sent: 'green', failed: 'red', cancelled: 'gray', skipped: 'gray',
};

export function StatusBadge({ status, tone }) {
  const resolved = tone || CAMPAIGN_TONES[status] || EMAIL_TONES[status] || 'gray';
  return <span className={`badge ${resolved}`}>{status.replace('_', ' ')}</span>;
}

/* ---------- Misc ---------- */
export const Spinner = () => <span className="spinner" />;
export const Empty = ({ message }) => <div className="empty">{message}</div>;

export const Progress = ({ percent }) => (
  <div className="progress">
    <div style={{ width: `${Math.max(0, Math.min(100, percent))}%` }} />
  </div>
);

export function Modal({ open, title, children, onClose, footer }) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="justify-between mb-16">
          <h3 style={{ fontSize: 16 }}>{title}</h3>
          <button className="btn ghost sm" onClick={onClose}>
            {Icons.x}
          </button>
        </div>
        {children}
        {footer && <div className="mt-16 flex justify-between">{footer}</div>}
      </div>
    </div>
  );
}

export function Confirm({ open, title = 'Confirm action', message, onCancel, onConfirm, confirmLabel = 'Confirm', danger }) {
  return (
    <Modal open={open} title={title} onClose={onCancel}
      footer={
        <>
          <Button variant="secondary" onClick={onCancel}>Cancel</Button>
          <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm}>{confirmLabel}</Button>
        </>
      }>
      <p className="muted">{message}</p>
    </Modal>
  );
}

const APP_TZ = 'Asia/Kolkata'; // default display timezone for all timestamps

const parseIso = (iso) => {
  const s = String(iso || '');
  if (/[zZ]|[+-]\d{2}:?\d{2}$/.test(s)) return new Date(s);
  return new Date(`${s}Z`); // SQLite stores naive UTC; treat offset-less ISO as UTC
};

export const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return parseIso(iso).toLocaleString(undefined, {
      timeZone: APP_TZ,
      year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
    });
  } catch {
    return iso;
  }
};

export const fmtRel = (iso) => {
  if (!iso) return '—';
  const d = parseIso(iso);
  const days = Math.floor((Date.now() - d.getTime()) / 86400000);
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  return `${days} days ago`;
};