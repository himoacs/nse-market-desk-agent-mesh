"""Render a markdown briefing note into print-ready HTML with charts inlined.

SAM's html_to_pdf tool renders an HTML artifact with headless Chromium, but it
does not resolve ``«artifact_content:...»`` embeds inside that HTML, so chart
images must already be ``data:`` URIs. Letting the LLM write the HTML itself
also doubles its output (the note in chat plus the same note as HTML), which
truncates long notes. This module does the conversion deterministically:

1. Chart references in the markdown (``![caption](chart.png)``, or a bare
   ``«artifact_return:chart.png»`` / ``«artifact_content:chart.png ...»`` line)
   become images.
2. Markdown (with tables) becomes HTML; the first ``# heading`` is the title.
3. Every image whose filename matches a supplied chart becomes a data: URI;
   an image alone in a paragraph becomes a ``<figure>`` with its alt text as caption.
"""

import base64
import html
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import markdown

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "note.html"
_IST = timezone(timedelta(hours=5, minutes=30))

# A line that is only an embed directive pointing at a file, e.g. «artifact_return:chart.png»
_EMBED_LINE = re.compile(r"^\s*«artifact_(?:return|content):\s*([^»>\s]+)[^»]*»\s*$", re.M)
_H1 = re.compile(r"^#\s+(.+?)\s*#*\s*$", re.M)
_IMG_ALONE = re.compile(r"<p>\s*(<img\b[^>]*>)\s*</p>", re.I)
_IMG_TAG = re.compile(r"<img\b[^>]*>", re.I)
_ATTR = re.compile(r'\b(src|alt)="([^"]*)"', re.I)


def _basename(ref: str) -> str:
    name = html.unescape(ref).strip().strip("<>").split("?")[0].rsplit("/", 1)[-1]
    return re.sub(r":\d+$", "", name)  # drop an artifact ":version" suffix


def _data_uri(content: bytes, mime_type: str) -> str:
    return f"data:{mime_type or 'image/png'};base64,{base64.b64encode(content).decode('ascii')}"


class _Inliner:
    def __init__(self, charts: Dict[str, Tuple[bytes, str]]):
        self.charts = charts
        self.inlined: List[str] = []
        self.missing: List[str] = []

    def resolve(self, tag: str) -> Tuple[Optional[str], str, str]:
        """Return (img_html or None if unavailable, caption, name)."""
        attrs = {k.lower(): v for k, v in _ATTR.findall(tag)}
        src, alt = attrs.get("src", ""), html.unescape(attrs.get("alt", ""))
        name = _basename(src)
        if src.startswith("data:"):
            return tag, alt, name
        if name not in self.charts:
            self.missing.append(name)
            return None, alt, name
        self.inlined.append(name)
        img = f'<img src="{_data_uri(*self.charts[name])}" alt="{html.escape(alt or name)}">'
        return img, ("" if alt == name else alt), name

    def figure(self, match: "re.Match[str]") -> str:
        img, caption, name = self.resolve(match.group(1))
        if img is None:
            return f'<p class="missing">[chart unavailable: {html.escape(name)}]</p>'
        cap = f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""
        return f"<figure>{img}{cap}</figure>"

    def inline(self, match: "re.Match[str]") -> str:
        if match.group(0).find('src="data:') != -1:
            return match.group(0)
        img, _, name = self.resolve(match.group(0))
        return img if img is not None else f"[chart unavailable: {html.escape(name)}]"


def render_note(markdown_text: str, charts: Dict[str, Tuple[bytes, str]], product: str = "Market note",
                rendered_at: str = "") -> Tuple[str, dict]:
    """Return (html, report). ``charts`` maps filename -> (bytes, mime_type)."""
    text = markdown_text.replace("\r\n", "\n")
    text = _EMBED_LINE.sub(lambda m: f"![]({_basename(m.group(1))})", text)

    title = product
    m = _H1.search(text)
    if m:
        title = m.group(1).strip()
        text = text[: m.start()] + text[m.end():]

    body = markdown.markdown(text.strip(), extensions=["tables", "sane_lists"], output_format="html")
    inliner = _Inliner(charts)
    body = _IMG_ALONE.sub(inliner.figure, body)
    body = _IMG_TAG.sub(inliner.inline, body)

    page = (_TEMPLATE_PATH.read_text(encoding="utf-8")
            .replace("{{TITLE}}", html.escape(title))
            .replace("{{PRODUCT}}", html.escape(product))
            .replace("{{RENDERED_AT}}", html.escape(rendered_at or datetime.now(_IST).strftime("%Y-%m-%d %H:%M IST")))
            .replace("{{BODY}}", body))
    report = {
        "title": title,
        "charts_inlined": inliner.inlined,
        "charts_missing": inliner.missing,
        "charts_unused": sorted(set(charts) - set(inliner.inlined)),
    }
    return page, report
