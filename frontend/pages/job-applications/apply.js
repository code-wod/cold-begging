import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../../components/Layout';
import { Panel, Button, Empty, Spinner, Input } from '../../components/ui';
import { api } from '../../lib/api';
import { useRouter } from 'next/router';

const PROFILE_FIELDS = [
  { key: 'full_name', label: 'Full Name', category: 'Personal' },
  { key: 'email', label: 'Email', category: 'Personal' },
  { key: 'phone', label: 'Phone', category: 'Personal' },
  { key: 'location', label: 'Location', category: 'Personal' },
  { key: 'city', label: 'City', category: 'Personal' },
  { key: 'state', label: 'State', category: 'Personal' },
  { key: 'linkedin', label: 'LinkedIn', category: 'Links' },
  { key: 'github', label: 'GitHub', category: 'Links' },
  { key: 'portfolio', label: 'Portfolio', category: 'Links' },
  { key: 'years_experience', label: 'Years Experience', category: 'Experience' },
  { key: 'current_company', label: 'Current Company', category: 'Experience' },
  { key: 'current_title', label: 'Current Title', category: 'Experience' },
  { key: 'desired_salary', label: 'Desired Salary', category: 'Compensation' },
  { key: 'desired_salary_min', label: 'Salary Min', category: 'Compensation' },
  { key: 'desired_salary_max', label: 'Salary Max', category: 'Compensation' },
  { key: 'work_authorization', label: 'Work Authorization', category: 'Legal' },
  { key: 'requires_sponsorship', label: 'Requires Sponsorship', category: 'Legal' },
  { key: 'gender', label: 'Gender', category: 'Demographics' },
  { key: 'ethnicity', label: 'Ethnicity', category: 'Demographics' },
  { key: 'veteran_status', label: 'Veteran Status', category: 'Demographics' },
  { key: 'disability_status', label: 'Disability', category: 'Demographics' },
  { key: 'cover_letter_template', label: 'Cover Letter', category: 'Custom' },
];

const CONFIDENCE_COLORS = { high: 'var(--success)', medium: 'var(--warning)', low: 'var(--muted)' };
function getConfidenceLevel(c) { return c >= 0.9 ? 'high' : c >= 0.7 ? 'medium' : 'low'; }

function Tag({ color, children, style }) {
  return <span style={{ display: 'inline-block', padding: '1px 6px', borderRadius: 4, fontSize: 10, fontWeight: 600, background: color || 'var(--bg-secondary)', color: color ? 'white' : 'var(--text)', ...style }}>{children}</span>;
}

export default function ApplyPage() {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [profile, setProfile] = useState(null);
  const [fields, setFields] = useState([]);
  const [screenshot, setScreenshot] = useState(null);
  const [atsPlatform, setAtsPlatform] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [roleTitle, setRoleTitle] = useState('');
  const [filling, setFilling] = useState(false);
  const [selectedField, setSelectedField] = useState(null);
  const [profileSearch, setProfileSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');
  const [step, setStep] = useState('fill');
  const [filledScreenshot, setFilledScreenshot] = useState(null);
  const [filledCount, setFilledCount] = useState(0);

  useEffect(() => { api('/job-applications/profile').then((data) => setProfile(data)).catch(() => {}); }, []);

  const extractFields = async () => {
    if (!url.trim()) return;
    setExtracting(true); setFields([]); setScreenshot(null); setStep('fill'); setFilledScreenshot(null);
    try {
      const res = await api('/job-applications/extract-fields', { method: 'POST', body: { job_url: url } });
      setFields(res.fields || []); setScreenshot(res.screenshot);
      setAtsPlatform(res.ats_platform || ''); setCompanyName(res.company_name || ''); setRoleTitle(res.role_title || '');
    } catch (e) { alert('Failed: ' + e.message); }
    finally { setExtracting(false); }
  };

  const updateFieldValue = (index, value) => {
    setFields((prev) => { const next = [...prev]; next[index] = { ...next[index], user_value: value, confidence: 1.0, status: 'filled' }; return next; });
  };

  const fillFromProfile = (fieldIndex, profileKey) => {
    if (!profile) return;
    const val = profile[profileKey];
    if (val !== undefined && val !== null && val !== '') updateFieldValue(fieldIndex, String(val));
  };

  const fillAllFromProfile = () => {
    if (!profile || !fields.length) return;
    setFields(fields.map((f) => {
      if (f.user_value) return f;
      const pk = f.profile_field;
      if (pk && profile[pk]) return { ...f, user_value: String(profile[pk]), confidence: 1.0, status: 'filled' };
      return f;
    }));
  };

  const fillRemote = async () => {
    setFilling(true);
    try {
      const res = await api('/job-applications/fill-remote', {
        method: 'POST',
        body: { job_url: url, fields: fields.map((f) => ({ ...f, user_value: f.user_value || f.mapped_value || '' })) },
      });
      setFilledScreenshot(res.screenshot); setFilledCount(res.filled_count); setStep('review');
    } catch (e) { alert('Fill failed: ' + e.message); }
    finally { setFilling(false); }
  };

  const saveAndContinue = async () => {
    setLoading(true);
    try {
      const res = await api('/job-applications/save-and-fill', {
        method: 'POST',
        body: { job_url: url, fields: fields.map((f) => ({ ...f, user_value: f.user_value || f.mapped_value || '' })) },
      });
      router.push(`/job-applications/${res.id}`);
    } catch (e) { alert('Save failed: ' + e.message); }
    finally { setLoading(false); }
  };

  const filteredProfileFields = PROFILE_FIELDS.filter((pf) => {
    if (activeCategory !== 'All' && pf.category !== activeCategory) return false;
    if (profileSearch) { const q = profileSearch.toLowerCase(); return pf.label.toLowerCase().includes(q) || pf.key.toLowerCase().includes(q); }
    return true;
  });
  const categories = ['All', ...new Set(PROFILE_FIELDS.map((f) => f.category))];
  const filledFields = fields.filter((f) => f.user_value || f.mapped_value);
  const unfilledRequired = fields.filter((f) => f.required && !f.user_value && !f.mapped_value);

  const fieldInput = (f, i) => {
    const val = f.user_value || f.mapped_value || '';
    if (f.options && f.options.length > 0 && f.field_type === 'select') {
      return (
        <select value={val} onChange={(e) => { e.stopPropagation(); updateFieldValue(i, e.target.value); }}
          style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: '1px solid var(--border)', background: 'var(--input)', fontSize: 13 }}>
          <option value="">-- Select --</option>
          {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      );
    }
    if (f.field_type === 'radio') {
      return (
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {(f.options || []).map((o) => (
            <label key={o.value} style={{ display: 'flex', gap: 4, fontSize: 13, cursor: 'pointer' }} onClick={(e) => e.stopPropagation()}>
              <input type="radio" name={`field_${i}`} value={o.value} checked={val === o.value} onChange={() => updateFieldValue(i, o.value)} />
              {o.label}
            </label>
          ))}
        </div>
      );
    }
    if (f.field_type === 'checkbox') {
      return (
        <label style={{ display: 'flex', gap: 6, fontSize: 13, cursor: 'pointer' }} onClick={(e) => e.stopPropagation()}>
          <input type="checkbox" checked={val === 'true' || val === 'Yes'} onChange={(e) => updateFieldValue(i, e.target.checked ? 'true' : 'false')} />
          Yes
        </label>
      );
    }
    return (
      <input value={val} onChange={(e) => { e.stopPropagation(); updateFieldValue(i, e.target.value); }}
        onClick={(e) => e.stopPropagation()} placeholder={f.placeholder || f.field_label || 'Enter value...'}
        style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: '1px solid var(--border)', background: 'var(--input)', fontSize: 13 }} />
    );
  };

  return (
    <Layout title="Apply to Job" breadcrumb={<><Link href="/job-applications">Applications</Link> / <span>Apply</span></>}>
      {/* URL Input */}
      <Panel bodyClassName="p-16" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Paste job application URL..."
            style={{ flex: 1 }} onKeyDown={(e) => e.key === 'Enter' && extractFields()} />
          <Button onClick={extractFields} disabled={extracting || !url.trim()}>{extracting ? 'Extracting...' : 'Extract Fields'}</Button>
          {fields.length > 0 && step === 'fill' && (<>
            <Button variant="outline" onClick={fillAllFromProfile} disabled={filling}>Fill All from Profile</Button>
            <Button onClick={fillRemote} disabled={filling || filledFields.length === 0}>{filling ? 'Filling...' : `Fill on Page (${filledFields.length})`}</Button>
          </>)}
          {step === 'review' && (<>
            <Button variant="outline" onClick={() => setStep('fill')}>Back to Edit</Button>
            <Button onClick={saveAndContinue} disabled={loading}>{loading ? 'Saving...' : 'Save & Submit'}</Button>
          </>)}
        </div>
        {atsPlatform && (
          <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
            Detected: <Tag color="var(--accent)">{atsPlatform}</Tag>
            {companyName && <> -- {companyName}</>}{roleTitle && <> | {roleTitle}</>}
          </div>
        )}
      </Panel>

      {extracting && <div style={{ textAlign: 'center', padding: 40 }}><Spinner /><div className="muted" style={{ marginTop: 12 }}>Opening browser and extracting fields...</div></div>}

      {/* FILL STEP */}
      {!extracting && fields.length > 0 && step === 'fill' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 16, alignItems: 'start' }}>
          <Panel title={`Form Fields (${fields.length})`} actions={<div style={{ display: 'flex', gap: 6 }}><Tag color="var(--success)">{filledFields.length} filled</Tag>{unfilledRequired.length > 0 && <Tag color="var(--error)">{unfilledRequired.length} required</Tag>}</div>}>
            {screenshot && <div style={{ marginBottom: 16, textAlign: 'center' }}><img src={`data:image/png;base64,${screenshot}`} alt="Job page" style={{ maxWidth: '100%', borderRadius: 6, border: '1px solid var(--border)' }} /></div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {fields.map((f, i) => {
                const val = f.user_value || f.mapped_value || '';
                const level = getConfidenceLevel(f.confidence);
                const isFilled = !!val;
                const isSelected = selectedField === i;
                return (
                  <div key={i} onClick={() => setSelectedField(isSelected ? null : i)}
                    style={{ padding: '10px 12px', borderRadius: 6, border: `1px solid ${isSelected ? 'var(--accent)' : isFilled ? 'var(--success)' : 'var(--border)'}`,
                      background: isSelected ? 'rgba(255,153,0,0.05)' : isFilled ? 'rgba(0,200,0,0.03)' : 'var(--card)', cursor: 'pointer', transition: 'all 0.15s' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontWeight: 500, fontSize: 13 }}>{f.field_label || f.field_name || `Field ${i+1}`}</span>
                      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                        {f.required && <Tag color="var(--error)" style={{ fontSize: 9 }}>Required</Tag>}
                        <Tag color={CONFIDENCE_COLORS[level]} style={{ fontSize: 9 }}>{Math.round(f.confidence*100)}%</Tag>
                      </div>
                    </div>
                    {fieldInput(f, i)}
                  </div>
                );
              })}
            </div>
          </Panel>

          {/* RIGHT: Profile */}
          <Panel title="Your Profile" style={{ position: 'sticky', top: 80 }}>
            <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>{selectedField !== null ? 'Click a value to fill the selected field' : 'Click a field on the left, then pick a value'}</div>
            <Input value={profileSearch} onChange={(e) => setProfileSearch(e.target.value)} placeholder="Search..." style={{ marginBottom: 8, fontSize: 12 }} />
            <div style={{ display: 'flex', gap: 4, marginBottom: 12, flexWrap: 'wrap' }}>
              {categories.map((cat) => (
                <button key={cat} onClick={() => setActiveCategory(cat)}
                  style={{ padding: '3px 8px', borderRadius: 4, fontSize: 11, border: 'none', cursor: 'pointer',
                    background: activeCategory === cat ? 'var(--accent)' : 'var(--bg-secondary)', color: activeCategory === cat ? 'white' : 'var(--text)' }}>{cat}</button>
              ))}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 500, overflowY: 'auto' }}>
              {!profile ? <Spinner /> : filteredProfileFields.map((pf) => {
                const val = profile[pf.key];
                if (!val) return null;
                const clickable = selectedField !== null;
                return (
                  <div key={pf.key} onClick={() => clickable && fillFromProfile(selectedField, pf.key)}
                    style={{ padding: '8px 10px', borderRadius: 4, border: '1px solid var(--border)', cursor: clickable ? 'pointer' : 'default',
                      background: clickable ? 'var(--bg-secondary)' : 'transparent', transition: 'all 0.15s' }}
                    onMouseEnter={(e) => { if (clickable) e.currentTarget.style.borderColor = 'var(--accent)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; }}>
                    <div className="muted" style={{ fontSize: 10, marginBottom: 2 }}>{pf.label}</div>
                    <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{String(val)}</div>
                  </div>
                );
              })}
            </div>
          </Panel>
        </div>
      )}

      {/* REVIEW STEP */}
      {!extracting && fields.length > 0 && step === 'review' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 16, alignItems: 'start' }}>
          <Panel title={`Filled Page Preview -- ${filledCount} field${filledCount !== 1 ? 's' : ''} filled`}>
            {(filledScreenshot || screenshot) ? (
              <div style={{ textAlign: 'center' }}><img src={`data:image/png;base64,${filledScreenshot || screenshot}`} alt="Filled page" style={{ maxWidth: '100%', borderRadius: 6, border: '1px solid var(--border)' }} /></div>
            ) : <Empty message="No screenshot" />}
            <div className="muted" style={{ fontSize: 12, marginTop: 12, textAlign: 'center' }}>Review the filled form above. Click "Back to Edit" to change, or "Save & Submit" to proceed.</div>
          </Panel>
          <Panel title="Field Summary" style={{ position: 'sticky', top: 80 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {fields.map((f, i) => {
                const val = f.user_value || f.mapped_value || '';
                const isFilled = !!val;
                return (
                  <div key={i} style={{ padding: '8px 10px', borderRadius: 4, border: `1px solid ${isFilled ? 'var(--success)' : 'var(--border)'}`, background: isFilled ? 'rgba(0,200,0,0.03)' : 'transparent' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 12, fontWeight: 500 }}>{f.field_label || f.field_name || `Field ${i+1}`}</span>
                      {isFilled ? <Tag color="var(--success)" style={{ fontSize: 9 }}>Filled</Tag> : f.required ? <Tag color="var(--error)" style={{ fontSize: 9 }}>Required</Tag> : <Tag style={{ fontSize: 9 }}>Empty</Tag>}
                    </div>
                    {isFilled && <div style={{ fontSize: 12, marginTop: 2, color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{val}</div>}
                  </div>
                );
              })}
            </div>
            <div style={{ marginTop: 16, padding: 12, borderRadius: 6, background: 'var(--bg-secondary)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}><span style={{ fontSize: 13 }}>Total</span><span style={{ fontWeight: 600 }}>{fields.length}</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}><span style={{ fontSize: 13, color: 'var(--success)' }}>Filled</span><span style={{ fontWeight: 600, color: 'var(--success)' }}>{filledFields.length}</span></div>
              {unfilledRequired.length > 0 && <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ fontSize: 13, color: 'var(--error)' }}>Required missing</span><span style={{ fontWeight: 600, color: 'var(--error)' }}>{unfilledRequired.length}</span></div>}
            </div>
          </Panel>
        </div>
      )}

      {!extracting && fields.length === 0 && (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <h3 style={{ marginBottom: 8 }}>Paste a job URL above</h3>
          <p className="muted" style={{ fontSize: 14 }}>We will open the page, detect the ATS, and extract all form fields.<br />Then you can fill them from your profile side-by-side.</p>
        </div>
      )}
    </Layout>
  );
}
