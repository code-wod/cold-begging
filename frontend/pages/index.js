import { useState } from 'react';

export default function Home() {
  const [file, setFile] = useState(null);
  const [senderEmail, setSenderEmail] = useState('');
  const [smtpPassword, setSmtpPassword] = useState('');
  const [gmailCredentials, setGmailCredentials] = useState('');
  const [maxEmails, setMaxEmails] = useState('10');
  const [rateLimit, setRateLimit] = useState('2.0');
  const [useGmailApi, setUseGmailApi] = useState(false);
  const [sendNow, setSendNow] = useState(false);
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState(null);

  const onSubmit = async (event) => {
    event.preventDefault();
    if (!file) {
      setStatus({ type: 'error', message: 'Please choose an Excel file.' });
      return;
    }

    const formData = new FormData();
    formData.append('excel_file', file);
    formData.append('sender_email', senderEmail);
    formData.append('smtp_password', smtpPassword);
    formData.append('gmail_credentials', gmailCredentials);
    formData.append('max_emails', maxEmails);
    formData.append('rate_limit', rateLimit);
    formData.append('use_gmail_api', useGmailApi ? 'true' : 'false');
    formData.append('send_now', sendNow ? 'true' : 'false');

    setStatus({ type: 'info', message: 'Uploading and processing…' });
    setResults(null);

    try {
      const response = await fetch('http://localhost:8000/process', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail || 'Processing failed');
      }

      const data = await response.json();
      setStatus({ type: 'success', message: 'Completed successfully.' });
      setResults(data);
    } catch (error) {
      setStatus({ type: 'error', message: error.message });
    }
  };

  return (
    <main style={{ fontFamily: 'Arial, sans-serif', padding: '2rem', background: '#f5f7fb', minHeight: '100vh' }}>
      <div style={{ maxWidth: 900, margin: '0 auto', background: '#fff', padding: '2rem', borderRadius: 16, boxShadow: '0 18px 32px rgba(0,0,0,0.08)' }}>
        <h1>Cold Email Automation</h1>
        <p>Upload an Excel sheet and generate outreach emails with optional send behavior.</p>

        {status && (
          <div style={{ marginBottom: '1rem', padding: '1rem', borderRadius: 10, background: status.type === 'error' ? '#ffe8e6' : '#e8f5e9', color: status.type === 'error' ? '#ba1b1b' : '#095c22' }}>
            {status.message}
          </div>
        )}

        <form onSubmit={onSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label>Excel file (.xlsx)</label>
            <input type="file" accept=".xlsx" onChange={(e) => setFile(e.target.files[0])} required />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label>Sender email</label>
              <input style={{ width: '100%', padding: '0.75rem', marginTop: '0.5rem' }} value={senderEmail} onChange={(e) => setSenderEmail(e.target.value)} placeholder="you@gmail.com" />
            </div>
            <div>
              <label>Gmail app password</label>
              <input style={{ width: '100%', padding: '0.75rem', marginTop: '0.5rem' }} type="password" value={smtpPassword} onChange={(e) => setSmtpPassword(e.target.value)} placeholder="App password" />
            </div>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label>Gmail credentials JSON path (optional for Gmail API)</label>
            <input style={{ width: '100%', padding: '0.75rem', marginTop: '0.5rem' }} value={gmailCredentials} onChange={(e) => setGmailCredentials(e.target.value)} placeholder="backend credentials path" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label>Max emails</label>
              <input type="number" style={{ width: '100%', padding: '0.75rem', marginTop: '0.5rem' }} min="1" value={maxEmails} onChange={(e) => setMaxEmails(e.target.value)} />
            </div>
            <div>
              <label>Rate limit (seconds)</label>
              <input type="number" style={{ width: '100%', padding: '0.75rem', marginTop: '0.5rem' }} min="0" step="0.5" value={rateLimit} onChange={(e) => setRateLimit(e.target.value)} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
            <label><input type="checkbox" checked={useGmailApi} onChange={(e) => setUseGmailApi(e.target.checked)} /> Use Gmail API</label>
            <label><input type="checkbox" checked={sendNow} onChange={(e) => setSendNow(e.target.checked)} /> Send now</label>
          </div>

          <button type="submit" style={{ padding: '0.9rem 1.5rem', borderRadius: 10, background: '#0070f3', color: '#fff', border: 'none', cursor: 'pointer' }}>Submit</button>
        </form>

        {results && (
          <section style={{ marginTop: '2rem' }}>
            <h2>Results</h2>
            <p>{results.results.length} rows processed</p>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f1f5f9' }}>
                  <th style={{ padding: '0.75rem', border: '1px solid #e2e8f0' }}>#</th>
                  <th style={{ padding: '0.75rem', border: '1px solid #e2e8f0' }}>Email</th>
                  <th style={{ padding: '0.75rem', border: '1px solid #e2e8f0' }}>Company</th>
                  <th style={{ padding: '0.75rem', border: '1px solid #e2e8f0' }}>Status</th>
                  <th style={{ padding: '0.75rem', border: '1px solid #e2e8f0' }}>Subject</th>
                </tr>
              </thead>
              <tbody>
                {results.results.map((row, index) => (
                  <tr key={`${row.email}-${index}`} style={{ background: index % 2 ? '#fff' : '#f8fbff' }}>
                    <td style={{ padding: '0.75rem', border: '1px solid #e2e8f0' }}>{index + 1}</td>
                    <td style={{ padding: '0.75rem', border: '1px solid #e2e8f0' }}>{row.email}</td>
                    <td style={{ padding: '0.75rem', border: '1px solid #e2e8f0' }}>{row.company_name}</td>
                    <td style={{ padding: '0.75rem', border: '1px solid #e2e8f0' }}>{row.status}</td>
                    <td style={{ padding: '0.75rem', border: '1px solid #e2e8f0' }}>{row.subject}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </div>
    </main>
  );
}
