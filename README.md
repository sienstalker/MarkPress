# MarkPress

Markdown-to-website generator with CI/CD.

MarkPress converts a folder of Markdown files into a static website. Every push to GitHub triggers a GitHub Actions workflow that lints the code, runs the tests, builds the site and publishes it to GitHub Pages. The footer of every page shows the workflow run number and commit that produced it.

**Live site:** https://sienstalker.github.io/MarkPress/

```
 git push ──► GitHub ──► GitHub Actions (GitHub-hosted runner)
                          │
                          ├─ job: test    lint (flake8) ► test (pytest)
                          ├─ job: build   python -m markpress ► upload Pages artifact
                          └─ job: deploy  publish to GitHub Pages ► smoke test
                                                    │
                          visitors ◄── GitHub Pages (HTTPS, global CDN)
```

No servers to manage: the pipeline runs on GitHub's machines, and the site is hosted by GitHub Pages.

## Project structure

```
markpress/
├── .github/workflows/
│   └── ci-cd.yml           the CI/CD pipeline
├── markpress/              the generator (Python package)
│   ├── generator.py        front matter, Markdown rendering, site build
│   ├── cli.py              command line: python -m markpress
│   ├── templates/          Jinja2 HTML templates
│   └── static/style.css
├── content/                the website's pages, written in Markdown
├── tests/                  pytest unit tests
├── requirements.txt        runtime dependencies
├── requirements-dev.txt    + pytest, pytest-cov, flake8
└── setup.cfg               flake8 and pytest settings
```

## Running it locally

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

flake8 markpress tests             # lint
pytest                             # tests
python -m markpress                # builds content/ into public/
python -m http.server -d public    # view at http://localhost:8000
```

Options: `--src`, `--out`, `--title "My Site"`, `--drafts` (include draft pages).

## Writing pages

Each `.md` file in `content/` becomes one page. An optional front-matter block goes at the top:

```
---
title: My notes
date: 2026-09-26
draft: false
---
```

The build fails on purpose (so a broken page never goes live) when a date isn't in `YYYY-MM-DD` format, two pages share the same address, or a page is named `index.md`.

## Setting up GitHub Actions and Pages

1. Push the project to GitHub, including the `.github/workflows/ci-cd.yml` file.
2. In the repository, open **Settings → Pages**, and under **Build and deployment → Source**, choose **GitHub Actions**.
3. Open the **Actions** tab. The workflow runs on every push to `main`; to run it manually, choose **CI/CD → Run workflow**.
4. When the run finishes, the site is live at `https://<your-username>.github.io/<repo-name>/`. The link also appears on the run's summary page, next to the **deploy** job.

No secrets, webhooks or servers are needed: GitHub provides the runner, and the workflow's built-in token is allowed to publish to Pages.

## The pipeline

The workflow has three jobs, each on a fresh Ubuntu runner. A job only starts if the one before it succeeded.

| Job | Steps |
|-----|-------|
| **test** | Checkout, set up Python 3.12 (with pip caching), install dependencies, `flake8`, `pytest` with coverage; test reports are uploaded as an artifact |
| **build** | Checkout, install dependencies, `python -m markpress`, upload `public/` as the Pages artifact |
| **deploy** | Publish to GitHub Pages, then a smoke test fetches the live site and checks that it shows this run's build number |

- **Pull requests** run the test and build jobs but never deploy, so changes are checked before they are merged.
- **Concurrency** is limited to one deployment at a time.
- **Permissions** are minimal: read-only by default, with Pages write access only in the deploy job.

## Demo ideas

- **Publish a page:** change `draft: true` to `false` in `content/upcoming-features.md` and push. The page appears on the live site.
- **A failing build is caught:** set a page's date to `25/09/2026` and push. The **test** job fails (a test builds the real `content/` folder), **build** and **deploy** are skipped, and the live site keeps serving the previous version. Fix the date and push again to recover.
- **Test reports:** open a workflow run and download the **test-reports** artifact.
