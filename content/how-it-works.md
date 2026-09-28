---
title: How the pipeline works
date: 2026-09-24
---

Each push to the `main` branch on GitHub starts a GitHub Actions workflow, which runs these steps on GitHub's own servers:

| Stage | What happens |
|-------|--------------|
| Checkout | The workflow fetches the pushed commit |
| Set up Python | Python and the dependencies are installed |
| Lint | `flake8` checks the code style |
| Test | `pytest` runs the unit tests and reports coverage |
| Build site | MarkPress converts `content/` into HTML in `public/` |
| Deploy | The site is published to GitHub Pages |
| Smoke test | The workflow fetches the live page and checks the build number |

If any stage fails, the workflow stops and the live site keeps serving the last good build.
