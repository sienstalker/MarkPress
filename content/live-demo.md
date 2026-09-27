---
title: Published live during the demo
date: 2026-09-25
---

This page was written a few minutes ago and pushed to GitHub. Nobody logged into the server or copied any files: the Jenkins pipeline built and deployed it automatically.

## What just happened

1. A `git push` sent this Markdown file to GitHub.
2. GitHub's webhook notified Jenkins on the EC2 server.
3. Jenkins linted the code, ran the tests and built the site.
4. The new site was copied to Nginx, and a smoke test confirmed it was live.

Check the footer below: the build number and commit ID show exactly which pipeline run produced this page.
