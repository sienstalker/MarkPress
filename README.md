# MarkPress

Markdown-to-website generator with CI/CD.

MarkPress converts a folder of Markdown files into a static website. Every push to GitHub triggers a Jenkins pipeline on an AWS EC2 server (a t4g.small Arm instance running Debian) that lints the code, runs the tests, builds the site and deploys it to Nginx. The footer of every page shows the Jenkins build number and commit that produced it.

```
 git push ──► GitHub ──webhook──► Nginx ──► Jenkins (EC2) ──► lint ► test ► build ► deploy ► smoke test
                                                                            │
                                         visitors ◄── Nginx :80 ◄── /var/www/markpress
```

## Project structure

```
markpress/
├── markpress/              the generator (Python package)
│   ├── generator.py        front matter, Markdown rendering, site build
│   ├── cli.py              command line: python -m markpress
│   ├── templates/          Jinja2 HTML templates
│   └── static/style.css
├── content/                the website's pages, written in Markdown
├── tests/                  pytest unit tests
├── deploy/
│   ├── setup_ec2.sh        one-time server setup (Jenkins, Nginx, Python)
│   └── nginx-markpress.conf
├── Jenkinsfile             the CI/CD pipeline
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

## Deploying on AWS EC2

### Reference setup

This project runs on:

- **Instance:** AWS EC2 **t4g.small**: 2 vCPUs and 2 GB of RAM on an AWS Graviton2 processor (**Arm Neoverse N1** cores, 64-bit Arm)
- **Operating system:** **Debian 13 for Arm (arm64)**, not Ubuntu
- **Disk:** 15 GB

Every part of the stack (Java, Jenkins, Python and its dependencies, and Nginx) comes as native arm64 packages from Debian and the Jenkins repository, so nothing needs to be compiled or emulated.

### 1. Launch the instance

- **AMI:** Debian 13 **64-bit (Arm)**. The setup script also works on Debian x86 and on Ubuntu 24.04, but this project is built and tested on Debian for Arm.
- **Type:** t4g.small (2 GB RAM). When choosing the AMI, make sure the architecture says **64-bit (Arm)**; an x86 AMI won't launch on a t4g instance.
- **Storage:** 15 GB or more
- **Security group inbound rules:**

| Port | Purpose | Source |
|------|---------|--------|
| 22   | SSH (also used to reach the Jenkins UI) | My IP |
| 80   | The website and the GitHub webhook | Anywhere (0.0.0.0/0) |

Port 8080 is **not** opened. Jenkins stays private: you reach its dashboard through an SSH tunnel, and GitHub reaches only the webhook path, which Nginx forwards to Jenkins.

Recommended: attach an **Elastic IP**, otherwise the public IP changes every time the instance stops and the GitHub webhook breaks.

### 2. Push this project to GitHub

```bash
git init
git add .
git commit -m "Initial MarkPress project"
git branch -M main
git remote add origin https://github.com/<your-username>/markpress.git
git push -u origin main
```

### 3. Set up the server

```bash
ssh -i your-key.pem admin@<EC2-public-IP>      # Debian's default user is "admin"
git clone https://github.com/<your-username>/markpress.git
cd markpress
bash deploy/setup_ec2.sh
```

This installs Java 21, Jenkins, Python, Nginx and rsync; gives Jenkins a temp folder on disk (Debian's in-memory `/tmp` is too small and makes Jenkins take its build node offline); creates `/var/www/markpress` owned by the `jenkins` user; configures Nginx; and prints the initial Jenkins admin password.

### 4. Open Jenkins through an SSH tunnel

On your own computer:

```bash
ssh -i your-key.pem -L 8080:localhost:8080 admin@<EC2-public-IP>
```

Keep that terminal open and visit `http://localhost:8080`.

### 5. Configure Jenkins

1. Paste the admin password, choose **Install suggested plugins** (includes Git, Pipeline, GitHub and JUnit), and create your admin user.
2. **New Item** → name it `markpress` → **Pipeline** → OK.
3. Under **Triggers**, tick **GitHub hook trigger for GITScm polling**.
4. Under **Pipeline**:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: `https://github.com/<your-username>/markpress.git`
   - Branch: `*/main` (the default `*/master` fails)
   - Script Path: `Jenkinsfile`
5. Save, then click **Build Now** once.

### 6. Add the GitHub webhook

In the GitHub repo: **Settings → Webhooks → Add webhook**

- Payload URL: `http://<EC2-public-IP>/github-webhook/` (port 80, no `:8080`; the trailing slash matters)
- Content type: `application/json`
- Events: **Just the push event**

GitHub sends a test ping; a green tick means it reached Jenkins through Nginx.

### 7. See it work

Open `http://<EC2-public-IP>/`. Then edit a page in `content/`, commit and push. Within a minute Jenkins runs the pipeline, and the page footer shows the new build number.

## Demo ideas

- **Publish a page:** change `draft: true` to `false` in `content/upcoming-features.md` and push. The page appears.
- **A failing build is caught:** set a page's date to `25/09/2026` and push. The *Test* stage fails (a test builds the real `content/` folder), deployment never runs, and the live site keeps serving the previous build.
- **Test report:** open a build in Jenkins and click **Test Result** to see all tests; the built site is saved under **Build Artifacts**.

## Pipeline stages

| Stage | What it does |
|-------|--------------|
| Checkout | Pulls the pushed commit from GitHub |
| Set up Python | Creates a virtual environment and installs dependencies |
| Lint | `flake8` style check |
| Test | `pytest` with JUnit report and coverage |
| Build site | `python -m markpress` generates `public/`, archived as an artifact |
| Deploy | `rsync` copies `public/` into `/var/www/markpress` |
| Smoke test | `curl`s the live site and checks it shows this build's number |

## Troubleshooting

- **Build stuck on "Waiting for next available executor":** open **Manage Jenkins → Nodes → Built-In Node** and read the offline reason. For low temp space, the setup script's temp-folder fix solves it; alternatively lower the **Free Temp Space** threshold under **Configure Monitors**.
- **Webhook shows "failed to connect to host":** check port 80 is open, the Payload URL has no `:8080`, and the instance's public IP hasn't changed.
- **Webhook returns 404:** the Nginx `location /github-webhook/` block is missing; re-run `sudo nginx -t && sudo systemctl reload nginx` after adding it.
- **`python3 -m venv` fails:** `sudo apt-get install python3-venv`.
- **Deploy stage: permission denied:** `sudo chown -R jenkins:jenkins /var/www/markpress`.
- **Jenkins becomes unresponsive:** the instance is out of memory; use a bigger instance or confirm swap is on with `free -h`.
