"""Publish bundle: archive copy, public/ assets, and the Cloudflare kill switch."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run  # noqa: E402


def load_jsonc(path: Path) -> dict:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        lines.append(line.split("//", 1)[0])
    return json.loads("\n".join(lines))


class IndexCopyTest(unittest.TestCase):
    def test_generated_index_says_published_daily(self):
        html = run.render_index(
            [{"date": "2026-11-27", "title": "Sample day (pipeline test)"}]
        )
        self.assertIn("<p>A website of websites. Published daily.</p>", html)
        self.assertNotIn("Local prototype only", html)
        self.assertNotIn("nothing has been published", html)
        self.assertIn("<h1>Kiln</h1>", html)

    def test_checked_in_index_has_the_same_line(self):
        text = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("<p>A website of websites. Published daily.</p>", text)
        self.assertNotIn("nothing has been published", text)

    def test_committed_public_bundle_is_the_site_only(self):
        public = ROOT / "public"
        files = sorted(
            p.relative_to(public).as_posix()
            for p in public.rglob("*")
            if p.is_file()
        )
        self.assertIn("index.html", files)
        self.assertTrue(any(path.startswith("sites/") and path.endswith("/index.html") for path in files))
        blob = "\n".join(files)
        self.assertNotIn("run.py", blob)
        self.assertNotIn(".github", blob)
        self.assertNotIn("logs/", blob)
        self.assertNotIn("/logs", blob)
        index = (public / "index.html").read_text(encoding="utf-8")
        self.assertIn("<p>A website of websites. Published daily.</p>", index)


class PublicBundleTest(unittest.TestCase):
    def test_assemble_public_copies_site_output_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text(
                "<p>A website of websites. Published daily.</p>\n",
                encoding="utf-8",
            )
            day = root / "sites" / "2026-11-27"
            day.mkdir(parents=True)
            (day / "index.html").write_text("<h1>day</h1>\n", encoding="utf-8")
            (day / "attribution.json").write_text("{}\n", encoding="utf-8")
            (root / "run.py").write_text("print('source')\n", encoding="utf-8")
            workflow = root / ".github" / "workflows"
            workflow.mkdir(parents=True)
            (workflow / "daily.yml").write_text("name: Daily\n", encoding="utf-8")
            logs = root / "logs"
            logs.mkdir()
            (logs / "build.log").write_text("log\n", encoding="utf-8")
            (root / "schema").mkdir()
            (root / "schema" / "attribution.schema.json").write_text("{}\n", encoding="utf-8")

            public = root / "public"
            run.assemble_public(public, root / "index.html", root / "sites")

            files = sorted(
                p.relative_to(public).as_posix()
                for p in public.rglob("*")
                if p.is_file()
            )
            self.assertEqual(
                files,
                [
                    "index.html",
                    "sites/2026-11-27/attribution.json",
                    "sites/2026-11-27/index.html",
                ],
            )
            for path in files:
                parts = Path(path).parts
                self.assertNotIn("run.py", parts)
                self.assertNotIn(".github", parts)
                self.assertNotIn("logs", parts)
                self.assertNotIn("schema", parts)

    def test_kill_switch_blocks_publish(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(run.publish_blocked(root))
            (root / "KILL_SWITCH").write_text("", encoding="utf-8")
            self.assertTrue(run.publish_blocked(root))


class CloudflareConfigTest(unittest.TestCase):
    def test_wrangler_is_assets_only_public_directory(self):
        config_path = ROOT / "wrangler.jsonc"
        self.assertTrue(config_path.is_file(), "wrangler.jsonc is missing")
        config = load_jsonc(config_path)
        self.assertEqual(config["name"], "kiln")
        self.assertNotIn("main", config)
        self.assertEqual(config["assets"]["directory"], "./public")
        self.assertEqual(config["assets"]["not_found_handling"], "none")
        self.assertNotIn("routes", config)
        command = config["build"]["command"]
        self.assertIn("scripts/cloudflare-build.sh", command)

    def test_cloudflare_build_runs_pipeline_and_refuses_kill_switch(self):
        script = ROOT / "scripts" / "cloudflare-build.sh"
        self.assertTrue(script.is_file(), "cloudflare build script is missing")
        text = script.read_text(encoding="utf-8")
        self.assertIn("python3 run.py", text)
        self.assertIn("KILL_SWITCH", text)
        self.assertIn("exit 1", text)

    def test_daily_workflow_keeps_cron_and_kill_switch(self):
        workflow = (ROOT / ".github" / "workflows" / "daily.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '0 13 * * *'", workflow)
        self.assertIn("KILL_SWITCH", workflow)
        self.assertIn("python3 run.py", workflow)


if __name__ == "__main__":
    unittest.main()
