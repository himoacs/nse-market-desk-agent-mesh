"""Tests for the note renderer and its SAM tool wrapper.

``markdown`` is a declared dependency; if it is not installed for the local
interpreter, the tests fall back to the bundle built by ``sam toolset validate``
(dist/<os>-<arch>/python), which contains it.
"""

import asyncio
import base64
import glob
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
try:
    import markdown  # noqa: F401
except ImportError:
    for d in sorted(glob.glob(str(ROOT / "dist" / "*" / "python"))):
        sys.path.append(d)
SDK = Path("/Applications/Solace Agent Mesh.app/Contents/Resources/sandbox/sam-tool-sdk")
if SDK.is_dir():
    sys.path.append(str(SDK))

from nse_publishing.render import render_note  # noqa: E402

PNG = (Path(__file__).parent / "fixtures" / "sector_rotation_quadrant.png").read_bytes()
CHARTS = {"sector_rotation_quadrant.png": (PNG, "image/png")}

NOTE = """# Pre-market note: Tuesday 6 October 2026

**Breadth fell to 0.33; IT keeps 3-month leadership.**

## Sector rotation

| Sector | 1M RS | 3M RS | Quadrant |
|---|---|---|---|
| IT | +0.95 | +12.56 | Leading |

![Sector rotation, 3M RS vs 1M RS](sector_rotation_quadrant.png)

- Auto lags.

*Source: NSE MCP.*
"""


class RenderNoteTest(unittest.TestCase):
    def test_title_table_and_inlined_chart(self):
        page, report = render_note(NOTE, CHARTS, product="Pre-market note")
        self.assertIn("<h1>Pre-market note: Tuesday 6 October 2026</h1>", page)
        self.assertIn("<table>", page)
        self.assertIn("<figure><img src=\"data:image/png;base64,", page)
        self.assertIn("<figcaption>Sector rotation, 3M RS vs 1M RS</figcaption>", page)
        self.assertIn(base64.b64encode(PNG[:60]).decode()[:40], page)
        self.assertEqual(report["charts_inlined"], ["sector_rotation_quadrant.png"])
        self.assertEqual(report["charts_missing"], [])
        self.assertNotIn("{{", page)

    def test_embed_directive_lines_become_images(self):
        note = "# T\n\nText\n\n«artifact_return:sector_rotation_quadrant.png»\n\n«artifact_content:sector_rotation_quadrant.png >>> format:datauri»\n"
        page, report = render_note(note, CHARTS)
        self.assertEqual(report["charts_inlined"], ["sector_rotation_quadrant.png"] * 2)
        self.assertNotIn("«", page)

    def test_versioned_and_pathed_refs(self):
        note = "# T\n\n![c](./charts/sector_rotation_quadrant.png:2)\n"
        _, report = render_note(note, CHARTS)
        self.assertEqual(report["charts_inlined"], ["sector_rotation_quadrant.png"])

    def test_missing_chart_is_reported_not_broken(self):
        page, report = render_note("# T\n\n![x](nope.png)\n", CHARTS)
        self.assertEqual(report["charts_missing"], ["nope.png"])
        self.assertIn("chart unavailable: nope.png", page)
        self.assertEqual(report["charts_unused"], ["sector_rotation_quadrant.png"])

    def test_no_h1_uses_product_title(self):
        page, report = render_note("Just text", {}, product="EOD wrap")
        self.assertEqual(report["title"], "EOD wrap")


try:
    from sam_tool_sdk import Artifact

    from nse_publishing import tools
except ImportError:  # pragma: no cover
    tools = None


@unittest.skipIf(tools is None, "sam_tool_sdk not importable")
class ToolWrapperTest(unittest.TestCase):
    def test_render_note_html(self):
        note = Artifact(content=NOTE.encode(), filename="pre_market_note_2026-10-06.md", version=1, mime_type="text/markdown")
        chart = Artifact(content=PNG, filename="sector_rotation_quadrant.png", version=1, mime_type="image/png")
        res = asyncio.run(tools.render_note_html(note, [chart], product="Pre-market note"))
        self.assertEqual(res.status, "success", res.message)
        self.assertEqual(res.data["html_filename"], "pre_market_note_2026-10-06.html")
        self.assertEqual(res.data_objects[0].name, "pre_market_note_2026-10-06.html")
        self.assertIn("data:image/png;base64,", res.data_objects[0].content)

    def test_portable_injection(self):
        from sam_tool_sdk.tool_runner import _detect_special_params

        ctx_param, artifact_params = _detect_special_params(tools.render_note_html)
        self.assertEqual(ctx_param, "ctx")
        self.assertEqual(set(artifact_params), {"note", "charts"})


if __name__ == "__main__":
    unittest.main()
