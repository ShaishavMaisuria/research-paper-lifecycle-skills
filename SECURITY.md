# Security Policy

## Supported versions

Security fixes apply to the current `main` branch of this repository.

## Reporting a vulnerability

Please do not open a public issue for security reports.

Use GitHub private vulnerability reporting if it is enabled for the repository.
If it is not available, contact the maintainer privately through GitHub before
sharing sensitive details.

Useful reports include:

- A short description of the issue and impact.
- Steps to reproduce.
- Affected files, skills, or scripts.
- Any logs or proof-of-concept details that do not expose secrets.
- Suggested mitigations, if you have them.

## Scope

In scope:

- Scripts that could expose local files, credentials, drafts, or unpublished
  research material.
- Workflows that could leak repository secrets or publish unintended artifacts.
- Install or packaging behavior that could execute unexpected code.
- Prompt or skill behavior that could encourage unsafe handling of private
  research data.

Out of scope:

- Reports about third-party scholarly APIs unless the issue is caused by this
  package's code.
- Social engineering, spam, denial-of-service, or scanner-only reports without
  a concrete impact.
- Claims that require redistributing copyrighted paper content to reproduce.

## Handling expectations

The maintainer will acknowledge valid reports when possible, investigate the
impact, and publish a fix or mitigation before encouraging public disclosure.
