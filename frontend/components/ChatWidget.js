import { useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import { Icons } from './ui';

const SUGGESTIONS = [
  'How do I create a campaign?',
  'How do I connect my Gmail?',
  'Why is my sending speed capped?',
  'How do I stop a campaign?',
];

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, busy]);

  const send = async (text) => {
    const message = (text ?? input).trim();
    if (!message || busy) return;
    const next = [...messages, { role: 'user', content: message }];
    setMessages(next);
    setInput('');
    setError('');
    setBusy(true);
    try {
      const res = await api('/api/chat', {
        method: 'POST',
        body: { message, history: messages },
      });
      setMessages([...next, { role: 'assistant', content: res.reply }]);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button className="chat-fab" onClick={() => setOpen(!open)} title="Help">
        {open ? Icons.x : Icons.agents}
      </button>
      {open && (
        <div className="chat-widget">
          <div className="chat-head">
            <b>PulseBoard Assistant</b>
            <span className="muted" style={{ fontSize: 11 }}>Ask how to use the app</span>
          </div>
          <div className="chat-body" ref={listRef}>
            {messages.length === 0 && (
              <div className="chat-welcome">
                <p className="muted">Hi! I can help you use PulseBoard — campaigns, email accounts, AI agents, scheduling, and more.</p>
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="chat-suggestion" onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`chat-msg ${m.role === 'user' ? 'user' : 'assistant'}`}>{m.content}</div>
            ))}
            {busy && <div className="chat-msg assistant muted">…</div>}
            {error && <div className="chat-msg assistant error">{error}</div>}
          </div>
          <form
            className="chat-input"
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about using PulseBoard…"
            />
            <button type="submit" disabled={busy || !input.trim()} title="Send">
              {busy ? '…' : Icons.send}
            </button>
          </form>
        </div>
      )}
    </>
  );
}