'use client';

import { useEffect, useMemo, useState } from 'react';
import { Database, Download, Eye, FileUp, LogIn, Play, RefreshCw, RotateCcw, Save, Shield, Trash2, UserPlus } from 'lucide-react';

type UploadItem = {
  id: number;
  original_filename: string;
  size_bytes: number;
  data_type: string;
  created_at: string;
};

type ImportJob = {
  id: number;
  upload_id: number;
  data_type: string;
  status: string;
  message: string | null;
  created_at: string;
  completed_at: string | null;
  has_error_report: boolean;
};

type BackupItem = {
  id: number;
  action: string;
  status: string;
  filename: string;
  size_bytes: number;
  message: string | null;
  created_at: string;
};

type AdminStats = {
  sample_count: number;
  taxon_count: number;
  taxonomy_abundance_count: number;
  functional_feature_count: number;
  functional_abundance_count: number;
  upload_count: number;
  import_job_count: number;
  backup_count: number;
  database_size_bytes: number;
  database_path: string;
  import_status_counts: Record<string, number>;
  functional_feature_counts: Record<string, number>;
};

type UploadPreview = {
  upload_id: number;
  filename: string;
  data_type: string;
  columns: string[];
  required_fields: string[];
  sample_columns: string[];
  preview_rows: Record<string, string>[];
  validation: string[];
};

type SampleItem = {
  id: number;
  sample_id: string;
  province: string | null;
  region: string | null;
  dynasty: string | null;
  period: string | null;
  estimated_year: number | null;
  sex: string | null;
  subsistence_pattern: string | null;
  site_name: string | null;
  latitude: number | null;
  longitude: number | null;
  source: string | null;
};

type AdminUserItem = {
  id: number;
  username: string;
  role: string;
  created_at: string;
};

type AuditLogItem = {
  id: number;
  username: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  status: string;
  detail: string | null;
  created_at: string;
};

const TOKEN_KEY = 'eaam_admin_token';

export default function AdminPage() {
  const [token, setToken] = useState('');
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [dataType, setDataType] = useState('auto');
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [jobs, setJobs] = useState<ImportJob[]>([]);
  const [backups, setBackups] = useState<BackupItem[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [samples, setSamples] = useState<SampleItem[]>([]);
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [preview, setPreview] = useState<UploadPreview | null>(null);
  const [fieldMapping, setFieldMapping] = useState<Record<string, string>>({});
  const [sampleQuery, setSampleQuery] = useState('');
  const [editingSample, setEditingSample] = useState<SampleItem | null>(null);
  const [newAdminUsername, setNewAdminUsername] = useState('');
  const [newAdminPassword, setNewAdminPassword] = useState('');
  const [backupLabel, setBackupLabel] = useState('manual');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const authHeaders = useMemo(
    () => ({ Authorization: `Bearer ${token}` }),
    [token]
  );

  useEffect(() => {
    const stored = window.localStorage.getItem(TOKEN_KEY);
    if (stored) setToken(stored);
  }, []);

  useEffect(() => {
    if (token) {
      refresh();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!token || !jobs.some((job) => job.status === 'running' || job.status === 'pending')) return;
    const timer = window.setInterval(() => {
      refresh(false);
    }, 5000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, jobs]);

  async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
    const res = await fetch(path, {
      ...init,
      headers: {
        ...(token ? authHeaders : {}),
        ...(init.headers || {}),
      },
    });
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`;
      try {
        const body = await res.json();
        detail = body.detail || detail;
      } catch {
        // keep default detail
      }
      throw new Error(detail);
    }
    return res.json() as Promise<T>;
  }

  async function login() {
    setBusy(true);
    setMessage('');
    try {
      const res = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || 'Login failed');
      }
      const body = await res.json();
      window.localStorage.setItem(TOKEN_KEY, body.token);
      setToken(body.token);
      setPassword('');
      setMessage('Logged in.');
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function refresh(showBusy = true) {
    if (showBusy) setBusy(true);
    setMessage('');
    try {
      const results = await Promise.allSettled([
        apiFetch<UploadItem[]>('/api/admin/uploads'),
        apiFetch<ImportJob[]>('/api/admin/imports'),
        apiFetch<BackupItem[]>('/api/admin/backups'),
        apiFetch<AdminStats>('/api/admin/stats'),
        apiFetch<SampleItem[]>(`/api/admin/samples?limit=25${sampleQuery ? `&q=${encodeURIComponent(sampleQuery)}` : ''}`),
        apiFetch<AdminUserItem[]>('/api/admin/users'),
        apiFetch<AuditLogItem[]>('/api/admin/audit-logs?limit=50'),
      ]);
      const [uploadData, jobData, backupData, statsData, sampleData, userData, auditData] = results;
      if (uploadData.status === 'fulfilled') setUploads(uploadData.value);
      if (jobData.status === 'fulfilled') setJobs(jobData.value);
      if (backupData.status === 'fulfilled') setBackups(backupData.value);
      if (statsData.status === 'fulfilled') setStats(statsData.value);
      if (sampleData.status === 'fulfilled') setSamples(sampleData.value);
      if (userData.status === 'fulfilled') setUsers(userData.value);
      if (auditData.status === 'fulfilled') setAuditLogs(auditData.value);

      const failures = results.filter((result) => result.status === 'rejected');
      if (failures.length > 0) {
        setMessage(`${failures.length} admin panel request(s) failed. Other sections were refreshed.`);
      }
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      if (showBusy) setBusy(false);
    }
  }

  async function upload() {
    if (!file) {
      setMessage('Choose a CSV or TSV file first.');
      return;
    }
    setBusy(true);
    setMessage('');
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('data_type', dataType);
      await apiFetch<UploadItem>('/api/admin/uploads', {
        method: 'POST',
        body: form,
      });
      setFile(null);
      setMessage('Upload completed.');
      await refresh();
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function runImport(uploadId: number) {
    setBusy(true);
    setMessage('');
    try {
      const job = await apiFetch<ImportJob>(`/api/admin/uploads/${uploadId}/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field_mapping: fieldMapping }),
      });
      setMessage(`Import job ${job.id} started. You can continue uploading while it runs.`);
      await refresh();
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function downloadReport(jobId: number, kind: 'log' | 'errors') {
    setMessage('');
    try {
      const res = await fetch(`/api/admin/imports/${jobId}/${kind}`, {
        headers: authHeaders,
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `import_${jobId}_${kind}.txt`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      setMessage(error.message);
    }
  }

  async function loadPreview(uploadId: number) {
    setBusy(true);
    setMessage('');
    try {
      const data = await apiFetch<UploadPreview>(`/api/admin/uploads/${uploadId}/preview`);
      setPreview(data);
      const defaults: Record<string, string> = {};
      for (const field of data.required_fields) defaults[field] = field;
      setFieldMapping(defaults);
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function deleteUpload(uploadItem: UploadItem) {
    const ok = window.confirm(`Delete uploaded file ${uploadItem.original_filename}? Any functional abundance records imported from this upload will also be removed.`);
    if (!ok) return;
    setBusy(true);
    setMessage('');
    try {
      await apiFetch(`/api/admin/uploads/${uploadItem.id}`, { method: 'DELETE' });
      if (preview?.upload_id === uploadItem.id) setPreview(null);
      setMessage('Upload deleted.');
      await refresh();
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveSample() {
    if (!editingSample) return;
    setBusy(true);
    setMessage('');
    try {
      await apiFetch<SampleItem>(`/api/admin/samples/${editingSample.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingSample),
      });
      setMessage(`Sample ${editingSample.sample_id} saved.`);
      setEditingSample(null);
      await refresh();
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function createAdminUser() {
    setBusy(true);
    setMessage('');
    try {
      await apiFetch<AdminUserItem>('/api/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: newAdminUsername, password: newAdminPassword, role: 'admin' }),
      });
      setNewAdminUsername('');
      setNewAdminPassword('');
      setMessage('Admin user created.');
      await refresh();
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function createBackup() {
    setBusy(true);
    setMessage('');
    try {
      const backup = await apiFetch<BackupItem>('/api/admin/backups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: backupLabel }),
      });
      setMessage(`Backup created: ${backup.filename}`);
      await refresh();
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function restoreBackup(backup: BackupItem) {
    const ok = window.confirm(`Restore database from ${backup.filename}? Current database will be replaced after a pre-restore copy is created.`);
    if (!ok) return;
    setBusy(true);
    setMessage('');
    try {
      const restored = await apiFetch<BackupItem>(`/api/admin/backups/${backup.id}/restore`, {
        method: 'POST',
      });
      setMessage(restored.message || 'Database restored.');
      await refresh();
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function downloadBackup(backupId: number) {
    setMessage('');
    try {
      const res = await fetch(`/api/admin/backups/${backupId}/download`, {
        headers: authHeaders,
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `eaam_backup_${backupId}.db`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      setMessage(error.message);
    }
  }

  async function deleteImportData(job: ImportJob) {
    const ok = window.confirm(`Delete data imported by job ${job.id}? This only removes functional abundance records for that upload.`);
    if (!ok) return;
    setBusy(true);
    setMessage('');
    try {
      const deleted = await apiFetch<ImportJob>(`/api/admin/imports/${job.id}/data`, {
        method: 'DELETE',
      });
      setMessage(deleted.message || 'Imported data deleted.');
      await refresh();
    } catch (error: any) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    window.localStorage.removeItem(TOKEN_KEY);
    setToken('');
    setUploads([]);
    setJobs([]);
    setBackups([]);
    setStats(null);
    setSamples([]);
    setUsers([]);
    setAuditLogs([]);
    setPreview(null);
    setMessage('Logged out.');
  }

  function formatBytes(value: number): string {
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
    return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`;
  }

  if (!token) {
    return (
      <div className="max-w-md mx-auto bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-5">
          <Shield className="h-5 w-5 text-indigo-700" />
          <h1 className="text-xl font-semibold">Admin Login</h1>
        </div>
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm text-gray-600">Username</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-sm text-gray-600">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <button
            onClick={login}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            <LogIn className="h-4 w-4" />
            Login
          </button>
          {message && <p className="text-sm text-red-600">{message}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Admin Console</h1>
          <p className="text-sm text-gray-500">Upload template files, run imports, and review reports.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refresh()}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={logout}
            className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
          >
            Logout
          </button>
        </div>
      </div>

      {message && (
        <div className="rounded-md border border-gray-200 bg-white px-4 py-3 text-sm text-gray-700">
          {message}
        </div>
      )}

      <section className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Database className="h-5 w-5 text-indigo-700" />
          <h2 className="text-lg font-semibold">Database Statistics</h2>
        </div>
        {stats ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ['Samples', stats.sample_count],
              ['Taxa', stats.taxon_count],
              ['Taxonomy records', stats.taxonomy_abundance_count],
              ['Functional records', stats.functional_abundance_count],
              ['Functional features', stats.functional_feature_count],
              ['Uploads', stats.upload_count],
              ['Import jobs', stats.import_job_count],
              ['Backups', stats.backup_count],
            ].map(([label, value]) => (
              <div key={label} className="rounded-md border border-gray-200 px-3 py-3">
                <div className="text-xs text-gray-500">{label}</div>
                <div className="mt-1 text-xl font-semibold">{value}</div>
              </div>
            ))}
            <div className="rounded-md border border-gray-200 px-3 py-3 sm:col-span-2 lg:col-span-4">
              <div className="text-xs text-gray-500">Database</div>
              <div className="mt-1 break-all text-sm text-gray-700">{stats.database_path}</div>
              <div className="mt-1 text-sm font-medium">{formatBytes(stats.database_size_bytes)}</div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Statistics are not loaded.</p>
        )}
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">Database Backups</h2>
        <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end mb-5">
          <label className="block">
            <span className="text-sm text-gray-600">Backup label</span>
            <input
              value={backupLabel}
              onChange={(e) => setBackupLabel(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <button
            onClick={createBackup}
            disabled={busy}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            <Database className="h-4 w-4" />
            Create Backup
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-b border-gray-200 text-left text-gray-500">
              <tr>
                <th className="py-2 pr-4">ID</th>
                <th className="py-2 pr-4">Action</th>
                <th className="py-2 pr-4">File</th>
                <th className="py-2 pr-4">Size</th>
                <th className="py-2 pr-4">Created</th>
                <th className="py-2 pr-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {backups.map((backup) => (
                <tr key={backup.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4">{backup.id}</td>
                  <td className="py-2 pr-4">{backup.action}</td>
                  <td className="py-2 pr-4">{backup.filename}</td>
                  <td className="py-2 pr-4">{formatBytes(backup.size_bytes)}</td>
                  <td className="py-2 pr-4">{new Date(backup.created_at).toLocaleString()}</td>
                  <td className="py-2 pr-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => downloadBackup(backup.id)}
                        className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-2 py-1 text-xs"
                      >
                        <Download className="h-3.5 w-3.5" />
                        Download
                      </button>
                      {backup.action === 'backup' && (
                        <button
                          onClick={() => restoreBackup(backup)}
                          disabled={busy}
                          className="inline-flex items-center gap-1 rounded-md border border-amber-300 px-2 py-1 text-xs text-amber-700 disabled:opacity-50"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                          Restore
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {backups.length === 0 && (
                <tr>
                  <td className="py-4 text-gray-500" colSpan={6}>No backups yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">Upload CSV / TSV</h2>
        <div className="grid gap-4 md:grid-cols-[1fr_220px_auto] md:items-end">
          <label className="block">
            <span className="text-sm text-gray-600">File</span>
            <input
              type="file"
              accept=".csv,.tsv,text/csv,text/tab-separated-values"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-sm text-gray-600">Data type</span>
            <select
              value={dataType}
              onChange={(e) => setDataType(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="auto">Auto</option>
              <option value="samples">Samples metadata</option>
              <option value="gene_family">KO gene family</option>
              <option value="pathway">Pathway</option>
            </select>
          </label>
          <button
            onClick={upload}
            disabled={busy}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            <FileUp className="h-4 w-4" />
            Upload
          </button>
        </div>
      </section>

      {preview && (
        <section className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Import Preview</h2>
              <p className="text-sm text-gray-500">{preview.filename} · {preview.data_type}</p>
            </div>
            <button
              onClick={() => runImport(preview.upload_id)}
              disabled={busy}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              Import With Mapping
            </button>
          </div>

          {preview.validation.length > 0 && (
            <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {preview.validation.map((item) => <div key={item}>{item}</div>)}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-3 mb-4">
            {preview.required_fields.map((field) => (
              <label key={field} className="block">
                <span className="text-sm text-gray-600">{field}</span>
                <select
                  value={fieldMapping[field] || field}
                  onChange={(e) => setFieldMapping({ ...fieldMapping, [field]: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  {preview.columns.map((column) => (
                    <option key={column} value={column}>{column || '(empty column)'}</option>
                  ))}
                </select>
              </label>
            ))}
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="border-b border-gray-200 text-left text-gray-500">
                <tr>
                  {preview.columns.slice(0, 8).map((column, index) => (
                    <th key={`${column}-${index}`} className="py-2 pr-4">{column || '(empty)'}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.preview_rows.map((row, index) => (
                  <tr key={index} className="border-b border-gray-100">
                    {preview.columns.slice(0, 8).map((column, colIndex) => (
                      <td key={`${column}-${colIndex}`} className="py-2 pr-4 max-w-[220px] truncate">
                        {row[column]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">Uploaded Files</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-b border-gray-200 text-left text-gray-500">
              <tr>
                <th className="py-2 pr-4">ID</th>
                <th className="py-2 pr-4">File</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">Size</th>
                <th className="py-2 pr-4">Uploaded</th>
                <th className="py-2 pr-4">Action</th>
              </tr>
            </thead>
            <tbody>
              {uploads.map((item) => (
                <tr key={item.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4">{item.id}</td>
                  <td className="py-2 pr-4">{item.original_filename}</td>
                  <td className="py-2 pr-4">{item.data_type}</td>
                  <td className="py-2 pr-4">{item.size_bytes}</td>
                  <td className="py-2 pr-4">{new Date(item.created_at).toLocaleString()}</td>
                  <td className="py-2 pr-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => loadPreview(item.id)}
                        disabled={busy}
                        className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-2 py-1 text-xs"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        Preview
                      </button>
                      <button
                        onClick={() => runImport(item.id)}
                        disabled={busy}
                        className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-2 py-1 text-xs"
                      >
                        <Play className="h-3.5 w-3.5" />
                        Import
                      </button>
                      <button
                        onClick={() => deleteUpload(item)}
                        disabled={busy}
                        className="inline-flex items-center gap-1 rounded-md border border-red-200 px-2 py-1 text-xs text-red-700 disabled:opacity-50"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {uploads.length === 0 && (
                <tr>
                  <td className="py-4 text-gray-500" colSpan={6}>No uploads yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold">Sample Metadata</h2>
            <p className="text-sm text-gray-500">Edit core sample fields used by filters and visualizations.</p>
          </div>
          <div className="flex gap-2">
            <input
              value={sampleQuery}
              onChange={(e) => setSampleQuery(e.target.value)}
              placeholder="Search sample_id"
              className="rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
            <button
              onClick={() => refresh()}
              disabled={busy}
              className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm disabled:opacity-50"
            >
              Search
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-b border-gray-200 text-left text-gray-500">
              <tr>
                <th className="py-2 pr-4">Sample</th>
                <th className="py-2 pr-4">Dynasty</th>
                <th className="py-2 pr-4">Province</th>
                <th className="py-2 pr-4">Region</th>
                <th className="py-2 pr-4">Sex</th>
                <th className="py-2 pr-4">Action</th>
              </tr>
            </thead>
            <tbody>
              {samples.map((sample) => (
                <tr key={sample.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4">{sample.sample_id}</td>
                  <td className="py-2 pr-4">{sample.dynasty}</td>
                  <td className="py-2 pr-4">{sample.province}</td>
                  <td className="py-2 pr-4">{sample.region}</td>
                  <td className="py-2 pr-4">{sample.sex}</td>
                  <td className="py-2 pr-4">
                    <button
                      onClick={() => setEditingSample(sample)}
                      className="rounded-md border border-gray-300 px-2 py-1 text-xs"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
              {samples.length === 0 && (
                <tr>
                  <td className="py-4 text-gray-500" colSpan={6}>No samples found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {editingSample && (
          <div className="mt-5 rounded-md border border-gray-200 p-4">
            <h3 className="text-sm font-semibold mb-3">Editing {editingSample.sample_id}</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                'sample_id',
                'province',
                'region',
                'dynasty',
                'period',
                'sex',
                'subsistence_pattern',
                'site_name',
                'source',
              ].map((field) => (
                <label key={field} className="block">
                  <span className="text-xs text-gray-500">{field}</span>
                  <input
                    value={String((editingSample as any)[field] ?? '')}
                    onChange={(e) => setEditingSample({ ...editingSample, [field]: e.target.value } as SampleItem)}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
              ))}
              {(['estimated_year', 'latitude', 'longitude'] as const).map((field) => (
                <label key={field} className="block">
                  <span className="text-xs text-gray-500">{field}</span>
                  <input
                    type="number"
                    value={(editingSample[field] ?? '') as any}
                    onChange={(e) => setEditingSample({
                      ...editingSample,
                      [field]: e.target.value === '' ? null : Number(e.target.value),
                    })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </label>
              ))}
            </div>
            <div className="mt-4 flex gap-2">
              <button
                onClick={saveSample}
                disabled={busy}
                className="inline-flex items-center gap-2 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                <Save className="h-4 w-4" />
                Save
              </button>
              <button
                onClick={() => setEditingSample(null)}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">Administrators</h2>
        <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end mb-5">
          <label className="block">
            <span className="text-sm text-gray-600">Username</span>
            <input
              value={newAdminUsername}
              onChange={(e) => setNewAdminUsername(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-sm text-gray-600">Password</span>
            <input
              type="password"
              value={newAdminPassword}
              onChange={(e) => setNewAdminPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <button
            onClick={createAdminUser}
            disabled={busy}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            <UserPlus className="h-4 w-4" />
            Add Admin
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {users.map((user) => (
            <span key={user.id} className="rounded-md border border-gray-200 px-3 py-2 text-sm">
              {user.username} · {user.role}
            </span>
          ))}
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">Import Jobs</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-b border-gray-200 text-left text-gray-500">
              <tr>
                <th className="py-2 pr-4">Job</th>
                <th className="py-2 pr-4">Upload</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Message</th>
                <th className="py-2 pr-4">Reports</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4">{job.id}</td>
                  <td className="py-2 pr-4">{job.upload_id}</td>
                  <td className="py-2 pr-4">{job.data_type}</td>
                  <td className="py-2 pr-4">
                    <span className={`rounded px-2 py-1 text-xs ${
                      job.status === 'success'
                        ? 'bg-emerald-50 text-emerald-700'
                        : job.status === 'failed'
                          ? 'bg-red-50 text-red-700'
                          : 'bg-amber-50 text-amber-700'
                    }`}>
                      {job.status}
                    </span>
                  </td>
                  <td className="py-2 pr-4 max-w-md">{job.message}</td>
                  <td className="py-2 pr-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => downloadReport(job.id, 'log')}
                        className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-2 py-1 text-xs"
                      >
                        <Download className="h-3.5 w-3.5" />
                        Log
                      </button>
                      {job.has_error_report && (
                        <button
                          onClick={() => downloadReport(job.id, 'errors')}
                          className="inline-flex items-center gap-1 rounded-md border border-red-200 px-2 py-1 text-xs text-red-700"
                        >
                          <Download className="h-3.5 w-3.5" />
                          Errors
                        </button>
                      )}
                      {['gene_family', 'pathway'].includes(job.data_type) && job.status !== 'deleted' && (
                        <button
                          onClick={() => deleteImportData(job)}
                          disabled={busy}
                          className="inline-flex items-center gap-1 rounded-md border border-red-200 px-2 py-1 text-xs text-red-700 disabled:opacity-50"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete Data
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {jobs.length === 0 && (
                <tr>
                  <td className="py-4 text-gray-500" colSpan={6}>No import jobs yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">Audit Logs</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-b border-gray-200 text-left text-gray-500">
              <tr>
                <th className="py-2 pr-4">Time</th>
                <th className="py-2 pr-4">User</th>
                <th className="py-2 pr-4">Action</th>
                <th className="py-2 pr-4">Target</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Detail</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map((log) => (
                <tr key={log.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4">{new Date(log.created_at).toLocaleString()}</td>
                  <td className="py-2 pr-4">{log.username}</td>
                  <td className="py-2 pr-4">{log.action}</td>
                  <td className="py-2 pr-4">{log.target_type}:{log.target_id}</td>
                  <td className="py-2 pr-4">{log.status}</td>
                  <td className="py-2 pr-4 max-w-md truncate">{log.detail}</td>
                </tr>
              ))}
              {auditLogs.length === 0 && (
                <tr>
                  <td className="py-4 text-gray-500" colSpan={6}>No audit logs yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
