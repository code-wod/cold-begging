import type { NormalizedConcept } from '../types';

interface SynonymGroup {
  concept: NormalizedConcept;
  keywords: string[];
}

const SYNONYM_MAP: SynonymGroup[] = [
  { concept: 'firstName', keywords: ['first name', 'first_name', 'firstname', 'given name', 'given_name', 'prenom', 'vorname'] },
  { concept: 'lastName', keywords: ['last name', 'last_name', 'lastname', 'surname', 'family name', 'family_name', 'familienname', 'nachname'] },
  { concept: 'fullName', keywords: ['full name', 'full_name', 'fullname', 'name', 'your name', 'candidate name'] },
  { concept: 'email', keywords: ['email', 'e-mail', 'email address', 'electronic mail', 'mail', 'courriel'] },
  { concept: 'phone', keywords: ['phone', 'telephone', 'mobile', 'cell', 'cell phone', 'phone number', 'telephone number', 'mobile number', 'contact number', 'tel', 'phoneNumber'] },
  { concept: 'street', keywords: ['street', 'address', 'street address', 'address line 1', 'address line', 'addressline', 'strasse', 'straße'] },
  { concept: 'city', keywords: ['city', 'town', 'locality', 'ort', 'stadt'] },
  { concept: 'state', keywords: ['state', 'province', 'region', 'county', 'bundesland', 'estado', 'province/state'] },
  { concept: 'country', keywords: ['country', 'nation', 'land', 'pays', 'pais'] },
  { concept: 'postalCode', keywords: ['postal code', 'zip code', 'zipcode', 'zip', 'postcode', 'postleitzahl', 'plz'] },
  { concept: 'linkedin', keywords: ['linkedin', 'linkedin url', 'linkedin profile', 'linkedin profile url'] },
  { concept: 'github', keywords: ['github', 'github url', 'github profile', 'github profile url'] },
  { concept: 'portfolio', keywords: ['portfolio', 'website', 'personal website', 'portfolio url', 'website url', 'url', 'homepage', 'blog'] },
  { concept: 'currentTitle', keywords: ['current title', 'current position', 'job title', 'title', 'position', 'current role', 'designation'] },
  { concept: 'yearsExperience', keywords: ['years of experience', 'experience', 'years experience', 'total experience', 'work experience', 'yoe'] },
  { concept: 'currentCompany', keywords: ['current company', 'company', 'employer', 'current employer', 'organization', 'organisation'] },
  { concept: 'salary', keywords: ['salary', 'compensation', 'pay', 'expected salary', 'salary expectation', 'desired salary', 'pay expectation'] },
  { concept: 'salaryMin', keywords: ['minimum salary', 'salary minimum', 'minimum pay', 'min salary'] },
  { concept: 'salaryMax', keywords: ['maximum salary', 'salary maximum', 'maximum pay', 'max salary'] },
  { concept: 'workAuthorization', keywords: ['work authorization', 'authorized to work', 'work permit', 'legally authorized', 'right to work', 'work authorization status'] },
  { concept: 'requiresSponsorship', keywords: ['sponsorship', 'require sponsorship', 'visa sponsorship', 'require visa', 'h1b', 'h-1b', 'visa status', 'immigration'] },
  { concept: 'willingToRelocate', keywords: ['relocate', 'willing to relocate', 'relocation', 'mobility'] },
  { concept: 'noticePeriod', keywords: ['notice period', 'notice', 'available from', 'start date', 'when can you start', 'availability'] },
  { concept: 'education', keywords: ['education', 'degree', 'university', 'school', 'college', 'academic', 'qualification'] },
  { concept: 'experience', keywords: ['experience', 'work experience', 'professional experience', 'employment history'] },
  { concept: 'coverLetter', keywords: ['cover letter', 'cover_letter', 'coverletter', 'motivation letter', 'anschreiben'] },
  { concept: 'gender', keywords: ['gender', 'sex', 'geschlecht'] },
  { concept: 'ethnicity', keywords: ['ethnicity', 'ethnic', 'race', 'racial', 'demographic'] },
  { concept: 'veteranStatus', keywords: ['veteran', 'veteran status', 'military', 'armed forces'] },
  { concept: 'disabilityStatus', keywords: ['disability', 'disability status', 'disabled', 'handicap'] },
  { concept: 'pronouns', keywords: ['pronouns', 'preferred pronouns', 'gender pronouns'] },
];

const AUTOCOMPLETE_MAP: Record<string, NormalizedConcept> = {
  'given-name': 'firstName',
  'family-name': 'lastName',
  'name': 'fullName',
  'email': 'email',
  'tel': 'phone',
  'street-address': 'street',
  'address-line1': 'street',
  'address-level2': 'city',
  'address-level1': 'state',
  'country': 'country',
  'postal-code': 'postalCode',
  'url': 'portfolio',
};

const PLACEHOLDER_MAP: Record<string, NormalizedConcept> = {
  'john.doe@example.com': 'email',
  'john doe': 'fullName',
  'john': 'firstName',
  'doe': 'lastName',
  '+1 (555) 123-4567': 'phone',
  '123 main st': 'street',
  'san francisco': 'city',
  'linkedin.com/in/': 'linkedin',
  'github.com/': 'github',
  'https://': 'portfolio',
  'your answer': 'unknown',
  'select...': 'unknown',
  'choose one': 'unknown',
};

export function normalizeField(field: {
  label?: string;
  name?: string;
  placeholder?: string;
  ariaLabel?: string;
  autocomplete?: string;
  surroundingText?: string;
}): NormalizedConcept {
  // 1. Check autocomplete attribute (highest confidence)
  if (field.autocomplete) {
    const mapped = AUTOCOMPLETE_MAP[field.autocomplete.toLowerCase()];
    if (mapped) return mapped;
  }

  // 2. Check name attribute
  if (field.name) {
    const nameNormalized = field.name.toLowerCase().replace(/[-_\s]+/g, ' ').trim();
    for (const group of SYNONYM_MAP) {
      if (group.keywords.some(k => nameNormalized.includes(k))) return group.concept;
    }
  }

  // 3. Check label
  if (field.label) {
    const labelNormalized = field.label.toLowerCase().replace(/[-_\s]+/g, ' ').trim();
    // Remove trailing colons, asterisks, required markers
    const cleaned = labelNormalized.replace(/[:*]+$/, '').replace(/\s*\(required\)\s*$/, '').trim();
    for (const group of SYNONYM_MAP) {
      if (group.keywords.some(k => cleaned.includes(k))) return group.concept;
    }
  }

  // 4. Check aria-label
  if (field.ariaLabel) {
    const ariaNormalized = field.ariaLabel.toLowerCase().replace(/[-_\s]+/g, ' ').trim();
    for (const group of SYNONYM_MAP) {
      if (group.keywords.some(k => ariaNormalized.includes(k))) return group.concept;
    }
  }

  // 5. Check placeholder
  if (field.placeholder) {
    const placeholderLower = field.placeholder.toLowerCase().trim();
    for (const [pattern, concept] of Object.entries(PLACEHOLDER_MAP)) {
      if (placeholderLower.includes(pattern.toLowerCase())) return concept;
    }
    const placeholderNormalized = placeholderLower.replace(/[-_\s]+/g, ' ');
    for (const group of SYNONYM_MAP) {
      if (group.keywords.some(k => placeholderNormalized.includes(k))) return group.concept;
    }
  }

  // 6. Check surrounding text
  if (field.surroundingText) {
    const surroundNormalized = field.surroundingText.toLowerCase().replace(/[-_\s]+/g, ' ').trim();
    for (const group of SYNONYM_MAP) {
      if (group.keywords.some(k => surroundNormalized.includes(k))) return group.concept;
    }
  }

  return 'unknown';
}

export function normalizeFieldName(name: string): NormalizedConcept {
  return normalizeField({ name });
}
