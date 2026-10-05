"""SAM tool entry point for publishing NSE desk notes.

Annotations must stay real objects (no ``from __future__ import annotations``)
so the SDK detects Artifact parameters, and the ``ctx`` parameter keeps the SDK
on portable (keyword) injection.
"""

from typing import List, Optional

from sam_tool_sdk import Artifact, DataDisposition, DataObject, SandboxToolContextFacade, ToolResult, tool_cli

from .render import render_note


async def render_note_html(
    note: Artifact,
    charts: Optional[List[Artifact]] = None,
    output_filename: str = "",
    product: str = "Market note",
    ctx: SandboxToolContextFacade = None,
) -> ToolResult:
    """Turn a markdown briefing note into print-ready HTML with its chart images embedded, ready for html_to_pdf.

    Write the note as a markdown artifact first, with each chart referenced as
    ![caption](chart_filename.png) where it should appear. The first '# ' heading
    becomes the document title. Then call this tool and pass the resulting HTML
    artifact to html_to_pdf.

    Args:
        note: the markdown note artifact filename
        charts: PNG chart artifact filenames referenced in the note
        output_filename: name for the HTML artifact (defaults to the note name with .html)
        product: label shown above the title, e.g. "Pre-market note" or "EOD wrap"
    """
    md_text = note.as_text() if hasattr(note, "as_text") else str(note.content)
    chart_map = {}
    for art in charts or []:
        content = art.content if isinstance(art.content, bytes) else art.content.encode("latin-1")
        chart_map[art.filename] = (content, art.mime_type or "image/png")
    page, report = render_note(md_text, chart_map, product=product)
    out_name = output_filename or (note.filename.rsplit(".", 1)[0] + ".html")
    if not out_name.endswith(".html"):
        out_name += ".html"
    if ctx is not None:
        ctx.send_status(f"Rendered {out_name} with {len(report['charts_inlined'])} chart(s)")
    msg = f"Rendered {out_name}: {len(report['charts_inlined'])} chart(s) embedded."
    if report["charts_missing"]:
        msg += f" Missing (not passed in charts): {', '.join(report['charts_missing'])}."
    return ToolResult.ok(
        message=msg + " Next: html_to_pdf with input_document=" + out_name,
        data={"html_filename": out_name, **report},
        data_objects=[DataObject(name=out_name, content=page, mime_type="text/html",
                                 disposition=DataDisposition.ARTIFACT,
                                 description=f"{product}: print-ready HTML with embedded charts")],
    )


cli_render_note_html = tool_cli(render_note_html)
