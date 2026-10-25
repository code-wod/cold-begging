
# Cold Begging: Open-Source Issue Resolution and Pull Request

## Domain / Role

Software Engineering — Open-source contribution, UI improvement, and bug fixing. I will act as a software engineer resolving existing issues in my Cold Begging GitHub repository. I will investigate reported problems, implement focused fixes in VS Code, verify the changes, and submit a pull request for review.

## Goal

Resolve two existing issues in the Cold Begging project: improve the visual appearance of the New Campaign button by making it green, and fix the missing subject line in personalized emails. I will inspect the relevant frontend and backend code, identify the root cause of each issue, implement the smallest appropriate changes, and verify the results through relevant tests or manual checks. I will create a pull request from my secondary GitHub account's fork targeting the original `code-wod/cold-begging` repository's `main` branch. The goal is to deliver reviewable, verified fixes without introducing unrelated changes.

## Starting Materials

- Original repository: https://github.com/code-wod/cold-begging
- Issue #11: Make the New Campaign Button Green.
- Issue #10: Subject missing from the personalized email.
- Existing frontend and backend source code.
- Relevant styling files, email-generation logic, configuration, and tests.
- Primary GitHub account for issue creation and maintainer review.
- Secondary GitHub account for contributing changes through a fork and pull request.
- VS Code and the local development environment.

## Steps and Applications

### 1. Inspect the Issues and Repository
**Apps:** Safari (GitHub)

Review issues #10 and #11, their descriptions, and any screenshots. Inspect the repository structure and identify the relevant frontend component and email-generation code. Confirm the intended behavior for both issues before making changes.

### 2. Investigate the Root Causes
**App:** VS Code

Locate the New Campaign button and inspect its existing styles and design conventions. Trace the personalized email generation flow and inspect the subject-selection logic, including the `subject_map` and the code that passes the subject into the generated email. Determine why the subject is missing instead of assuming the provided snippet is the complete cause.

### 3. Set Up the Contribution Branch
**Apps:** Safari (GitHub), VS Code

Using the secondary GitHub account, fork the original repository and clone the fork locally. Create a dedicated branch for the fixes. Confirm the branch is based on the latest appropriate version of the original repository's default branch.

### 4. Fix the New Campaign Button
**App:** VS Code

Update the button styling to use a suitable green consistent with the application's design. Preserve the existing layout, accessibility, hover and focus states, and responsive behavior. Avoid unrelated UI changes.

### 5. Fix the Personalized Email Subject
**App:** VS Code

Trace the subject from selection through email generation and delivery. Correct the root cause so that personalized emails receive the intended subject line. Preserve the existing personalization strategies and ensure that subject generation works correctly for the supported modes. Add or update tests where appropriate.

### 6. Verify Both Fixes
**Apps:** VS Code, browser

Run relevant tests and build checks. Start the application if the environment supports it. Verify the New Campaign button's appearance in the dashboard and confirm that personalized emails contain the expected subject. Review logs and error output where applicable. Inspect the complete Git diff and ensure that only changes related to the two issues are included.

### 7. Commit and Submit the Pull Request
**Apps:** VS Code, Safari (GitHub)

Commit the changes with a descriptive message and push the branch to the secondary account's fork. Open a pull request targeting `code-wod/cold-begging:main`. Link issues #10 and #11, summarize each root cause and fix, and document the verification performed.

### 8. Final Review
**App:** Safari (GitHub)

Review the pull request title, description, changed files, and diff. Confirm that both fixes are represented accurately and that no unrelated changes are included. Switch to the primary maintainer account to review the contribution. Leave the pull request unmerged unless the task requirements explicitly require merging.

## Deliverables

1. A focused code change addressing the New Campaign button's visual styling.
2. A focused code change fixing the missing personalized email subject.
3. Relevant test updates or documented verification results.
4. A pull request from the secondary account's fork targeting the original repository's `main` branch.
5. A clear pull request description linking issues #10 and #11, explaining the root causes, changes, and verification.
6. A clean, reviewable diff containing only the intended changes.

The final deliverable is a verifiable pull request ready for maintainer review. No unrelated refactoring or documentation changes will be included, and the pull request will remain unmerged unless required by the task instructions.
