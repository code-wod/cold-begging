import type { FormField, ApplicationProfile, FieldSuggestion, NormalizedConcept, MatchSource } from '../types';
import { normalizeField } from './normalizer';
import { storage } from '../storage/store';
import { api } from '../api/client';

// ── Confidence thresholds ───────────────────────────────────────────────────
const CONFIDENCE_AUTO = 0.90;   // auto-fill without review
const CONFIDENCE_REVIEW = 0.70; // show in review
const CONFIDENCE_SUGGEST = 0.50; // suggestion only

// ── Value lookup from profile ───────────────────────────────────────────────
function getProfileValue(profile: ApplicationProfile, concept: NormalizedConcept): string | undefined {
  switch (concept) {
    case 'firstName': return profile.personal.firstName;
    case 'lastName': return profile.personal.lastName;
    case 'fullName': return profile.personal.fullName || [profile.personal.firstName, profile.personal.lastName].filter(Boolean).join(' ');
    case 'email': return profile.personal.email;
    case 'phone': return profile.personal.phone;
    case 'street': return profile.personal.address?.street;
    case 'city': return profile.personal.address?.city;
    case 'state': return profile.personal.address?.state;
    case 'country': return profile.personal.address?.country;
    case 'postalCode': return profile.personal.address?.postalCode;
    case 'linkedin': return profile.professional.linkedin;
    case 'github': return profile.professional.github;
    case 'portfolio': return profile.professional.portfolio;
    case 'currentTitle': return profile.professional.currentTitle;
    case 'yearsExperience': return profile.professional.yearsOfExperience;
    case 'currentCompany': return profile.professional.currentCompany;
    case 'salary': return profile.preferences.salaryExpectation;
    case 'workAuthorization': return profile.workAuthorization.authorizedToWork ? 'Yes' : undefined;
    case 'requiresSponsorship': return profile.workAuthorization.requiresSponsorship ? 'Yes' : 'No';
    case 'willingToRelocate': return profile.workAuthorization.willingToRelocate ? 'Yes' : 'No';
    case 'noticePeriod': return profile.preferences.noticePeriod;
    case 'education': return profile.education?.[0]?.degree;
    case 'coverLetter': return profile.documents.coverLetterPath;
    default: return undefined;
  }
}

// ── Calculate confidence ────────────────────────────────────────────────────
function calculateConfidence(
  field: FormField,
  concept: NormalizedConcept,
  source: MatchSource,
  hasValue: boolean,
  isRequired: boolean
): number {
  if (!hasValue) return 0;

  let confidence = 0;

  // Base confidence from match source
  switch (source) {
    case 'exact': confidence = 0.95; break;
    case 'synonym': confidence = 0.85; break;
    case 'autocomplete': confidence = 0.92; break;
    case 'learned': confidence = 0.90; break;
    case 'semantic': confidence = 0.75; break;
    case 'ai': confidence = 0.70; break;
  }

  // Adjust for field context
  if (field.label && concept !== 'unknown') confidence += 0.03;
  if (field.autocomplete) confidence += 0.02;
  if (field.required) confidence += 0.01;

  // Penalize for missing context
  if (!field.label && !field.name && !field.ariaLabel) confidence -= 0.05;

  return Math.min(0.99, Math.max(0, confidence));
}

// ── Main matching function ──────────────────────────────────────────────────
export async function matchFields(
  fields: FormField[],
  profile: ApplicationProfile,
  learnedAnswers?: Map<string, string>
): Promise<FieldSuggestion[]> {
  const suggestions: FieldSuggestion[] = [];

  // Load learned answers if not provided
  if (!learnedAnswers) {
    const answers = await storage.getLearnedAnswers();
    learnedAnswers = new Map(answers.map(a => [a.normalizedQuestion, a.answer]));
  }

  for (const field of fields) {
    // Skip non-fillable fields (file inputs, radio are handled separately)
    if (field.inputType === 'file' || field.elementType === 'radio') continue;
    if (field.inputType === 'hidden' || field.inputType === 'submit') continue;

    // Step 1: Normalize to concept
    const concept = normalizeField({
      label: field.label,
      name: field.name,
      placeholder: field.placeholder,
      ariaLabel: field.ariaLabel,
      autocomplete: field.autocomplete,
      surroundingText: field.surroundingText,
    });

    // Step 2: Try to find value from profile
    let value = getProfileValue(profile, concept);
    let source: MatchSource = 'exact';
    let confidence = calculateConfidence(field, concept, source, !!value, field.required);

    // Step 3: Try learned answers if no profile value
    if (!value && concept !== 'unknown') {
      const questionKey = (field.label || field.name || field.placeholder || '').toLowerCase().replace(/[:*?]+$/, '').trim();
      if (questionKey && learnedAnswers?.has(questionKey)) {
        value = learnedAnswers.get(questionKey);
        source = 'learned';
        confidence = calculateConfidence(field, concept, source, true, field.required);
      }
    }

    // Step 4: For unknown concepts, try label-based learned answers
    if (!value && concept === 'unknown') {
      const questionKey = (field.label || field.name || field.placeholder || '').toLowerCase().replace(/[:*?]+$/, '').trim();
      if (questionKey && learnedAnswers?.has(questionKey)) {
        value = learnedAnswers.get(questionKey);
        source = 'learned';
        confidence = calculateConfidence(field, 'unknown', source, true, field.required);
      }
    }

    // Step 5: Handle select/combobox options
    if (!value && field.options && field.options.length > 0) {
      const matched = matchSelectOption(field.options, concept, profile);
      if (matched) {
        value = matched.value;
        source = 'exact';
        confidence = calculateConfidence(field, concept, source, true, field.required);
      }
    }

    // Step 6: Handle yes/no fields
    if (!value && (concept === 'workAuthorization' || concept === 'requiresSponsorship' || concept === 'willingToRelocate')) {
      value = profile.workAuthorization.authorizedToWork ? 'Yes' : undefined;
      source = 'profile';
      confidence = calculateConfidence(field, concept, source, !!value, field.required);
    }

    // Determine if review is required
    const requiresReview = confidence < CONFIDENCE_AUTO || concept === 'unknown';

    suggestions.push({
      fieldId: field.id,
      profilePath: concept,
      value,
      confidence,
      source,
      requiresReview,
    });
  }

  return suggestions;
}

// ── Match select options ────────────────────────────────────────────────────
function matchSelectOption(
  options: { value: string; label: string }[],
  concept: NormalizedConcept,
  profile: ApplicationProfile
): { value: string; label: string } | undefined {
  const optionLabels = options.map(o => o.label.toLowerCase());

  // For country fields
  if (concept === 'country' && profile.personal.address?.country) {
    const country = profile.personal.address.country.toLowerCase();
    const match = options.find(o =>
      o.label.toLowerCase() === country ||
      o.value.toLowerCase() === country
    );
    if (match) return match;
  }

  // For state fields
  if (concept === 'state' && profile.personal.address?.state) {
    const state = profile.personal.address.state.toLowerCase();
    const match = options.find(o =>
      o.label.toLowerCase() === state ||
      o.value.toLowerCase() === state
    );
    if (match) return match;
  }

  // For yes/no fields
  if (concept === 'requiresSponsorship' || concept === 'willingToRelocate') {
    const wantsYes = concept === 'willingToRelocate'
      ? profile.workAuthorization.willingToRelocate
      : !profile.workAuthorization.requiresSponsorship;

    const yesOption = options.find(o => /^(yes|true|1)$/i.test(o.label) || /^(yes|true|1)$/i.test(o.value));
    const noOption = options.find(o => /^(no|false|0)$/i.test(o.label) || /^(no|false|0)$/i.test(o.value));

    return wantsYes ? yesOption : noOption;
  }

  // For work authorization
  if (concept === 'workAuthorization') {
    const authValue = profile.workAuthorization.authorizedToWork ? 'yes' : 'no';
    const match = options.find(o =>
      o.label.toLowerCase().includes(authValue) ||
      o.value.toLowerCase().includes(authValue)
    );
    if (match) return match;
  }

  // Generic: look for best match by label similarity
  const value = getProfileValue(profile, concept);
  if (value) {
    const valueLower = value.toLowerCase();
    const match = options.find(o =>
      o.label.toLowerCase() === valueLower ||
      o.value.toLowerCase() === valueLower ||
      o.label.toLowerCase().includes(valueLower) ||
      valueLower.includes(o.label.toLowerCase())
    );
    if (match) return match;
  }

  return undefined;
}

// ── AI fallback for unknown fields ──────────────────────────────────────────
export async function aiMapFields(
  fields: { label?: string; name?: string; placeholder?: string; ariaLabel?: string; context?: string }[]
): Promise<Record<string, { concept: string; confidence: number }>> {
  try {
    return await api.semanticMap(fields);
  } catch {
    return {};
  }
}

// ── Get confidence level label ──────────────────────────────────────────────
export function getConfidenceLevel(confidence: number): 'auto' | 'review' | 'suggest' | 'skip' {
  if (confidence >= CONFIDENCE_AUTO) return 'auto';
  if (confidence >= CONFIDENCE_REVIEW) return 'review';
  if (confidence >= CONFIDENCE_SUGGEST) return 'suggest';
  return 'skip';
}
