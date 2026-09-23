import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import {
  Button, Field, Input, Select, TextArea, Panel, Spinner, useToast, Icons, Empty,
} from '../components/ui';

const EMPTY_PROFILE = {
  first_name: '', middle_name: '', last_name: '', preferred_name: '',
  email: '', phone: '', country: '', state: '', city: '', address: '', postal_code: '',
  current_title: '', current_company: '', years_of_experience: null,
  linkedin_url: '', github_url: '', portfolio_url: '', personal_website: '',
  degree: '', field_of_study: '', university: '', graduation_year: null, gpa: '',
  education_history: [],
  authorized_to_work: null, requires_sponsorship: null,
  work_authorization_countries: [],
  preferred_locations: [], remote_preference: 'any', employment_type: 'full_time',
  notice_period: '', expected_salary: '', expected_salary_currency: 'USD',
  willing_to_relocate: null, willing_to_travel: null,
  programming_languages: [], frameworks: [], databases: [], tools: [], other_skills: [],
  experience_history: [], projects: [], certifications: [],
  common_answers: {}, eeoo_answers: {}, custom_answers: {},
};

function TagInput({ value = [], onChange, placeholder }) {
  const [input, setInput] = useState('');
  const add = () => {
    const v = input.trim();
    if (v && !value.includes(v)) { onChange([...value, v]); setInput(''); }
  };
  const remove = (i) => onChange(value.filter((_, idx) => idx !== i));
  return (
    <div>
      <div className="flex" style={{ flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
        {value.map((tag, i) => (
          <span key={i} className="badge teal" style={{ fontSize: 12, cursor: 'pointer' }} onClick={() => remove(i)}>
            {tag} {Icons.x}
          </span>
        ))}
      </div>
      <div className="flex" style={{ gap: 6 }}>
        <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder={placeholder}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add(); } }} />
        <Button size="sm" onClick={add}>Add</Button>
      </div>
    </div>
  );
}

function BoolField({ label, value, onChange }) {
  return (
    <Field label={label}>
      <div className="flex" style={{ gap: 16 }}>
        <label className="flex" style={{ fontSize: 13.5 }}>
          <input type="radio" name={label} checked={value === true} onChange={() => onChange(true)} /> Yes
        </label>
        <label className="flex" style={{ fontSize: 13.5 }}>
          <input type="radio" name={label} checked={value === false} onChange={() => onChange(false)} /> No
        </label>
        <label className="flex" style={{ fontSize: 13.5 }}>
          <input type="radio" name={label} checked={value === null} onChange={() => onChange(null)} /> Prefer not to say
        </label>
      </div>
    </Field>
  );
}

function ExperienceItem({ item, onChange, onRemove }) {
  return (
    <div className="panel" style={{ padding: 12, marginBottom: 8 }}>
      <div className="flex justify-between" style={{ marginBottom: 8 }}>
        <b style={{ fontSize: 13 }}>Experience Entry</b>
        <button className="btn ghost sm" onClick={onRemove}>{Icons.trash}</button>
      </div>
      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <Field label="Company">
          <Input value={item.company || ''} onChange={(e) => onChange({ ...item, company: e.target.value })} />
        </Field>
        <Field label="Title">
          <Input value={item.title || ''} onChange={(e) => onChange({ ...item, title: e.target.value })} />
        </Field>
        <Field label="Location">
          <Input value={item.location || ''} onChange={(e) => onChange({ ...item, location: e.target.value })} />
        </Field>
        <Field label="Start Date">
          <Input value={item.start_date || ''} onChange={(e) => onChange({ ...item, start_date: e.target.value })} placeholder="MM/YYYY" />
        </Field>
        <Field label="End Date">
          <Input value={item.end_date || ''} onChange={(e) => onChange({ ...item, end_date: e.target.value })} placeholder="MM/YYYY or Present" disabled={item.currently_working} />
        </Field>
        <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: 4 }}>
          <label className="flex" style={{ fontSize: 13 }}>
            <input type="checkbox" checked={!!item.currently_working}
              onChange={(e) => onChange({ ...item, currently_working: e.target.checked, end_date: e.target.checked ? 'Present' : '' })} />
            {' '}Currently working here
          </label>
        </div>
      </div>
      <Field label="Description">
        <TextArea rows={2} value={item.description || ''} onChange={(e) => onChange({ ...item, description: e.target.value })} />
      </Field>
    </div>
  );
}

function ProjectItem({ item, onChange, onRemove }) {
  return (
    <div className="panel" style={{ padding: 12, marginBottom: 8 }}>
      <div className="flex justify-between" style={{ marginBottom: 8 }}>
        <b style={{ fontSize: 13 }}>Project</b>
        <button className="btn ghost sm" onClick={onRemove}>{Icons.trash}</button>
      </div>
      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <Field label="Name">
          <Input value={item.name || ''} onChange={(e) => onChange({ ...item, name: e.target.value })} />
        </Field>
        <Field label="URL">
          <Input value={item.url || ''} onChange={(e) => onChange({ ...item, url: e.target.value })} />
        </Field>
      </div>
      <Field label="Description">
        <TextArea rows={2} value={item.description || ''} onChange={(e) => onChange({ ...item, description: e.target.value })} />
      </Field>
      <Field label="Technologies (comma-separated)">
        <Input value={(item.technologies || []).join(', ')}
          onChange={(e) => onChange({ ...item, technologies: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} />
      </Field>
    </div>
  );
}

export default function JobProfile() {
  const { user } = useAuth();
  const toast = useToast();
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState(EMPTY_PROFILE);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('personal');

  useEffect(() => {
    if (user) loadProfile();
  }, [user]);

  const loadProfile = async () => {
    try {
      const data = await api('/api/job-applications/profile');
      setProfile(data);
      setForm({ ...EMPTY_PROFILE, ...data });
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      const data = await api('/api/job-applications/profile', { method: 'PUT', body: form });
      setProfile(data);
      setForm({ ...EMPTY_PROFILE, ...data });
      toast('Profile saved', 'success');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const updateField = (key, val) => setForm({ ...form, [key]: val });

  const tabs = [
    { id: 'personal', label: 'Personal' },
    { id: 'contact', label: 'Contact' },
    { id: 'professional', label: 'Professional' },
    { id: 'education', label: 'Education' },
    { id: 'skills', label: 'Skills' },
    { id: 'experience', label: 'Experience' },
    { id: 'projects', label: 'Projects' },
    { id: 'work_auth', label: 'Work Authorization' },
    { id: 'preferences', label: 'Preferences' },
    { id: 'answers', label: 'Common Answers' },
  ];

  if (!user) return <Layout title="Job Profile"><Spinner /></Layout>;

  return (
    <Layout title="Job Profile" breadcrumb={<><span>Job Profile</span></>}>
      <div className="page-head">
        <h1>Job Application Profile</h1>
        <div className="muted">Your centralized profile for autofilling job applications.</div>
      </div>

      <div className="flex" style={{ gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {tabs.map((t) => (
          <Button key={t.id} size="sm" variant={activeTab === t.id ? 'primary' : 'secondary'}
            onClick={() => setActiveTab(t.id)}>
            {t.label}
          </Button>
        ))}
      </div>

      <Panel>
        {profile === null ? <Spinner /> : (
          <>
            {/* Personal */}
            {activeTab === 'personal' && (
              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                <Field label="First Name"><Input value={form.first_name} onChange={(e) => updateField('first_name', e.target.value)} /></Field>
                <Field label="Middle Name"><Input value={form.middle_name} onChange={(e) => updateField('middle_name', e.target.value)} /></Field>
                <Field label="Last Name"><Input value={form.last_name} onChange={(e) => updateField('last_name', e.target.value)} /></Field>
                <Field label="Preferred Name"><Input value={form.preferred_name} onChange={(e) => updateField('preferred_name', e.target.value)} /></Field>
              </div>
            )}

            {/* Contact */}
            {activeTab === 'contact' && (
              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <Field label="Email"><Input type="email" value={form.email} onChange={(e) => updateField('email', e.target.value)} /></Field>
                <Field label="Phone"><Input value={form.phone} onChange={(e) => updateField('phone', e.target.value)} /></Field>
                <Field label="Country"><Input value={form.country} onChange={(e) => updateField('country', e.target.value)} /></Field>
                <Field label="State / Province"><Input value={form.state} onChange={(e) => updateField('state', e.target.value)} /></Field>
                <Field label="City"><Input value={form.city} onChange={(e) => updateField('city', e.target.value)} /></Field>
                <Field label="Postal Code"><Input value={form.postal_code} onChange={(e) => updateField('postal_code', e.target.value)} /></Field>
                <div style={{ gridColumn: '1 / -1' }}>
                  <Field label="Address"><Input value={form.address} onChange={(e) => updateField('address', e.target.value)} /></Field>
                </div>
              </div>
            )}

            {/* Professional */}
            {activeTab === 'professional' && (
              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <Field label="Current Title"><Input value={form.current_title} onChange={(e) => updateField('current_title', e.target.value)} /></Field>
                <Field label="Current Company"><Input value={form.current_company} onChange={(e) => updateField('current_company', e.target.value)} /></Field>
                <Field label="Years of Experience"><Input type="number" value={form.years_of_experience ?? ''} onChange={(e) => updateField('years_of_experience', e.target.value ? parseInt(e.target.value) : null)} /></Field>
                <div />
                <Field label="LinkedIn URL"><Input value={form.linkedin_url} onChange={(e) => updateField('linkedin_url', e.target.value)} /></Field>
                <Field label="GitHub URL"><Input value={form.github_url} onChange={(e) => updateField('github_url', e.target.value)} /></Field>
                <Field label="Portfolio URL"><Input value={form.portfolio_url} onChange={(e) => updateField('portfolio_url', e.target.value)} /></Field>
                <Field label="Personal Website"><Input value={form.personal_website} onChange={(e) => updateField('personal_website', e.target.value)} /></Field>
              </div>
            )}

            {/* Education */}
            {activeTab === 'education' && (
              <div>
                <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <Field label="University / School"><Input value={form.university} onChange={(e) => updateField('university', e.target.value)} /></Field>
                  <Field label="Degree"><Input value={form.degree} onChange={(e) => updateField('degree', e.target.value)} /></Field>
                  <Field label="Field of Study"><Input value={form.field_of_study} onChange={(e) => updateField('field_of_study', e.target.value)} /></Field>
                  <Field label="Graduation Year"><Input type="number" value={form.graduation_year ?? ''} onChange={(e) => updateField('graduation_year', e.target.value ? parseInt(e.target.value) : null)} /></Field>
                  <Field label="GPA"><Input value={form.gpa} onChange={(e) => updateField('gpa', e.target.value)} /></Field>
                </div>
                <div style={{ marginTop: 16 }}>
                  <div className="flex justify-between" style={{ marginBottom: 8 }}>
                    <b>Education History</b>
                    <Button size="sm" onClick={() => updateField('education_history', [...form.education_history, { school: '', degree: '', field: '', year: '' }])}>
                      {Icons.plus} Add
                    </Button>
                  </div>
                  {form.education_history.map((item, i) => (
                    <div key={i} className="panel" style={{ padding: 12, marginBottom: 8 }}>
                      <div className="flex justify-between" style={{ marginBottom: 8 }}>
                        <b style={{ fontSize: 13 }}>Education {i + 1}</b>
                        <button className="btn ghost sm" onClick={() => updateField('education_history', form.education_history.filter((_, idx) => idx !== i))}>{Icons.trash}</button>
                      </div>
                      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                        <Field label="School"><Input value={item.school || ''} onChange={(e) => { const arr = [...form.education_history]; arr[i] = { ...arr[i], school: e.target.value }; updateField('education_history', arr); }} /></Field>
                        <Field label="Degree"><Input value={item.degree || ''} onChange={(e) => { const arr = [...form.education_history]; arr[i] = { ...arr[i], degree: e.target.value }; updateField('education_history', arr); }} /></Field>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Skills */}
            {activeTab === 'skills' && (
              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                  <Field label="Programming Languages">
                    <TagInput value={form.programming_languages} onChange={(v) => updateField('programming_languages', v)} placeholder="e.g. Python, JavaScript" />
                  </Field>
                  <Field label="Frameworks">
                    <TagInput value={form.frameworks} onChange={(v) => updateField('frameworks', v)} placeholder="e.g. React, Django" />
                  </Field>
                  <Field label="Databases">
                    <TagInput value={form.databases} onChange={(v) => updateField('databases', v)} placeholder="e.g. PostgreSQL, MongoDB" />
                  </Field>
                </div>
                <div>
                  <Field label="Tools">
                    <TagInput value={form.tools} onChange={(v) => updateField('tools', v)} placeholder="e.g. Docker, Git, AWS" />
                  </Field>
                  <Field label="Other Skills">
                    <TagInput value={form.other_skills} onChange={(v) => updateField('other_skills', v)} placeholder="e.g. System Design, Agile" />
                  </Field>
                </div>
              </div>
            )}

            {/* Experience */}
            {activeTab === 'experience' && (
              <div>
                <div className="flex justify-between" style={{ marginBottom: 12 }}>
                  <b>Work Experience</b>
                  <Button size="sm" onClick={() => updateField('experience_history', [...form.experience_history, { company: '', title: '', location: '', start_date: '', end_date: '', currently_working: false, description: '' }])}>
                    {Icons.plus} Add Experience
                  </Button>
                </div>
                {form.experience_history.length === 0 && <Empty message="No experience entries yet." />}
                {form.experience_history.map((item, i) => (
                  <ExperienceItem key={i} item={item}
                    onChange={(updated) => { const arr = [...form.experience_history]; arr[i] = updated; updateField('experience_history', arr); }}
                    onRemove={() => updateField('experience_history', form.experience_history.filter((_, idx) => idx !== i))} />
                ))}
              </div>
            )}

            {/* Projects */}
            {activeTab === 'projects' && (
              <div>
                <div className="flex justify-between" style={{ marginBottom: 12 }}>
                  <b>Projects</b>
                  <Button size="sm" onClick={() => updateField('projects', [...form.projects, { name: '', description: '', technologies: [], url: '' }])}>
                    {Icons.plus} Add Project
                  </Button>
                </div>
                {form.projects.length === 0 && <Empty message="No projects yet." />}
                {form.projects.map((item, i) => (
                  <ProjectItem key={i} item={item}
                    onChange={(updated) => { const arr = [...form.projects]; arr[i] = updated; updateField('projects', arr); }}
                    onRemove={() => updateField('projects', form.projects.filter((_, idx) => idx !== i))} />
                ))}
              </div>
            )}

            {/* Work Authorization */}
            {activeTab === 'work_auth' && (
              <div>
                <BoolField label="Authorized to work in your country?" value={form.authorized_to_work} onChange={(v) => updateField('authorized_to_work', v)} />
                <BoolField label="Require visa sponsorship?" value={form.requires_sponsorship} onChange={(v) => updateField('requires_sponsorship', v)} />
                <Field label="Countries where authorized">
                  <TagInput value={form.work_authorization_countries} onChange={(v) => updateField('work_authorization_countries', v)} placeholder="e.g. US, UK, Canada" />
                </Field>
              </div>
            )}

            {/* Preferences */}
            {activeTab === 'preferences' && (
              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <Field label="Preferred Locations">
                  <TagInput value={form.preferred_locations} onChange={(v) => updateField('preferred_locations', v)} placeholder="e.g. San Francisco, Remote" />
                </Field>
                <Field label="Remote Preference">
                  <Select value={form.remote_preference} onChange={(e) => updateField('remote_preference', e.target.value)}
                    options={['any', 'remote_only', 'hybrid_or_remote', 'onsite_only']} />
                </Field>
                <Field label="Employment Type">
                  <Select value={form.employment_type} onChange={(e) => updateField('employment_type', e.target.value)}
                    options={['full_time', 'part_time', 'contract', 'internship']} />
                </Field>
                <Field label="Notice Period"><Input value={form.notice_period} onChange={(e) => updateField('notice_period', e.target.value)} placeholder="e.g. 2 weeks" /></Field>
                <Field label="Expected Salary"><Input value={form.expected_salary} onChange={(e) => updateField('expected_salary', e.target.value)} placeholder="e.g. 120000" /></Field>
                <Field label="Currency"><Input value={form.expected_salary_currency} onChange={(e) => updateField('expected_salary_currency', e.target.value)} /></Field>
                <BoolField label="Willing to relocate?" value={form.willing_to_relocate} onChange={(v) => updateField('willing_to_relocate', v)} />
                <BoolField label="Willing to travel?" value={form.willing_to_travel} onChange={(v) => updateField('willing_to_travel', v)} />
              </div>
            )}

            {/* Common Answers */}
            {activeTab === 'answers' && (
              <div>
                <div className="muted" style={{ marginBottom: 12, fontSize: 13 }}>
                  Pre-configure answers for common application questions. These will be used automatically when matching questions are found.
                </div>
                <Field label="How did you hear about us?">
                  <TextArea rows={2} value={form.common_answers?.how_heard || ''}
                    onChange={(e) => updateField('common_answers', { ...form.common_answers, how_heard: e.target.value })} />
                </Field>
                <Field label="Why do you want to work at this company?">
                  <TextArea rows={3} value={form.common_answers?.why_company || ''}
                    onChange={(e) => updateField('common_answers', { ...form.common_answers, why_company: e.target.value })} />
                </Field>
                <Field label="Cover Letter / Additional Information">
                  <TextArea rows={3} value={form.common_answers?.additional || ''}
                    onChange={(e) => updateField('common_answers', { ...form.common_answers, additional: e.target.value })} />
                </Field>
              </div>
            )}

            <div className="flex justify-between" style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
              <div className="muted" style={{ fontSize: 12 }}>
                {profile.updated_at && `Last saved: ${new Date(profile.updated_at).toLocaleString()}`}
              </div>
              <Button onClick={save} disabled={saving}>{saving ? 'Saving...' : 'Save Profile'}</Button>
            </div>
          </>
        )}
      </Panel>
    </Layout>
  );
}
