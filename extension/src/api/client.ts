import type { ApplicationProfile, LearnedAnswer, FieldSuggestion } from '../types';

const DEFAULT_API_BASE = 'http://localhost:8000/api';

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor() {
    this.baseUrl = DEFAULT_API_BASE;
  }

  async init(): Promise<void> {
    const stored = await chrome.storage.local.get('auth_token');
    this.token = stored.auth_token || null;
  }

  setToken(token: string) {
    this.token = token;
    chrome.storage.local.set({ auth_token: token });
  }

  clearToken() {
    this.token = null;
    chrome.storage.local.remove('auth_token');
  }

  isAuthenticated(): boolean {
    return !!this.token;
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = { 'Content-Type': 'application/json' };
    if (this.token) h['Authorization'] = `Bearer ${this.token}`;
    return h;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const res = await fetch(url, {
      ...options,
      headers: { ...this.headers(), ...(options.headers as Record<string, string> || {}) },
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, body.detail || 'Request failed');
    }
    return res.json();
  }

  // ── Auth ────────────────────────────────────────────────────────────────
  async login(email: string, password: string): Promise<{ access_token: string; user: any }> {
    const data = await this.request<any>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async getMe(): Promise<any> {
    return this.request<any>('/auth/me');
  }

  // ── Profile ─────────────────────────────────────────────────────────────
  async getProfile(): Promise<ApplicationProfile> {
    return this.request<ApplicationProfile>('/extension/profile');
  }

  async updateProfile(profile: Partial<ApplicationProfile>): Promise<ApplicationProfile> {
    return this.request<ApplicationProfile>('/extension/profile', {
      method: 'PUT',
      body: JSON.stringify(profile),
    });
  }

  // ── Learned Answers ─────────────────────────────────────────────────────
  async getLearnedAnswers(): Promise<LearnedAnswer[]> {
    return this.request<LearnedAnswer[]>('/extension/learned-answers');
  }

  async saveLearnedAnswer(answer: {
    question: string;
    answer: string;
    scope?: string;
    company?: string;
    job_title?: string;
  }): Promise<LearnedAnswer> {
    return this.request<LearnedAnswer>('/extension/learned-answers', {
      method: 'POST',
      body: JSON.stringify(answer),
    });
  }

  // ── AI Semantic Mapping ─────────────────────────────────────────────────
  async semanticMap(fields: { label?: string; name?: string; placeholder?: string; ariaLabel?: string; context?: string }[]): Promise<Record<string, { concept: string; confidence: number }>> {
    return this.request<Record<string, { concept: string; confidence: number }>>('/extension/semantic-map', {
      method: 'POST',
      body: JSON.stringify({ fields }),
    });
  }

  // ── Analysis ────────────────────────────────────────────────────────────
  async analyzePage(url: string, fields: any[]): Promise<{ suggestions: FieldSuggestion[] }> {
    return this.request<{ suggestions: FieldSuggestion[] }>('/extension/analyze', {
      method: 'POST',
      body: JSON.stringify({ url, fields }),
    });
  }

  // ── Sessions ────────────────────────────────────────────────────────────
  async saveSession(session: {
    url: string;
    company?: string;
    job_title?: string;
    platform?: string;
    fields_detected?: number;
    fields_filled?: number;
    duration_seconds?: number;
  }): Promise<void> {
    await this.request('/extension/sessions', {
      method: 'POST',
      body: JSON.stringify(session),
    });
  }

  async getSessions(limit?: number): Promise<any[]> {
    const q = limit ? `?limit=${limit}` : '';
    return this.request<any[]>(`/extension/sessions${q}`);
  }

  // ── Documents ───────────────────────────────────────────────────────────
  async uploadDocument(file: File, type: 'resume' | 'cover_letter'): Promise<{ path: string; name: string }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);

    const url = `${this.baseUrl}/extension/documents`;
    const res = await fetch(url, {
      method: 'POST',
      headers: this.token ? { 'Authorization': `Bearer ${this.token}` } : {},
      body: formData,
    });
    if (!res.ok) throw new ApiError(res.status, 'Upload failed');
    return res.json();
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export const api = new ApiClient();
