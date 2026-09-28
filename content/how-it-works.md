---
title: How the pipeline works
date: 2026-09-24
---

Each push to the `main` branch on GitHub starts a GitHub Actions workflow that checks the change. Render deploys the site only after every check passes.

| Stage | Where | What happens |
|-------|-------|--------------|
| Lint | GitHub Actions | `flake8` checks the code style |
| Test | GitHub Actions | `pytest` runs the unit tests and reports coverage |
| Build check | GitHub Actions | MarkPress builds the site to prove it works |
| Build | Render | Render installs the dependencies and runs MarkPress |
| Deploy | Render | The new site goes live on Render's global CDN |

If any check fails, Render skips the deploy and the live site keeps serving the last good version.
