"""
Markdown rendering for AI-generated text — Bryan and Bryan.

Renders trusted-but-unstructured AI output (the case strength assessment from
Claude, plus any future AI features) into safe HTML for both the website and
the PDF report.

Security model:
1. Pre-escape the input via markupsafe.escape so any raw HTML in the source
   is converted to entities (`<script>` -> `&lt;script&gt;`). This neutralises
   injection attempts before the markdown parser ever sees them.
2. Run Python-Markdown with NO extensions (no html, no attr_list, no fenced
   code blocks, etc.). The parser will convert markdown syntax (## heading,
   **bold**, *italic*) but leave HTML entities untouched.
3. Wrap the result in a Markup() object so Jinja's autoescape does not
   re-escape the output.

This is the only place markdown -> HTML conversion happens for AI text.
Both render paths (PDF report and HTML results page) go through the
`markdown_safe` Jinja filter registered in app/__init__.py:create_app().
"""
from __future__ import annotations

import re

import markdown
from markupsafe import Markup, escape


# Detect a "malformed heading" — a markdown ATX heading (`# `, `## `, etc.)
# whose line continues with more than 10 words. The Claude model sometimes
# emits `## Section Title <body text continues on the same line...>` with no
# newline break. Without preprocessing, Python-Markdown swallows the entire
# paragraph into the heading element, which renders worse than the raw
# markdown. We strip the leading `#` marks in that case so the line falls
# through to a normal paragraph.
_MALFORMED_HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
_HEADING_WORD_LIMIT = 10


def _strip_malformed_headings(text: str) -> str:
    def _replace(match: re.Match) -> str:
        body = match.group(2)
        if len(body.split()) > _HEADING_WORD_LIMIT:
            return body  # treat as plain prose
        return match.group(0)  # well-formed short heading — keep it

    return _MALFORMED_HEADING.sub(_replace, text)


def render_markdown_safe(text: str | None) -> Markup:
    """
    Convert untrusted markdown text into safe HTML.

    Returns Markup("") for empty/None input so the Jinja filter is safe to
    apply unconditionally.
    """
    if not text:
        return Markup("")
    cleaned = _strip_malformed_headings(text)
    escaped = str(escape(cleaned))      # neutralise raw HTML in the source
    html = markdown.markdown(escaped)   # ## -> <h2>, ** -> <strong>, etc.
    return Markup(html)
