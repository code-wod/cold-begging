import React, { useState } from 'react';
import type { ApplicationProfile } from '../../types';

interface Props {
  profile: ApplicationProfile | null;
  onUpdateProfile: (profile: Partial<ApplicationProfile>) => Promise<void>;
}

export function ProfilePanel({ profile, onUpdateProfile }: Props) {
  const [editing, setEditing] = useState(false);
  const [localProfile, setLocalProfile] = useState<Partial<ApplicationProfile>>(profile || {});
  const [saving, setSaving] = useState(false);

  function update(path: string, value: any) {
    const keys = path.split('.');
    const updated = { ...localProfile };
    let current: any = updated;
    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) current[keys[i]] = {};
      current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = value;
    setLocalProfile(updated);
  }

  async function handleSave() {
    setSaving(true);
    try {
      await onUpdateProfile(localProfile);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  if (!profile) {
    return (
      <div style={styles.empty}>
        <p>No profile found.</p>
        <p>Set up your profile in the web app first.</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>Your Profile</h3>
        <button
          onClick={() => editing ? handleSave() : setEditing(true)}
          style={editing ? styles.saveButton : styles.editButton}
          disabled={saving}
        >
          {saving ? 'Saving...' : editing ? 'Save' : 'Edit'}
        </button>
      </div>

      <div style={styles.sections}>
        {/* Personal Info */}
        <Section title="Personal">
          <Field label="First Name" value={localProfile.personal?.firstName} editing={editing}
            onChange={v => update('personal.firstName', v)} />
          <Field label="Last Name" value={localProfile.personal?.lastName} editing={editing}
            onChange={v => update('personal.lastName', v)} />
          <Field label="Email" value={localProfile.personal?.email} editing={editing}
            onChange={v => update('personal.email', v)} />
          <Field label="Phone" value={localProfile.personal?.phone} editing={editing}
            onChange={v => update('personal.phone', v)} />
          <Field label="Street" value={localProfile.personal?.address?.street} editing={editing}
            onChange={v => update('personal.address.street', v)} />
          <Field label="City" value={localProfile.personal?.address?.city} editing={editing}
            onChange={v => update('personal.address.city', v)} />
          <Field label="State" value={localProfile.personal?.address?.state} editing={editing}
            onChange={v => update('personal.address.state', v)} />
          <Field label="Country" value={localProfile.personal?.address?.country} editing={editing}
            onChange={v => update('personal.address.country', v)} />
          <Field label="Postal Code" value={localProfile.personal?.address?.postalCode} editing={editing}
            onChange={v => update('personal.address.postalCode', v)} />
        </Section>

        {/* Professional */}
        <Section title="Professional">
          <Field label="Current Title" value={localProfile.professional?.currentTitle} editing={editing}
            onChange={v => update('professional.currentTitle', v)} />
          <Field label="Current Company" value={localProfile.professional?.currentCompany} editing={editing}
            onChange={v => update('professional.currentCompany', v)} />
          <Field label="Years of Experience" value={localProfile.professional?.yearsOfExperience} editing={editing}
            onChange={v => update('professional.yearsOfExperience', v)} />
          <Field label="LinkedIn" value={localProfile.professional?.linkedin} editing={editing}
            onChange={v => update('professional.linkedin', v)} />
          <Field label="GitHub" value={localProfile.professional?.github} editing={editing}
            onChange={v => update('professional.github', v)} />
          <Field label="Portfolio" value={localProfile.professional?.portfolio} editing={editing}
            onChange={v => update('professional.portfolio', v)} />
        </Section>

        {/* Work Authorization */}
        <Section title="Work Authorization">
          <Field label="Authorized to Work" value={localProfile.workAuthorization?.authorizedToWork ? 'Yes' : 'No'} editing={editing}
            onChange={v => update('workAuthorization.authorizedToWork', v === 'Yes')} type="select" options={['Yes', 'No']} />
          <Field label="Requires Sponsorship" value={localProfile.workAuthorization?.requiresSponsorship ? 'Yes' : 'No'} editing={editing}
            onChange={v => update('workAuthorization.requiresSponsorship', v === 'Yes')} type="select" options={['Yes', 'No']} />
          <Field label="Willing to Relocate" value={localProfile.workAuthorization?.willingToRelocate ? 'Yes' : 'No'} editing={editing}
            onChange={v => update('workAuthorization.willingToRelocate', v === 'Yes')} type="select" options={['Yes', 'No']} />
        </Section>

        {/* Preferences */}
        <Section title="Preferences">
          <Field label="Notice Period" value={localProfile.preferences?.noticePeriod} editing={editing}
            onChange={v => update('preferences.noticePeriod', v)} />
          <Field label="Salary Expectation" value={localProfile.preferences?.salaryExpectation} editing={editing}
            onChange={v => update('preferences.salaryExpectation', v)} />
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={styles.section}>
      <h4 style={styles.sectionTitle}>{title}</h4>
      {children}
    </div>
  );
}

function Field({
  label,
  value,
  editing,
  onChange,
  type = 'text',
  options,
}: {
  label: string;
  value?: string;
  editing: boolean;
  onChange: (value: string) => void;
  type?: string;
  options?: string[];
}) {
  return (
    <div style={styles.field}>
      <label style={styles.fieldLabel}>{label}</label>
      {editing ? (
        type === 'select' && options ? (
          <select
            value={value || ''}
            onChange={e => onChange(e.target.value)}
            style={styles.fieldInput}
          >
            {options.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        ) : (
          <input
            type="text"
            value={value || ''}
            onChange={e => onChange(e.target.value)}
            style={styles.fieldInput}
          />
        )
      ) : (
        <span style={styles.fieldValue}>{value || '—'}</span>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: '16px',
    fontWeight: 600,
    margin: 0,
  },
  editButton: {
    padding: '6px 12px',
    background: 'white',
    border: '1px solid #ddd',
    borderRadius: '6px',
    fontSize: '12px',
    cursor: 'pointer',
  },
  saveButton: {
    padding: '6px 12px',
    background: '#ff9900',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  sections: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  section: {
    background: 'white',
    borderRadius: '8px',
    padding: '12px',
    border: '1px solid #eee',
  },
  sectionTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#666',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    margin: '0 0 8px 0',
  },
  field: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 0',
    borderBottom: '1px solid #f5f5f5',
  },
  fieldLabel: {
    fontSize: '12px',
    color: '#666',
    flex: 1,
  },
  fieldValue: {
    fontSize: '12px',
    color: '#333',
    textAlign: 'right',
  },
  fieldInput: {
    width: '180px',
    padding: '4px 8px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '12px',
    textAlign: 'right',
  },
  empty: {
    textAlign: 'center',
    padding: '24px',
    color: '#666',
    fontSize: '13px',
  },
};
