import { useState, useEffect, useCallback } from 'react';
import Layout from '../../components/Layout';
import { Card, Button, Badge, Empty, Spinner, Input } from '../../components/ui';
import api from '../../lib/api';
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

const CONFIDENCE_COLORS = {
  high: 'var(--success)',
  medium: 'var(--warning)',
  low: 'var(--muted)',
};

function getConfidenceLevel(c) {
  if (c >= 0.9) return 'high';
  if (c >= 0.7) return 'medium';
  return 'low';
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

  // Load profile
  useEffect(() => {
    api.get('/job-applications/profile').then((r) => setProfile(r.data)).catch(() => {});
  }, []);

  const extractFields = async () => {
    if (!url.trim()) return;
    setExtracting(true);
    setFields([]);
    setScreenshot(null);
    try {
      const res = await api.post('/job-applications/extract-fields', { job_url: url });
      setFields(res.data.fields || []);
      setScreenshot(res.data.screenshot);
      setAtsPlatform(res.data.ats_platform || '');
      setCompanyName(res.data.company_name || '');
      setRoleTitle(res.data.role_title || '');
    } catch (e) {
      alert('Failed to extract fields: ' + (e.response?.data?.detail || e.message));
    } finally {
      setExtracting(false);
    }
  };

  const updateFieldValue = (index, value) => {
    setFields((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], user_value: value, confidence: 1.0, status: 'filled' };
      return next;
    });
  };

  const fillFromProfile = (fieldIndex, profileKey) => {
    if (!profile) return;
    const val = profile[profileKey];
    if (val !== undefined && val !== null && val !== '') {
      updateFieldValue(fieldIndex, String(val));
    }
  };

  const fillAllFromProfile = () => {
    if (!profile || !fields.length) return;
    const updated = fields.map((f) => {
      if (f.user_value) return f;
      const profileKey = f.profile_field;
      if (profileKey && profile[profileKey]) {
        return { ...f, user_value: String(profile[profileKey]), confidence: 1.0, status: 'filled' };
      }
      return f;
    });
    setFields(updated);
  };

  const fillRemote = async () => {
    setFilling(true);
    try {
      const res = await api.post('/job-applications/fill-remote', {
        job_url: url,
        fields: fields.map((f) => ({
          ...f,
          user_value: f.user_value || f.mapped_value || '',
        })),
      });
      if (res.data.screenshot) {
        setScreenshot(res.data.screenshot);
      }
      alert(`Filled ${res.data.filled_count} fields on the actual page!`);
    } catch (e) {
      alert('Fill failed: ' + (e.response?.data?.detail || e.message));
    } finally {
      setFilling(false);
    }
  };

  const saveAndContinue = async () => {
    setLoading(true);
    try {
      const res = await api.post('/job-applications/save-and-fill', {
        job_url: url,
        fields: fields.map((f) => ({
          ...f,
          user_value: f.user_value || f.mapped_value || '',
        })),
      });
      router.push(`/job-applications/${res.data.id}`);
    } catch (e) {
      alert('Save failed: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  const filteredProfileFields = PROFILE_FIELDS.filter((pf) => {
    if (activeCategory !== 'All' && pf.category !== activeCategory) return false;
    if (profileSearch) {
      const q = profileSearch.toLowerCase();
      return pf.label.toLowerCase().includes(q) || pf.key.toLowerCase().includes(q);
    }
    return true;
  });

  const categories = ['All', ...new Set(PROFILE_FIELDS.map((f) => f.category))];

  return (
    <Layout title="Apply to Job" breadcrumb={[{ label: 'Applications', href: '/job-applications' }, { label: 'Apply' }]}>
      {/* URL Input */}
      <Card style={{ padding: 16, marginBottom: 16 }}>
        <div className="flex" style={{ gap: 8 }}>
          <Input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste job application URL..."
            style={{ flex: 1 }}
            onKeyDown={(e) => e.key === 'Enter' && extractFields()}
          />
          <Button onClick={extractFields} disabled={extracting || !url.trim()}>
            {extracting ? 'Extracting...' : 'Extract Fields'}
          </Button>
          {fields.length > 0 && (
            <>
              <Button variant="outline" onClick={fillAllFromProfile} disabled={filling}>
                Fill All from Profile
              </Button>
              <Button onClick={fillRemote} disabled={filling}>
                {filling ? 'Filling...' : 'Fill on Page'}
              </Button>
              <Button variant="outline" onClick={saveAndContinue} disabled={loading}>
                {loading ? 'Saving...' : 'Save & Continue'}
              </Button>
            </>
          )}
        </div>
        {atsPlatform && (
          <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
            Detected: <Badge>{atsPlatform}</Badge>
            {companyName && <> — {companyName}</>}
            {roleTitle && <> · {roleTitle}</>}
          </div>
        )}
      </Card>

      {extracting && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spinner />
          <div className="muted" style={{ marginTop: 12 }}>Opening browser and extracting fields...</div>
        </div>
      )}

      {/* Side-by-side panels */}
      {fields.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16, alignItems: 'start' }}>
          {/* LEFT: Extracted Fields */}
          <Card style={{ padding: 16 }}>
            <div style={{ fontWeight: 600, marginBottom: 12 }}>
              Form Fields ({fields.length})
            </div>

            {/* Screenshot */}
            {screenshot && (
              <div style={{ marginBottom: 16, textAlign: 'center' }}>
                <img
                  src={`data:image/png;base64,${screenshot}`}
                  alt="Job page"
                  style={{ maxWidth: '100%', borderRadius: 6, border: '1px solid var(--border)' }}
                />
              </div>
            )}

            {/* Fields list */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {fields.map((f, i) => {
                const val = f.user_value || f.mapped_value || '';
                const level = getConfidenceLevel(f.confidence);
                const isSelected = selectedField === i;
                return (
                  <div
                    key={i}
                    onClick={() => setSelectedField(isSelected ? null : i)}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 6,
                      border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                      background: isSelected ? 'var(--accent-bg, rgba(255,153,0,0.05))' : 'var(--card)',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                  >
                    <div className="flex" style={{ justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontWeight: 500, fontSize: 13 }}>{f.field_label || f.field_name || `Field ${i + 1}`}</span>
                      <div className="flex" style={{ gap: 4, alignItems: 'center' }}>
                        {f.required && <Badge color="var(--error)" style={{ fontSize: 9 }}>Required</Badge>}
                        <Badge color={CONFIDENCE_COLORS[level]} style={{ fontSize: 9 }}>
                          {level} ({Math.round(f.confidence * 100)}%)
                        </Badge>
                        {f.field_type !== 'text' && (
                          <Badge style={{ fontSize: 9 }}>{f.field_type}</Badge>
                        )}
                      </div>
                    </div>

                    {f.options && f.options.length > 0 && f.field_type === 'select' ? (
                      <select
                        value={val}
                        onChange={(e) => { e.stopPropagation(); updateFieldValue(i, e.target.value); }}
                        style={{
                          width: '100%', padding: '6px 8px', borderRadius: 4,
                          border: '1px solid var(--border)', background: 'var(--input)', fontSize: 13,
                        }}
                      >
                        <option value="">— Select —</option>
                        {f.options.map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    ) : f.field_type === 'radio' ? (
                      <div className="flex" style={{ gap: 12, flexWrap: 'wrap' }}>
                        {(f.options || []).map((o) => (
                          <label key={o.value} className="flex" style={{ gap: 4, fontSize: 13, cursor: 'pointer' }}
                            onClick={(e) => e.stopPropagation()}>
                            <input
                              type="radio"
                              name={`field_${i}`}
                              value={o.value}
                              checked={val === o.value}
                              onChange={() => updateFieldValue(i, o.value)}
                            />
                            {o.label}
                          </label>
                        ))}
                      </div>
                    ) : f.field_type === 'checkbox' ? (
                      <label className="flex" style={{ gap: 6, fontSize: 13, cursor: 'pointer' }}
                        onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={val === 'true' || val === 'Yes'}
                          onChange={(e) => updateFieldValue(i, e.target.checked ? 'true' : 'false')}
                        />
                        Yes
                      </label>
                    ) : (
                      <input
                        value={val}
                        onChange={(e) => { e.stopPropagation(); updateFieldValue(i, e.target.value); }}
                        onClick={(e) => e.stopPropagation()}
                        placeholder={f.placeholder || f.field_label || 'Enter value...'}
                        style={{
                          width: '100%', padding: '6px 8px', borderRadius: 4,
                          border: '1px solid var(--border)', background: 'var(--input)', fontSize: 13,
                        }}
                      />
                    )}

                    {f.mapping_reasoning && (
                      <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
                        {f.mapping_reasoning}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>

          {/* RIGHT: Profile Values */}
          <Card style={{ padding: 16, position: 'sticky', top: 80 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Your Profile</div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
              {selectedField !== null ? 'Click a value to fill the selected field' : 'Click a field on the left, then pick a profile value'}
            </div>

            {/* Search */}
            <Input
              value={profileSearch}
              onChange={(e) => setProfileSearch(e.target.value)}
              placeholder="Search profile fields..."
              style={{ marginBottom: 8, fontSize: 12 }}
            />

            {/* Category tabs */}
            <div className="flex" style={{ gap: 4, marginBottom: 12, flexWrap: 'wrap' }}>
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  style={{
                    padding: '3px 8px', borderRadius: 4, fontSize: 11, border: 'none', cursor: 'pointer',
                    background: activeCategory === cat ? 'var(--accent)' : 'var(--bg-secondary)',
                    color: activeCategory === cat ? 'white' : 'var(--text)',
                  }}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Profile values */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 500, overflowY: 'auto' }}>
              {!profile ? (
                <Spinner />
              ) : (
                filteredProfileFields.map((pf) => {
                  const val = profile[pf.key];
                  if (val === undefined || val === null || val === '') return null;
                  const isClickable = selectedField !== null;
                  return (
                    <div
                      key={pf.key}
                      onClick={() => isClickable && fillFromProfile(selectedField, pf.key)}
                      style={{
                        padding: '8px 10px', borderRadius: 4,
                        border: '1px solid var(--border)',
                        cursor: isClickable ? 'pointer' : 'default',
                        background: isClickable ? 'var(--bg-secondary)' : 'transparent',
                        transition: 'all 0.15s',
                      }}
                      onMouseEnter={(e) => { if (isClickable) e.currentTarget.style.borderColor = 'var(--accent)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; }}
                    >
                      <div className="muted" style={{ fontSize: 10, marginBottom: 2 }}>{pf.label}</div>
                      <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {String(val)}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Empty state */}
      {!extracting && fields.length === 0 && (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🔗</div>
          <h3 style={{ marginBottom: 8 }}>Paste a job URL above</h3>
          <p className="muted" style={{ fontSize: 14 }}>
            We'll open the page, detect the ATS, and extract all form fields.
            <br />Then you can fill them from your profile side-by-side.
          </p>
        </div>
      )}
    </Layout>
  );
}
