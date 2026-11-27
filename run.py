#!/usr/bin/env python3
"""Kiln T0 pipeline: brief -> local placeholder site, attribution, and archive index.

No network, no deploy, no extra packages. One command: python3 run.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
SITES = ROOT / "sites"
INDEX = ROOT / "index.html"
SCHEMA_PATH = ROOT / "schema" / "attribution.schema.json"
KILL_SWITCH = ROOT / "KILL_SWITCH"
ET = ZoneInfo("America/New_York")
PUBLIC_STEPS = ("brief", "sources", "design", "build", "publish")
SIZE_LIMIT_BYTES = 5 * 1024 * 1024

# ---------------------------------------------------------------------------
# Time and IO
# ---------------------------------------------------------------------------

def now_et() -> datetime:
    return datetime.now(ET)


def iso(ts: datetime | None = None) -> str:
    return (ts or now_et()).isoformat(timespec="seconds")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Append-only log and derived attribution.json
# ---------------------------------------------------------------------------

def append_log(day_dir: Path, entry: dict) -> list[dict]:
    path = day_dir / "build-log.jsonl"
    day_dir.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return read_log(day_dir)


def read_log(day_dir: Path) -> list[dict]:
    path = day_dir / "build-log.jsonl"
    if not path.exists():
        return []
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            lines.append(json.loads(raw))
    return lines


def derive_attribution(brief: dict, log: list[dict]) -> dict:
    """Build the designer's core shape from the log. Additive fields are optional."""
    latest: dict[str, dict] = {}
    for entry in log:
        step = entry.get("step")
        if step in PUBLIC_STEPS:
            latest[step] = entry

    steps = []
    for name in PUBLIC_STEPS:
        entry = latest.get(name)
        if not entry:
            continue
        item = {
            "time": entry["time"],
            "step": name,
            "output": entry.get("output", ""),
        }
        if entry.get("agent"):
            item["agent"] = entry["agent"]
        steps.append(item)

    sources = []
    for src in brief.get("sources", []):
        item = {
            "title": src["title"],
            "url": src["url"],
            "license": src["license"],
            "type": src["type"],
        }
        if src.get("used_for"):
            item["used_for"] = src["used_for"]
        sources.append(item)

    return {
        "schema_version": "0.1.0",
        "site": {
            "date": brief["date"],
            "slug": brief.get("slug") or brief["date"],
            "title": brief.get("title") or brief["date"],
        },
        "sources": sources,
        "agents": [
            {"name": "Product Designer", "role": "Brand, design spec, and How this was made panel"},
            {"name": "Forge", "role": "Publishing pipeline, build, QA, and archive index"},
        ],
        "steps": steps,
    }


def write_attribution(day_dir: Path, brief: dict) -> dict:
    attr = derive_attribution(brief, read_log(day_dir))
    write_json(day_dir / "attribution.json", attr)
    return attr


def log_step(day_dir: Path, brief: dict, step: str, output: str, agent: str, **extra) -> dict:
    entry = {"time": iso(), "step": step, "output": output, "agent": agent}
    entry.update(extra)
    append_log(day_dir, entry)
    return write_attribution(day_dir, brief)


# ---------------------------------------------------------------------------
# Placeholder HTML — bare, unstyled, marked awaiting designer spec
# ---------------------------------------------------------------------------

def render_panel(attr: dict) -> str:
    sources_html = []
    for src in attr.get("sources", []):
        license_ = escape(src.get("license") or "license unknown")
        used = f" — {escape(src['used_for'])}" if src.get("used_for") else ""
        sources_html.append(
            "<li><a href=\"{url}\">{title}</a> ({type}) — license: {license}{used}</li>".format(
                url=escape(src.get("url") or "#", quote=True),
                title=escape(src.get("title") or "Untitled"),
                type=escape(src.get("type") or "source"),
                license=license_,
                used=used,
            )
        )
    agents_html = []
    for agent in attr.get("agents", []):
        agents_html.append(
            "<li><strong>{name}</strong> — {role}</li>".format(
                name=escape(agent.get("name") or "Unknown"),
                role=escape(agent.get("role") or ""),
            )
        )
    steps_html = []
    for step in attr.get("steps", []):
        who = f" ({escape(step['agent'])})" if step.get("agent") else ""
        steps_html.append(
            "<li><time datetime=\"{dt}\">{dt}</time> — <strong>{name}</strong>{who}: {output}</li>".format(
                dt=escape(step.get("time") or ""),
                name=escape(step.get("step") or ""),
                who=who,
                output=escape(step.get("output") or ""),
            )
        )
    return f"""\
<aside id="how-this-was-made">
  <h2>How this was made</h2>
  <p>Shared attribution panel — awaiting designer spec. Data is read from attribution.json, which is derived from the append-only build log.</p>
  <section>
    <h3>Sources</h3>
    <ul>
      {chr(10).join(sources_html) or "<li>No sources recorded.</li>"}
    </ul>
  </section>
  <section>
    <h3>Agents</h3>
    <ul>
      {chr(10).join(agents_html) or "<li>No agents recorded.</li>"}
    </ul>
  </section>
  <section>
    <h3>Process</h3>
    <ol>
      {chr(10).join(steps_html) or "<li>No steps recorded yet.</li>"}
    </ol>
  </section>
</aside>"""


def render_site(brief: dict, attr: dict) -> str:
    title = brief.get("title") or brief["date"]
    summary = brief.get("summary") or ""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kiln — {escape(brief["date"])} — {escape(title)}</title>
</head>
<body>
  <p><strong>Awaiting designer spec.</strong> This is a bare, unstyled semantic placeholder. Visual design, layout, typography, color, and UX are owned by the Product Designer and are not invented here.</p>
  <header>
    <p>Kiln</p>
    <p><a href="../../index.html">Back to the archive index</a></p>
    <h1>{escape(title)}</h1>
    <p><time datetime="{escape(brief["date"])}">{escape(brief["date"])}</time></p>
  </header>
  <main>
    <p>{escape(summary)}</p>
    <p>Machine-readable record: <a href="./attribution.json">attribution.json</a>. Append-only log: <a href="./build-log.jsonl">build-log.jsonl</a>. Build note draft (not published): <a href="./build-note.md">build-note.md</a>.</p>
  </main>
  {render_panel(attr)}
</body>
</html>
"""


def render_index(days: list[dict]) -> str:
    items = []
    for day in days:
        date = escape(day["date"])
        title = escape(day["title"])
        items.append(
            f'<li><a href="sites/{date}/index.html"><time datetime="{date}">{date}</time> — {title}</a> '
            f'(<a href="sites/{date}/attribution.json">attribution</a>)</li>'
        )
    listing = "\n      ".join(items) if items else "<li>No days generated yet.</li>"
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kiln — archive index</title>
</head>
<body>
  <p><strong>Awaiting designer spec.</strong> This is a bare, unstyled archive index, newest first. Visual design, layout, typography, color, and UX are owned by the Product Designer and are not invented here.</p>
  <header>
    <h1>Kiln</h1>
    <p>A website of websites. Local prototype only — nothing has been published.</p>
  </header>
  <main>
    <ol reversed>
      {listing}
    </ol>
  </main>
</body>
</html>
"""


def render_build_note(brief: dict, attr: dict, log: list[dict]) -> str:
    sources = "\n".join(
        f"- {s['title']} ({s['url']}) — {s['license']}" for s in attr.get("sources", [])
    ) or "- None"
    agents = "\n".join(
        f"- {a['name']}: {a['role']}" for a in attr.get("agents", [])
    ) or "- None"
    steps = "\n".join(
        f"- {s['time']} — {s['step']}: {s['output']}" for s in attr.get("steps", [])
    ) or "- None"
    return f"""\
# Build note — {brief['date']} (draft, not for auto-publish)

Derived automatically from the append-only build log. Editorial voice and whether this is shown are owned by the Product Designer. Do not publish this file until Maxwell approves.

## Site

- Title: {brief.get('title') or brief['date']}
- Date: {brief['date']}
- Slug: {brief.get('slug') or brief['date']}

## Sources

{sources}

## Agents

{agents}

## Process

{steps}

## Log (all recorded steps, including internal QA)

{chr(10).join(f"- {e['time']} — {e['step']}: {e.get('output','')}" for e in log) or "- Empty"}
"""


def write_site(day_dir: Path, brief: dict, attr: dict) -> None:
    (day_dir / "index.html").write_text(render_site(brief, attr), encoding="utf-8")
    (day_dir / "build-note.md").write_text(
        render_build_note(brief, attr, read_log(day_dir)), encoding="utf-8"
    )


def regenerate_index() -> list[dict]:
    days = []
    if SITES.exists():
        for folder in SITES.iterdir():
            attr_path = folder / "attribution.json"
            html_path = folder / "index.html"
            if not (folder.is_dir() and attr_path.exists() and html_path.exists()):
                continue
            attr = load_json(attr_path)
            site = attr.get("site") or {}
            days.append(
                {
                    "date": site.get("date") or folder.name,
                    "title": site.get("title") or folder.name,
                }
            )
    days.sort(key=lambda d: d["date"], reverse=True)
    INDEX.write_text(render_index(days), encoding="utf-8")
    return days


# ---------------------------------------------------------------------------
# QA: schema, local links, size, basic a11y
# ---------------------------------------------------------------------------

def validate_attribution(attr: dict, schema: dict) -> list[str]:
    """Tiny required-field checker. No jsonschema dependency."""
    errors = []

    def require_object(value, path):
        if not isinstance(value, dict):
            errors.append(f"{path} must be an object")
            return False
        return True

    def check_item(item, item_schema, path):
        if not require_object(item, path):
            return
        for key in item_schema.get("required", []):
            if key not in item or item[key] in (None, ""):
                errors.append(f"{path}.{key} is required")
        props = item_schema.get("properties", {})
        for key, value in item.items():
            if key in props and props[key].get("type") == "string" and not isinstance(value, str):
                errors.append(f"{path}.{key} must be a string")

    if not require_object(attr, "$"):
        return errors
    for key in schema.get("required", []):
        if key not in attr:
            errors.append(f"missing required field: {key}")
    for name in ("sources", "agents", "steps"):
        value = attr.get(name)
        if name in attr and not isinstance(value, list):
            errors.append(f"{name} must be an array")
            continue
        item_schema = schema["properties"][name]["items"]
        for i, item in enumerate(value or []):
            check_item(item, item_schema, f"{name}[{i}]")
    if "site" in attr:
        check_item(attr["site"], schema["properties"]["site"], "site")
        date = (attr.get("site") or {}).get("date")
        if date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date)):
            errors.append("site.date must be YYYY-MM-DD")
    return errors


def local_links(html: str) -> list[str]:
    found = re.findall(r"""(?:href|src)\s*=\s*(['"])([^'"]+)\1""", html, flags=re.I)
    return [url for _, url in found]


def is_local(url: str) -> bool:
    if not url or url.startswith("#"):
        return False
    if re.match(r"^[a-z][a-z0-9+.-]*:", url, flags=re.I):
        return False  # http, https, mailto, etc.
    return True


def check_links(page: Path) -> list[str]:
    errors = []
    html = page.read_text(encoding="utf-8")
    for url in local_links(html):
        if not is_local(url):
            continue
        target = (page.parent / url).resolve()
        if not str(target).startswith(str(ROOT.resolve())):
            errors.append(f"{page.name}: local link escapes the pipeline root: {url}")
        elif not target.exists():
            errors.append(f"{page.name}: broken local link: {url}")
    return errors


def check_a11y(page: Path) -> list[str]:
    html = page.read_text(encoding="utf-8")
    errors = []
    if not re.search(r"<html\b[^>]*\blang=", html, flags=re.I):
        errors.append(f"{page.name}: missing html lang")
    if not re.search(r"<title>[^<]+</title>", html, flags=re.I):
        errors.append(f"{page.name}: missing title")
    if not re.search(r"<h1\b", html, flags=re.I):
        errors.append(f"{page.name}: missing h1")
    for img in re.finditer(r"<img\b[^>]*>", html, flags=re.I):
        tag = img.group(0)
        if not re.search(r"\balt=", tag, flags=re.I):
            errors.append(f"{page.name}: img missing alt")
    return errors


def folder_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def run_qa(day_dir: Path, schema: dict) -> list[str]:
    errors = []
    attr_path = day_dir / "attribution.json"
    site_page = day_dir / "index.html"
    if not attr_path.exists():
        return ["attribution.json is missing"]
    attr = load_json(attr_path)
    errors.extend(validate_attribution(attr, schema))
    if site_page.exists():
        errors.extend(check_links(site_page))
        errors.extend(check_a11y(site_page))
    else:
        errors.append("index.html is missing")
    if INDEX.exists():
        errors.extend(check_links(INDEX))
        errors.extend(check_a11y(INDEX))
    size = folder_size(day_dir)
    if size > SIZE_LIMIT_BYTES:
        errors.append(f"site folder is {size} bytes, over the {SIZE_LIMIT_BYTES} byte cap")
    return errors


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run(brief_path: Path) -> int:
    brief = load_json(brief_path)
    for key in ("date", "title", "sources"):
        if key not in brief:
            print(f"brief is missing {key}", file=sys.stderr)
            return 1

    day_dir = SITES / brief["date"]
    if day_dir.exists():
        for leftover in day_dir.iterdir():
            if leftover.is_file():
                leftover.unlink()
    day_dir.mkdir(parents=True, exist_ok=True)
    schema = load_json(SCHEMA_PATH)

    print(f"date: {brief['date']}")
    print(f"brief: {brief_path}")

    log_step(
        day_dir,
        brief,
        "brief",
        f"Loaded brief '{brief['title']}' from {brief_path.name}",
        "Forge",
        input=brief_path.name,
    )
    write_site(day_dir, brief, load_json(day_dir / "attribution.json"))
    print("step: brief")

    n = len(brief.get("sources") or [])
    log_step(
        day_dir,
        brief,
        "sources",
        f"Recorded {n} source(s) with title, url, license, and type",
        "Forge",
        input=brief_path.name,
    )
    write_site(day_dir, brief, load_json(day_dir / "attribution.json"))
    print("step: sources")

    log_step(
        day_dir,
        brief,
        "design",
        "No approved designer spec yet. Wrote a bare semantic placeholder marked 'awaiting designer spec'.",
        "Product Designer",
        input="none — awaiting designer spec",
    )
    write_site(day_dir, brief, load_json(day_dir / "attribution.json"))
    print("step: design (placeholder)")

    log_step(
        day_dir,
        brief,
        "build",
        f"Wrote sites/{brief['date']}/index.html (unstyled placeholder) and refreshed the How this was made panel from attribution.json.",
        "Forge",
        output_path=f"sites/{brief['date']}/index.html",
    )
    write_site(day_dir, brief, load_json(day_dir / "attribution.json"))
    print("step: build")

    regenerate_index()
    qa_errors = run_qa(day_dir, schema)
    if qa_errors:
        log_step(
            day_dir,
            brief,
            "qa",
            "QA failed: " + "; ".join(qa_errors),
            "Forge",
        )
        write_site(day_dir, brief, load_json(day_dir / "attribution.json"))
        print("QA failed:", file=sys.stderr)
        for err in qa_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    size = folder_size(day_dir)
    log_step(
        day_dir,
        brief,
        "qa",
        f"QA passed: attribution.json matches the schema, no broken local links, basic a11y checks passed, folder size {size} bytes.",
        "Forge",
    )
    print(f"step: qa (passed, {size} bytes)")

    skipped = KILL_SWITCH.exists()
    if skipped:
        publish_output = (
            "Publish skipped — KILL_SWITCH is present. Owner: Maxwell. "
            "Site was generated and QA'd, but not marked published or deployed."
        )
    else:
        publish_output = (
            f"Local only: sites/{brief['date']}/index.html is ready. Nothing was deployed or pushed."
        )
    log_step(day_dir, brief, "publish", publish_output, "Forge")
    write_site(day_dir, brief, load_json(day_dir / "attribution.json"))
    days = regenerate_index()
    # Re-run link checks after the final write so the index and panel are current.
    final_errors = run_qa(day_dir, schema)
    if final_errors:
        print("final QA failed:", file=sys.stderr)
        for err in final_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"step: publish ({'skipped by kill switch' if skipped else 'local only'})")
    print(f"wrote: {day_dir / 'index.html'}")
    print(f"wrote: {day_dir / 'attribution.json'}")
    print(f"wrote: {day_dir / 'build-log.jsonl'}")
    print(f"wrote: {day_dir / 'build-note.md'}")
    print(f"wrote: {INDEX} ({len(days)} day(s))")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Kiln T0 pipeline.")
    parser.add_argument(
        "--brief",
        default=str(ROOT / "sample-brief.json"),
        help="Path to a brief JSON file (default: sample-brief.json)",
    )
    args = parser.parse_args()
    brief_path = Path(args.brief)
    if not brief_path.is_absolute():
        brief_path = (Path.cwd() / brief_path).resolve()
    if not brief_path.exists():
        print(f"brief not found: {brief_path}", file=sys.stderr)
        return 1
    return run(brief_path)


if __name__ == "__main__":
    sys.exit(main())
