---
title: From Jenkins to Render
date: 2026-09-28
---

MarkPress has been deployed three different ways. The Markdown and the generator never changed; only the pipeline around them did.

## Version 1: Jenkins on AWS EC2

The first pipeline ran on a single Arm-based EC2 instance. A GitHub webhook reached Jenkins through Nginx, Jenkins tested and built the site, and Nginx served it from the same machine.

It worked, but it meant running a server: installing Java and Jenkins, keeping the Jenkins dashboard private behind an SSH tunnel, and fixing a build node that went offline because the temporary folder was too small.

## Version 2: GitHub Actions and GitHub Pages

The second version removed the server entirely. GitHub Actions ran the checks and the build on GitHub's own machines, and GitHub Pages hosted the result.

## Version 3: GitHub Actions and Render

The current version splits the work between two services:

| Part | Service | Job |
|------|---------|-----|
| Continuous integration | GitHub Actions | Lint, test and check that the site builds |
| Continuous deployment | Render | Build the site and publish it, but only after every check passes |

## What stayed the same

- Every change goes through the same checks before it can go live.
- A failed check stops the deploy, so visitors keep seeing the last good version.
- Publishing a page is still just a `git push`.
