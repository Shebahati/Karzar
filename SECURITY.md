# Security Policy

## Supported versions

Security fixes are applied on the `main` branch of [Shebahati/Karzar](https://github.com/Shebahati/Karzar).

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email the maintainer via GitHub: [@Shebahati](https://github.com/Shebahati) (use a private channel / security advisory when possible).

Include:
- Affected component (API, Storefront, Admin, deploy)
- Steps to reproduce
- Impact assessment
- Any suggested fix

We aim to acknowledge reports within 7 days.

## Secrets

Never commit `.env`, `.env.local`, `.deploy-secrets`, private keys, or production credentials.
See [docs/COLLABORATOR_DEPLOY.md](docs/COLLABORATOR_DEPLOY.md).
