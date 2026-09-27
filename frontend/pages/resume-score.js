import { useState, useEffect, useRef } from 'react';
import Layout from '../components/Layout';
import Link from 'next/link';
import { api, AUTH_URL } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Panel, Spinner, useToast, Icons, Button } from '../components/ui';

export default function ResumeScore() {
  const { user } = useAuth();
  const toast = useToast();
  const fileRef = useRef();
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [usage, setUsage] = useState(null);

  useEffect(() => { fetchUsage(); }, []);

  const fetchUsage = async () => {
    try {
      const data = await api('/api/resume-score/usage');
      setUsage(data);
    } catch (e) {
      console.error('Failed to fetch usage', e);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const data = await api('/api/resume-score', { method: 'POST', body: formData, form: true });
      setResult(data);
      setUsage({ used: (usage?.used || 0) + 1, remaining: data.checks_remaining, plan: data.plan, is_unlimited: data.checks_remaining === -1 });
    } catch (e) {
      if (e.status === 402) {
        toast('Upgrade to check more resumes', 'error');
      } else {
        toast(e.message || 'Failed to score resume', 'error');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    const f = e.target.files?.[0];
    if (f) {
      if (!f.name.toLowerCase().endsWith('.pdf')) {
        toast('Only PDF files are allowed', 'error');
        return;
      }
      setFile(f);
      setResult(null);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#16a34a';
    if (score >= 60) return '#d97706';
    return '#dc2626';
  };

  const getScoreLabel = (score) => {
    if (score >= 90) return 'Excellent';
    if (score >= 75) return 'Good';
    if (score >= 50) return 'Average';
    return 'Needs Work';
  };

  return (
    <Layout title="Resume Score">
      <div className="page-head">
        <div>
          <h1>Resume Score</h1>
          <p className="muted">Upload your resume and get an AI-powered score with improvement tips</p>
        </div>
        {usage && (
          <div className="flex" style={{ gap: 8, alignItems: 'center' }}>
            <span className={`badge ${usage.is_unlimited ? 'green' : usage.remaining > 3 ? 'blue' : 'red'}`}>
              {usage.is_unlimited ? 'Unlimited checks' : `${usage.remaining} checks remaining`}
            </span>
            <span className="badge gray">{usage.plan} plan</span>
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: !result ? '1fr' : '1fr 1fr', gap: 20 }}>
        {/* Upload Panel */}
        <Panel title="Upload Resume">
          <div style={{ textAlign: 'center', padding: '30px 20px' }}>
            <input ref={fileRef} type="file" accept=".pdf" onChange={handleFileChange} style={{ display: 'none' }} />
            <div
              onClick={() => fileRef.current?.click()}
              style={{
                border: '2px dashed #ddd', borderRadius: 12, padding: '40px 20px', cursor: 'pointer',
                background: file ? '#f0fdf4' : '#fafafa', transition: 'all 0.2s',
              }}
            >
              <p style={{ fontSize: 32, margin: '0 0 8px' }}>{file ? '📄' : '📎'}</p>
              {file ? (
                <>
                  <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{file.name}</p>
                  <p style={{ fontSize: 12, color: '#666' }}>{(file.size / 1024).toFixed(1)} KB</p>
                </>
              ) : (
                <>
                  <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>Click to upload PDF</p>
                  <p style={{ fontSize: 12, color: '#999' }}>Max 10MB</p>
                </>
              )}
            </div>
            <button
              onClick={handleUpload}
              disabled={!file || loading}
              style={{
                marginTop: 16, padding: '12px 32px', background: file ? '#ff9900' : '#ccc',
                color: 'white', border: 'none', borderRadius: 8, fontSize: 14, fontWeight: 600,
                cursor: file ? 'pointer' : 'not-allowed',
              }}
            >
              {loading ? 'Analyzing...' : 'Score My Resume'}
            </button>
          </div>

          {/* Limits info */}
          <div style={{ borderTop: '1px solid #f0f0f0', padding: '12px 16px', fontSize: 12, color: '#888' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span>Free plan: 10 checks</span>
              <span>Starter (₹49): 50 checks</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Pro (₹99/mo): Unlimited</span>
              <Link href="/billing"><a style={{ color: '#ff9900', fontWeight: 600 }}>Upgrade →</a></Link>
            </div>
          </div>
        </Panel>

        {/* Results Panel */}
        {result && (
          <Panel title="Score Results">
            {/* Overall Score */}
            <div style={{ textAlign: 'center', padding: '20px 0', borderBottom: '1px solid #f0f0f0' }}>
              <div style={{
                width: 100, height: 100, borderRadius: '50%',
                background: `conic-gradient(${getScoreColor(result.score.overall_score)} ${result.score.overall_score * 3.6}deg, #eee 0deg)`,
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 8,
              }}>
                <div style={{
                  width: 80, height: 80, borderRadius: '50%', background: 'white',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                }}>
                  <span style={{ fontSize: 28, fontWeight: 700, color: getScoreColor(result.score.overall_score) }}>
                    {result.score.overall_score}
                  </span>
                  <span style={{ fontSize: 10, color: '#888' }}>/ 100</span>
                </div>
              </div>
              <div style={{ fontSize: 16, fontWeight: 600, color: getScoreColor(result.score.overall_score) }}>
                {getScoreLabel(result.score.overall_score)}
              </div>
            </div>

            {/* Section Scores */}
            {result.score.sections && (
              <div style={{ padding: '16px 0', borderBottom: '1px solid #f0f0f0' }}>
                <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: '#333' }}>Section Breakdown</h4>
                {Object.entries(result.score.sections).map(([key, section]) => (
                  <div key={key} style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 12, textTransform: 'capitalize', color: '#555' }}>
                        {key.replace(/_/g, ' ')}
                      </span>
                      <span style={{ fontSize: 12, fontWeight: 600, color: getScoreColor(section.score) }}>
                        {section.score}
                      </span>
                    </div>
                    <div style={{ height: 6, background: '#eee', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{
                        width: `${section.score}%`, height: '100%', borderRadius: 3,
                        background: getScoreColor(section.score), transition: 'width 0.5s',
                      }} />
                    </div>
                    <p style={{ fontSize: 11, color: '#888', margin: '2px 0 0' }}>{section.feedback}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Strengths */}
            {result.score.strengths?.length > 0 && (
              <div style={{ padding: '16px 0', borderBottom: '1px solid #f0f0f0' }}>
                <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: '#16a34a' }}>Strengths</h4>
                {result.score.strengths.map((s, i) => (
                  <div key={i} style={{ fontSize: 12, color: '#555', marginBottom: 4, paddingLeft: 16, position: 'relative' }}>
                    <span style={{ position: 'absolute', left: 0, color: '#16a34a' }}>✓</span> {s}
                  </div>
                ))}
              </div>
            )}

            {/* Improvements */}
            {result.score.improvements?.length > 0 && (
              <div style={{ padding: '16px 0', borderBottom: '1px solid #f0f0f0' }}>
                <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: '#d97706' }}>Improvements</h4>
                {result.score.improvements.map((s, i) => (
                  <div key={i} style={{ fontSize: 12, color: '#555', marginBottom: 4, paddingLeft: 16, position: 'relative' }}>
                    <span style={{ position: 'absolute', left: 0, color: '#d97706' }}>→</span> {s}
                  </div>
                ))}
              </div>
            )}

            {/* Missing Keywords */}
            {result.score.missing_keywords?.length > 0 && (
              <div style={{ padding: '16px 0', borderBottom: '1px solid #f0f0f0' }}>
                <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: '#dc2626' }}>Missing Keywords</h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {result.score.missing_keywords.map((kw, i) => (
                    <span key={i} className="badge red" style={{ fontSize: 11 }}>{kw}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Detected Skills */}
            {result.detected_skills?.length > 0 && (
              <div style={{ padding: '16px 0' }}>
                <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: '#333' }}>Detected Skills</h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {result.detected_skills.map((skill, i) => (
                    <span key={i} className="badge green" style={{ fontSize: 11 }}>{skill}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Summary */}
            {result.score.summary && (
              <div style={{ padding: '12px 16px', background: '#f8f9fa', borderRadius: 8, marginTop: 12, fontSize: 12, color: '#555', lineHeight: 1.6 }}>
                {result.score.summary}
              </div>
            )}
          </Panel>
        )}
      </div>
    </Layout>
  );
}
