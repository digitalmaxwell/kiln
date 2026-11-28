# Kiln

A daily website of websites. This repository is the publishing pipeline and a local archive of generated sites.

Visual design is owned by the Product Designer. Every HTML page in this repo is a bare, unstyled semantic placeholder marked **awaiting designer spec**. Nothing here invents layout, typography, color, or UX.

## Run locally

Python 3.10+, no packages to install:

```bash
python3 run.py
```

Optional: `python3 run.py --brief path/to/brief.json`

This writes `sites/YYYY-MM-DD/index.html`, derives `attribution.json` from an append-only `build-log.jsonl`, writes a `build-note.md` draft (not for auto-publish), regenerates the archive `index.html`, and runs checks (schema, local links, basic a11y, size). When `KILL_SWITCH` is absent it also copies the publishable pages (`index.html` and `sites/`) into `public/` for the Worker.

## Kill switch

Owner: **Maxwell**. Only Maxwell (or someone he names) should add or remove this file.

If a file named `KILL_SWITCH` is present at the repository root, `run.py` still generates the day's site and runs QA, but it does not mark the site published and it does not refresh `public/`. The daily GitHub Actions workflow skips its deploy job when this file is present. `scripts/cloudflare-build.sh` then exits non-zero, so `npx wrangler deploy` does not upload a new version and the previous deployment stays in place.

To halt a publish: add an empty file named `KILL_SWITCH` at the repo root. To resume: delete it.

Do not commit `KILL_SWITCH` unless you intend to halt publishes.

## Daily workflow

`.github/workflows/daily.yml` runs on `workflow_dispatch` and on a cron at `0 13 * * *` (13:00 UTC). That is 8:00 AM America/New_York during EST. During EDT it drifts to 9:00 AM ET; 8:00 AM EDT would be 12:00 UTC. The cron is left as a single 13:00 UTC schedule on purpose, to keep the workflow small.

The workflow checks out the repo, sets up Python, honors the kill switch, runs `python3 run.py` (including QA), and uploads the built site as an artifact. It does not commit or push generated files back to the repo.

## Deploy

Production is an assets-only Worker named `kiln` on Workers Builds, production branch `main`, workers.dev host only. There is no custom domain and no secrets in this repo.

`wrangler.jsonc` points `assets.directory` at `./public`. That directory is only `index.html` and `sites/` (the pages and the files they link to). `run.py`, `.github`, schema, and the rest of the repo are not in it, so they are not uploaded. `public/` is committed so the directory exists when a build starts; `build.command` refreshes it before upload. Requests that do not match a file return 404 (`not_found_handling` is `none`). URLs stay `/` and `/sites/<date>/...`.

Dashboard deploy command: `npx wrangler deploy`. `preview_urls` is on so a pull request can get a workers.dev preview. There is no custom domain.

Wrangler runs this before upload (`build.command`):

```bash
sh scripts/cloudflare-build.sh
```

That script runs `python3 run.py`, then exits non-zero if `KILL_SWITCH` is present.

Workers Builds does not read Wrangler's custom build as its own Build command. Leave the dashboard Build command empty, or set it to the same script:

```bash
sh scripts/cloudflare-build.sh
```

Do not deploy the repository root.

`.github/workflows/daily.yml` is unchanged: cron `0 13 * * *` (8:00 AM America/New_York during EST), `python3 run.py` still runs when `KILL_SWITCH` is present, and the workflow's deploy job stays skipped unless that file is absent and both `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` are set. The workflow never prints or commits those secrets.

## Layout

```
run.py
scripts/cloudflare-build.sh
wrangler.jsonc
sample-brief.json
schema/attribution.schema.json
index.html
sites/YYYY-MM-DD/index.html
sites/YYYY-MM-DD/attribution.json
sites/YYYY-MM-DD/build-log.jsonl
sites/YYYY-MM-DD/build-note.md
public/                  publishable site only; the only directory Wrangler uploads
.github/workflows/daily.yml
```
