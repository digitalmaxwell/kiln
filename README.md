# Kiln

A daily website of websites. This repository is the publishing pipeline and a local archive of generated sites.

Visual design is owned by the Product Designer. Every HTML page in this repo is a bare, unstyled semantic placeholder marked **awaiting designer spec**. Nothing here invents layout, typography, color, or UX.

## Run locally

Python 3.10+, no packages to install:

```bash
python3 run.py
```

Optional: `python3 run.py --brief path/to/brief.json`

This writes `sites/YYYY-MM-DD/index.html`, derives `attribution.json` from an append-only `build-log.jsonl`, writes a `build-note.md` draft (not for auto-publish), regenerates the archive `index.html`, and runs checks (schema, local links, basic a11y, size).

## Kill switch

Owner: **Maxwell**. Only Maxwell (or someone he names) should add or remove this file.

If a file named `KILL_SWITCH` is present at the repository root, `run.py` still generates the day's site and runs QA, but it does not mark the site published. The daily GitHub Actions workflow also skips the deploy job when this file is present.

To halt a publish: add an empty file named `KILL_SWITCH` at the repo root. To resume: delete it.

Do not commit `KILL_SWITCH` unless you intend to halt publishes.

## Daily workflow

`.github/workflows/daily.yml` runs on `workflow_dispatch` and on a cron at `0 13 * * *` (13:00 UTC). That is 8:00 AM America/New_York during EST. During EDT it drifts to 9:00 AM ET; 8:00 AM EDT would be 12:00 UTC. The cron is left as a single 13:00 UTC schedule on purpose, to keep the workflow small.

The workflow checks out the repo, sets up Python, honors the kill switch, runs `python3 run.py` (including QA), and uploads the built site as an artifact. It does not commit or push generated files back to the repo.

## Deploy (inactive until Cloudflare is connected)

A deploy job is wired with `cloudflare/wrangler-action` and is a no-op unless both `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` repo secrets are set, and `KILL_SWITCH` is absent. It never prints or commits secrets. There is no deploy step that runs today.

Preferred production path (no token handling): in the Cloudflare dashboard, Workers & Pages → Create → Pages → Connect to Git, authorize the Cloudflare GitHub app for `digitalmaxwell/kiln` only, build command `python3 run.py`, output directory `.`.

## Layout

```
run.py
sample-brief.json
schema/attribution.schema.json
index.html
sites/YYYY-MM-DD/index.html
sites/YYYY-MM-DD/attribution.json
sites/YYYY-MM-DD/build-log.jsonl
sites/YYYY-MM-DD/build-note.md
.github/workflows/daily.yml
```
