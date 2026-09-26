import type { ApplicationProfile, LearnedAnswer, AutofillState } from '../types';

const DEFAULT_PROFILE: ApplicationProfile = {
  personal: {},
  professional: {},
  education: [],
  workAuthorization: {},
  preferences: {},
  documents: {},
  customAnswers: {},
};

class Storage {
  // ── Profile ──────────────────────────────────────────────────────────────
  async getProfile(): Promise<ApplicationProfile> {
    const data = await chrome.storage.local.get('profile');
    return { ...DEFAULT_PROFILE, ...data.profile };
  }

  async setProfile(profile: ApplicationProfile): Promise<void> {
    await chrome.storage.local.set({ profile });
  }

  async updateProfile(partial: Partial<ApplicationProfile>): Promise<ApplicationProfile> {
    const current = await this.getProfile();
    const updated = {
      ...current,
      ...partial,
      personal: { ...current.personal, ...(partial.personal || {}) },
      professional: { ...current.professional, ...(partial.professional || {}) },
      workAuthorization: { ...current.workAuthorization, ...(partial.workAuthorization || {}) },
      preferences: { ...current.preferences, ...(partial.preferences || {}) },
      documents: { ...current.documents, ...(partial.documents || {}) },
    };
    await this.setProfile(updated);
    return updated;
  }

  // ── Learned Answers ──────────────────────────────────────────────────────
  async getLearnedAnswers(): Promise<LearnedAnswer[]> {
    const data = await chrome.storage.local.get('learnedAnswers');
    return data.learnedAnswers || [];
  }

  async saveLearnedAnswer(answer: Omit<LearnedAnswer, 'id' | 'usedCount' | 'createdAt' | 'updatedAt'>): Promise<LearnedAnswer> {
    const answers = await this.getLearnedAnswers();
    const existing = answers.findIndex(
      a => a.normalizedQuestion === answer.normalizedQuestion &&
           a.scope === answer.scope &&
           (a.company || '') === (answer.company || '')
    );
    const now = new Date().toISOString();
    const newAnswer: LearnedAnswer = {
      ...answer,
      id: existing >= 0 ? answers[existing].id : crypto.randomUUID(),
      usedCount: existing >= 0 ? answers[existing].usedCount : 0,
      createdAt: existing >= 0 ? answers[existing].createdAt : now,
      updatedAt: now,
    };
    if (existing >= 0) {
      answers[existing] = newAnswer;
    } else {
      answers.push(newAnswer);
    }
    await chrome.storage.local.set({ learnedAnswers: answers });
    return newAnswer;
  }

  async incrementAnswerUsage(answerId: string): Promise<void> {
    const answers = await this.getLearnedAnswers();
    const a = answers.find(x => x.id === answerId);
    if (a) {
      a.usedCount++;
      a.updatedAt = new Date().toISOString();
      await chrome.storage.local.set({ learnedAnswers: answers });
    }
  }

  // ── Sessions ─────────────────────────────────────────────────────────────
  async getSessions(): Promise<any[]> {
    const data = await chrome.storage.local.get('sessions');
    return data.sessions || [];
  }

  async saveSession(session: any): Promise<void> {
    const sessions = await this.getSessions();
    sessions.unshift(session);
    if (sessions.length > 50) sessions.length = 50;
    await chrome.storage.local.set({ sessions });
  }

  // ── State ────────────────────────────────────────────────────────────────
  async getState(): Promise<AutofillState> {
    const data = await chrome.storage.local.get('autofillState');
    return data.autofillState || 'idle';
  }

  async setState(state: AutofillState): Promise<void> {
    await chrome.storage.local.set({ autofillState: state });
  }

  // ── Auth ─────────────────────────────────────────────────────────────────
  async getToken(): Promise<string | null> {
    const data = await chrome.storage.local.get('auth_token');
    return data.auth_token || null;
  }

  async setToken(token: string): Promise<void> {
    await chrome.storage.local.set({ auth_token: token });
  }

  // ── Detection Cache ──────────────────────────────────────────────────────
  async getCachedDetection(url: string): Promise<any | null> {
    const data = await chrome.storage.session.get(`detection:${url}`);
    return data[`detection:${url}`] || null;
  }

  async setCachedDetection(url: string, detection: any): Promise<void> {
    await chrome.storage.session.set({ [`detection:${url}`]: detection });
  }
}

export const storage = new Storage();
