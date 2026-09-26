// ── Platform Detection ──────────────────────────────────────────────────────
export type Platform =
  | 'greenhouse'
  | 'workday'
  | 'lever'
  | 'ashby'
  | 'smartrecruiters'
  | 'generic'
  | 'unknown';

// ── Application Detection ───────────────────────────────────────────────────
export interface ApplicationDetectionResult {
  isApplicationPage: boolean;
  confidence: number;
  platform: Platform;
  jobTitle?: string;
  company?: string;
}

// ── Form Field ──────────────────────────────────────────────────────────────
export type FieldType =
  | 'input'
  | 'textarea'
  | 'select'
  | 'checkbox'
  | 'radio'
  | 'combobox'
  | 'custom';

export type InputType =
  | 'text'
  | 'email'
  | 'tel'
  | 'number'
  | 'date'
  | 'url'
  | 'password'
  | 'file'
  | 'hidden'
  | 'checkbox'
  | 'radio'
  | string;

export interface FormField {
  id: string;
  elementType: FieldType;
  inputType?: InputType;
  label?: string;
  name?: string;
  placeholder?: string;
  ariaLabel?: string;
  autocomplete?: string;
  options?: { value: string; label: string }[];
  section?: string;
  surroundingText?: string;
  selector: string;
  required: boolean;
  currentValue: string;
  pageContext?: string;
  index: number;
}

// ── Normalized Field Concept ────────────────────────────────────────────────
export type NormalizedConcept =
  | 'firstName'
  | 'lastName'
  | 'fullName'
  | 'email'
  | 'phone'
  | 'street'
  | 'city'
  | 'state'
  | 'country'
  | 'postalCode'
  | 'linkedin'
  | 'github'
  | 'portfolio'
  | 'currentTitle'
  | 'yearsExperience'
  | 'currentCompany'
  | 'salary'
  | 'salaryMin'
  | 'salaryMax'
  | 'workAuthorization'
  | 'requiresSponsorship'
  | 'willingToRelocate'
  | 'noticePeriod'
  | 'education'
  | 'experience'
  | 'coverLetter'
  | 'gender'
  | 'ethnicity'
  | 'veteranStatus'
  | 'disabilityStatus'
  | 'pronouns'
  | 'unknown';

// ── Field Suggestion ────────────────────────────────────────────────────────
export type MatchSource =
  | 'exact'
  | 'synonym'
  | 'autocomplete'
  | 'learned'
  | 'semantic'
  | 'ai'
  | 'profile';

export interface FieldSuggestion {
  fieldId: string;
  profilePath?: string;
  value?: string;
  confidence: number;
  source: MatchSource;
  requiresReview: boolean;
}

// ── Application Profile ─────────────────────────────────────────────────────
export interface ApplicationProfile {
  personal: {
    firstName?: string;
    middleName?: string;
    lastName?: string;
    fullName?: string;
    email?: string;
    phone?: string;
    address?: {
      street?: string;
      city?: string;
      state?: string;
      country?: string;
      postalCode?: string;
    };
  };
  professional: {
    currentTitle?: string;
    yearsOfExperience?: string;
    skills?: string[];
    linkedin?: string;
    github?: string;
    portfolio?: string;
    currentCompany?: string;
  };
  education: {
    degree?: string;
    field?: string;
    school?: string;
    graduationYear?: string;
  }[];
  workAuthorization: {
    authorizedToWork?: boolean;
    requiresSponsorship?: boolean;
    willingToRelocate?: boolean;
  };
  preferences: {
    remotePreference?: string;
    noticePeriod?: string;
    salaryExpectation?: string;
  };
  documents: {
    resumePath?: string;
    resumeName?: string;
    coverLetterPath?: string;
  };
  customAnswers: Record<string, string>;
}

// ── Learned Answer ──────────────────────────────────────────────────────────
export interface LearnedAnswer {
  id: string;
  question: string;
  normalizedQuestion: string;
  answer: string;
  answerType: string;
  scope: 'global' | 'company' | 'job' | 'session';
  source: 'user' | 'profile' | 'ai' | 'imported';
  confidence: number;
  userConfirmed: boolean;
  usedCount: number;
  company?: string;
  jobTitle?: string;
  createdAt: string;
  updatedAt: string;
}

// ── Autofill Session ────────────────────────────────────────────────────────
export interface AutofillSession {
  id: string;
  url: string;
  platform?: string;
  company?: string;
  jobTitle?: string;
  detectedFields: FormField[];
  suggestions: FieldSuggestion[];
  filledFields: string[];
  skippedFields: string[];
  reviewRequiredFields: string[];
  startedAt: string;
  completedAt?: string;
}

// ── Extension State ─────────────────────────────────────────────────────────
export type AutofillState =
  | 'idle'
  | 'application_detected'
  | 'analyzing'
  | 'ready'
  | 'review_required'
  | 'filling'
  | 'completed'
  | 'login_required'
  | 'captcha_required'
  | 'error';

// ── Messages ────────────────────────────────────────────────────────────────
export type ContentToBackground =
  | { type: 'DETECT_APPLICATION' }
  | { type: 'EXTRACT_FIELDS' }
  | { type: 'FILL_FIELDS'; fields: { selector: string; value: string }[] }
  | { type: 'GET_STATE' }
  | { type: 'CLICK_NEXT' };

export type BackgroundToContent =
  | { type: 'APPLICATION_DETECTED'; result: ApplicationDetectionResult }
  | { type: 'FIELDS_EXTRACTED'; fields: FormField[] }
  | { type: 'FIELDS_FILLED'; results: { fieldId: string; success: boolean }[] }
  | { type: 'STATE_UPDATE'; state: AutofillState };

export type SidePanelMessage =
  | { type: 'INIT'; profile: ApplicationProfile }
  | { type: 'ANALYZE'; url: string }
  | { type: 'AUTO_FILL'; suggestions: FieldSuggestion[] }
  | { type: 'UPDATE_SUGGESTION'; fieldId: string; value: string }
  | { type: 'REJECT_SUGGESTION'; fieldId: string }
  | { type: 'SAVE_ANSWER'; question: string; answer: string; scope: string }
  | { type: 'GET_PROFILE' }
  | { type: 'UPDATE_PROFILE'; profile: Partial<ApplicationProfile> };
