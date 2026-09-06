import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Spinner, useToast, Icons, Button, Field, Input, TextArea, Panel } from '../components/ui';

export default function JobPreferences() {
  const { user } = useAuth();
  const toast = useToast();
  const [prefs, setPrefs] = useState({
    preferred_roles: [],
    preferred_locations: [],
    employment_types: [],
    experience_levels: [],
    skills: [],
    minimum_salary: '',
    currency: 'USD',
    remote_preference: 'any',
    visa_sponsorship: false
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Input states for multi-select fields
  const [roleInput, setRoleInput] = useState('');
  const [locationInput, setLocationInput] = useState('');
  const [skillInput, setSkillInput] = useState('');

  useEffect(() => {
    fetchPreferences();
  }, []);

  const fetchPreferences = async () => {
    setLoading(true);
    try {
      const data = await api('/api/jobs/preferences');
      setPrefs({
        preferred_roles: data.preferred_roles || [],
        preferred_locations: data.preferred_locations || [],
        employment_types: data.employment_types || [],
        experience_levels: data.experience_levels || [],
        skills: data.skills || [],
        minimum_salary: data.minimum_salary || '',
        currency: data.currency || 'USD',
        remote_preference: data.remote_preference || 'any',
        visa_sponsorship: data.visa_sponsorship || false
      });
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const addItem = (field, value) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    setPrefs(prev => {
      if (prev[field].includes(trimmed)) return prev;
      return { ...prev, [field]: [...prev[field], trimmed] };
    });
  };

  const removeItem = (field, value) => {
    setPrefs(prev => ({
      ...prev,
      [field]: prev[field].filter(v => v !== value)
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api('/api/jobs/preferences', { method: 'PUT', body: prefs });
      toast('Preferences saved!', 'success');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <Layout title="Job Preferences" breadcrumb={<span>Job Preferences</span>}><Spinner /></Layout>;
  }

  return (
    <Layout title="Job Preferences" breadcrumb={<span>Job Preferences</span>}>
      <div className="page-head">
        <h1>Job Search Preferences</h1>
        <div className="muted">Configure your ideal job criteria for AI-powered matching.</div>
      </div>

      <Panel title="Preferred Roles" actions={
        <div style={{ display: 'flex', gap: 8 }}>
          <Input
            value={roleInput}
            onChange={(e) => setRoleInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addItem('preferred_roles', roleInput), setRoleInput(''))}
            placeholder="e.g., Backend Engineer"
            style={{ width: 200 }}
          />
          <Button size="sm" onClick={() => addItem('preferred_roles', roleInput), setRoleInput('')}>
            {Icons.plus} Add
          </Button>
        </div>
      }>
        {prefs.preferred_roles.length === 0 ? (
          <div className="muted" style={{ padding: 16 }}>No preferred roles added.</div>
        ) : (
          <div className="flex flex-wrap gap-4">
            {prefs.preferred_roles.map((role) => (
              <span key={role} className="badge blue" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                {role}
                <button onClick={() => removeItem('preferred_roles', role)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0, fontSize: 14, lineHeight: 1 }}>
                  {Icons.x}
                </button>
              </span>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Preferred Locations" actions={
        <div style={{ display: 'flex', gap: 8 }}>
          <Input
            value={locationInput}
            onChange={(e) => setLocationInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addItem('preferred_locations', locationInput), setLocationInput(''))}
            placeholder="e.g., San Francisco, Remote, India"
            style={{ width: 200 }}
          />
          <Button size="sm" onClick={() => addItem('preferred_locations', locationInput), setLocationInput('')}>
            {Icons.plus} Add
          </Button>
        </div>
      }>
        {prefs.preferred_locations.length === 0 ? (
          <div className="muted" style={{ padding: 16 }}>No preferred locations added.</div>
        ) : (
          <div className="flex flex-wrap gap-4">
            {prefs.preferred_locations.map((loc) => (
              <span key={loc} className="badge teal" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                {loc}
                <button onClick={() => removeItem('preferred_locations', loc)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0, fontSize: 14, lineHeight: 1 }}>
                  {Icons.x}
                </button>
              </span>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Skills" actions={
        <div style={{ display: 'flex', gap: 8 }}>
          <Input
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addItem('skills', skillInput), setSkillInput(''))}
            placeholder="e.g., Python, React, AWS"
            style={{ width: 200 }}
          />
          <Button size="sm" onClick={() => addItem('skills', skillInput), setSkillInput('')}>
            {Icons.plus} Add
          </Button>
        </div>
      }>
        {prefs.skills.length === 0 ? (
          <div className="muted" style={{ padding: 16 }}>No skills added.</div>
        ) : (
          <div className="flex flex-wrap gap-4">
            {prefs.skills.map((skill) => (
              <span key={skill} className="badge green" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                {skill}
                <button onClick={() => removeItem('skills', skill)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0, fontSize: 14, lineHeight: 1 }}>
                  {Icons.x}
                </button>
              </span>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Employment Preferences">
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          <Field label="Employment Types">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {['full_time', 'part_time', 'contract', 'internship'].map(type => (
                <label key={type} style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={prefs.employment_types.includes(type)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setPrefs(prev => ({ ...prev, employment_types: [...prev.employment_types, type] }));
                      } else {
                        setPrefs(prev => ({ ...prev, employment_types: prev.employment_types.filter(t => t !== type) }));
                      }
                    }}
                  />
                  <span>{type.replace('_', ' ')}</span>
                </label>
              ))}
            </div>
          </Field>

          <Field label="Experience Levels">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {['entry', 'junior', 'mid', 'senior', 'lead', 'principal'].map(level => (
                <label key={level} style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={prefs.experience_levels.includes(level)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setPrefs(prev => ({ ...prev, experience_levels: [...prev.experience_levels, level] }));
                      } else {
                        setPrefs(prev => ({ ...prev, experience_levels: prev.experience_levels.filter(l => l !== level) }));
                      }
                    }}
                  />
                  <span>{level}</span>
                </label>
              ))}
            </div>
          </Field>

          <Field label="Remote Preference">
            <Select
              options={[
                { value: 'any', label: 'Any' },
                { value: 'remote_only', label: 'Remote Only' },
                { value: 'hybrid_or_remote', label: 'Hybrid or Remote' },
                { value: 'onsite_only', label: 'Onsite Only' }
              ]}
              value={prefs.remote_preference}
              onChange={(e) => setPrefs({ ...prefs, remote_preference: e.target.value })}
            />
          </Field>

          <Field label="Minimum Salary (annual)">
            <Input
              type="number"
              placeholder="100000"
              value={prefs.minimum_salary}
              onChange={(e) => setPrefs({ ...prefs, minimum_salary: e.target.value })}
            />
          </Field>

          <Field label="Currency">
            <Select
              options={['USD', 'EUR', 'GBP', 'INR', 'CAD', 'AUD']}
              value={prefs.currency}
              onChange={(e) => setPrefs({ ...prefs, currency: e.target.value })}
            />
          </Field>

          <Field label="Visa Sponsorship Required">
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={prefs.visa_sponsorship}
                onChange={(e) => setPrefs({ ...prefs, visa_sponsorship: e.target.checked })}
              />
              <span>I require visa sponsorship</span>
            </label>
          </Field>
        </div>
      </Panel>

      <div className="mt-16 flex justify-between">
        <Button variant="secondary" onClick={fetchPreferences}>{Icons.refresh} Reset</Button>
        <Button onClick={handleSave} disabled={saving}>{saving ? <Spinner /> : 'Save Preferences'}</Button>
      </div>
    </Layout>
  );
}