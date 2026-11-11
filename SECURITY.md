# Security Policy

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's
[private vulnerability reporting](../../security/advisories/new) for this repository,
or contact the maintainer, Ishan Chakraborty, directly.

## Secrets

LinkedIn credentials (`LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`) must be supplied
through environment variables and never committed. `.env*` files are git-ignored.

