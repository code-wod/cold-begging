import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Empty, Panel, Spinner, useToast, Icons, Button, Field, Input, Select, Modal } from '../components/ui';

export default function Resumes() {
  const { user } = useAuth();
  const toast = useToast();
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploadModal, setUploadModal] = useState(false);
  const [linkModal, setLinkModal] = useState(false);
  const [uploadData, setUploadData] = useState({ name: '', resume_type: 'general', is_default: false });
  const [linkData, setLinkData] = useState({ name: '', url: '', resume_type: 'general', is_default: false });
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchResumes();
  }, []);

  const fetchResumes = async () => {
    setLoading(true);
    try {
      const data = await api('/api/jobs/resumes');
      setResumes(data);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    const file = uploadData.file;
    if (!file) {
      toast('Please select a file', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', uploadData.name);
    formData.append('resume_type', uploadData.resume_type);
    formData.append('is_default', uploadData.is_default.toString());

    setUploading(true);
    try {
      const token = localStorage.getItem('cold_email_token');
      const res = await fetch('/api/jobs/resumes', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      if (!res.ok) throw new Error('Upload failed');
      toast('Resume uploaded!', 'success');
      setUploadModal(false);
      setUploadData({ name: '', resume_type: 'general', is_default: false, file: null });
      fetchResumes();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleLink = async () => {
    if (!linkData.name || !linkData.url) {
      toast('Name and URL are required', 'error');
      return;
    }

    try {
      await api('/api/jobs/resumes/link', { method: 'POST', body: linkData });
      toast('Resume link added!', 'success');
      setLinkModal(false);
      setLinkData({ name: '', url: '', resume_type: 'general', is_default: false });
      fetchResumes();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const handleSetDefault = async (resumeId) => {
    try {
      await api(`/api/jobs/resumes/${resumeId}/default`, { method: 'POST' });
      toast('Default resume updated', 'success');
      fetchResumes();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const handleDelete = async (resumeId) => {
    if (!confirm('Delete this resume?')) return;
    try {
      await api(`/api/jobs/resumes/${resumeId}`, { method: 'DELETE' });
      toast('Resume deleted', 'success');
      fetchResumes();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  return (
    <Layout title="Resumes" breadcrumb={<span>Resumes</span>}>
      <div className="page-head">
        <h1>Resume Management</h1>
        <div className="muted">Manage your resume variants for tailored job applications.</div>
      </div>

      <div className="flex" style={{ gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
        <Button onClick={() => setUploadModal(true)}>
          {Icons.plus} Upload Resume
        </Button>
        <Button variant="secondary" onClick={() => setLinkModal(true)}>
          {Icons.link} Add Resume Link
        </Button>
      </div>

      <Panel title={`Resumes (${resumes.length})`}>
        {loading ? (
          <Spinner />
        ) : resumes.length === 0 ? (
          <Empty message="No resumes yet. Upload a PDF or add a link to get started." />
        ) : (
          <div className="resumes-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
            {resumes.map((resume) => (
              <div key={resume.id} className="panel resume-card" style={{ flexDirection: 'column' }}>
                <div className="flex justify-between" style={{ marginBottom: 8 }}>
                  <h3 style={{ fontSize: 16 }}>{resume.name}</h3>
                  {resume.is_default && <span className="badge green">Default</span>}
                </div>
                <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
                  Type: {resume.resume_type}
                </div>
                {resume.filename && (
                  <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
                    File: {resume.filename}
                  </div>
                )}
                {resume.skills.length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    <div className="label" style={{ fontSize: 12, marginBottom: 4 }}>Skills</div>
                    <div className="flex flex-wrap gap-4">
                      {resume.skills.slice(0, 8).map(s => <span key={s} className="badge gray" style={{ fontSize: 11 }}>{s}</span>)}
                      {resume.skills.length > 8 && <span className="badge gray" style={{ fontSize: 11 }}>+{resume.skills.length - 8}</span>}
                    </div>
                  </div>
                )}
                {resume.experience_years && (
                  <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
                    Experience: {resume.experience_years} years
                  </div>
                )}
                <div className="flex justify-between mt-16" style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                  {!resume.is_default && (
                    <Button size="sm" variant="secondary" onClick={() => handleSetDefault(resume.id)}>
                      {Icons.check} Set Default
                    </Button>
                  )}
                  <Button size="sm" variant="danger" onClick={() => handleDelete(resume.id)}>
                    {Icons.trash} Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      {/* Upload Modal */}
      <Modal open={uploadModal} title="Upload Resume" onClose={() => setUploadModal(false)}>
        <form onSubmit={handleUpload}>
          <Field label="Name">
            <Input
              placeholder="e.g., Backend Go Developer"
              value={uploadData.name}
              onChange={(e) => setUploadData({ ...uploadData, name: e.target.value })}
              required
            />
          </Field>
          <Field label="Resume Type">
            <Select
              options={['general', 'backend', 'frontend', 'fullstack', 'devops', 'data', 'mobile', 'other']}
              value={uploadData.resume_type}
              onChange={(e) => setUploadData({ ...uploadData, resume_type: e.target.value })}
            />
          </Field>
          <Field label="Set as Default">
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={uploadData.is_default}
                onChange={(e) => setUploadData({ ...uploadData, is_default: e.target.checked })}
              />
              <span>Make this the default resume</span>
            </label>
          </Field>
          <Field label="PDF File">
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setUploadData({ ...uploadData, file: e.target.files[0] })}
              required
              style={{ display: 'block', marginTop: 8 }}
            />
            <div className="help">PDF only. Text will be extracted for AI matching.</div>
          </Field>
          <div className="mt-16 flex justify-between">
            <Button variant="secondary" type="button" onClick={() => setUploadModal(false)}>Cancel</Button>
            <Button type="submit" disabled={uploading}>{uploading ? <Spinner /> : 'Upload'}</Button>
          </div>
        </form>
      </Modal>

      {/* Link Modal */}
      <Modal open={linkModal} title="Add Resume Link" onClose={() => setLinkModal(false)}>
        <Field label="Name">
          <Input
            placeholder="e.g., LinkedIn Profile"
            value={linkData.name}
            onChange={(e) => setLinkData({ ...linkData, name: e.target.value })}
            required
          />
        </Field>
        <Field label="URL">
          <Input
            type="url"
            placeholder="https://linkedin.com/in/yourname"
            value={linkData.url}
            onChange={(e) => setLinkData({ ...linkData, url: e.target.value })}
            required
          />
        </Field>
        <Field label="Resume Type">
          <Select
            options={['general', 'backend', 'frontend', 'fullstack', 'devops', 'data', 'mobile', 'other']}
            value={linkData.resume_type}
            onChange={(e) => setLinkData({ ...linkData, resume_type: e.target.value })}
          />
        </Field>
        <Field label="Set as Default">
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={linkData.is_default}
              onChange={(e) => setLinkData({ ...linkData, is_default: e.target.checked })}
            />
            <span>Make this the default resume</span>
          </label>
        </Field>
        <div className="mt-16 flex justify-between">
          <Button variant="secondary" onClick={() => setLinkModal(false)}>Cancel</Button>
          <Button onClick={handleLink}>Add Link</Button>
        </div>
      </Modal>
    </Layout>
  );
}