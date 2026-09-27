---
title: How the pipeline works
date: 2026-09-24
---

Each push to the `main` branch on GitHub triggers a webhook, and Jenkins runs these stages on the EC2 server:

| Stage | What happens |
|-------|--------------|
| Checkout | Jenkins pulls the latest commit from GitHub |
| Set up Python | A virtual environment is created and dependencies installed |
| Lint | `flake8` checks the code style |
| Test | `pytest` runs the unit tests and reports coverage |
| Build site | MarkPress converts `content/` into HTML in `public/` |
| Deploy | The new site is copied into the folder Nginx serves |
| Smoke test | Jenkins fetches the live page and checks the build number |

If any stage fails, the pipeline stops and the live site keeps serving the last good build.
