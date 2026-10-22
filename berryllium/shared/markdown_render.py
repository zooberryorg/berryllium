"""
Markdown rendering and sanitization utilities.
"""
import html as html_lib

import markdown
import nh3
from django.conf import settings
from django.utils.safestring import mark_safe
from markdown.extensions.toc import slugify_unicode

try:
    from pygments.token import STANDARD_TYPES

    PYGMENTS_CLASSES = {cls for cls in STANDARD_TYPES.values() if cls}
except ImportError:
    PYGMENTS_CLASSES = set()

# Whitelisted HTML tags
ALLOWED_TAGS = {
    "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "b", "i", "sup", "sub", "abbr",
    "blockquote", "code", "pre", "span", "div",
    "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tr", "th", "td",
    "a", "img",
}

# Whitelisted HTML attributes
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "abbr": {"title"},
}

# Headings keep their id for the table of contents (render_markdown_with_toc). Every id starts with
# HEADING_ID_PREFIX, so a heading can't take over the id of something else on the page.
HEADING_ID_PREFIX = "section-"
TOC_ATTRIBUTES = {**ALLOWED_ATTRIBUTES, **{f"h{level}": {"id"} for level in range(1, 7)}}

# Whitelisted CSS classes
ALLOWED_CLASSES = {
    "div": {"highlight", "linenodiv"},
    "table": {"highlighttable"},
    "td": {"linenos", "code"},
    "span": PYGMENTS_CLASSES | {"normal", "special"},
}

# Only images uploaded from our own site are allowed. Blocks tracking pixels and hotlinked images.
# NOTE: Remove this function to allow external images.
def _filter_attribute(tag, attribute, value):
    if tag == "img" and attribute == "src" and not value.startswith(settings.MEDIA_URL):
        return None
    
    return value

def _heading_slug(value, separator):
    return HEADING_ID_PREFIX + (slugify_unicode(value, separator) or "heading")
def _toc_entries(tokens, max_depth=3, depth=1):
    """Python-Markdown's toc_tokens -> [{"id", "title", "children"}], up to max_depth levels deep."""
    entries = []
    for token in tokens:
        if not token["id"].startswith(HEADING_ID_PREFIX):
            continue
        entries.append({
            "id": token["id"],
            # names come HTML-escaped, can unescape so the template escapes them exactly once
            "title": html_lib.unescape(token["name"]),
            "children": _toc_entries(token["children"], max_depth, depth + 1) if depth < max_depth else [],
        })
    return entries
def render_markdown_with_toc(text):
    """
    Similar to render_markdown but it includes a table of contents built from the headings.
    Returns (html, toc) where toc is a nested list of {"id", "title", "children"}.
    """
    md = markdown.Markdown(
        extensions=[*getattr(settings, "MARKDOWNX_MARKDOWN_EXTENSIONS", []), "markdown.extensions.toc"],
        extension_configs={
            **getattr(settings, "MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS", {}),
            "markdown.extensions.toc": {"slugify": _heading_slug, "permalink": False},
        },
    )
    html = md.convert(text or "")
    clean = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=TOC_ATTRIBUTES,
        allowed_classes=ALLOWED_CLASSES,
        attribute_filter=_filter_attribute,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer nofollow",
    )
    return mark_safe(clean), _toc_entries(getattr(md, "toc_tokens", []))


def render_markdown(text):
    html = markdown.markdown(
        text or "",
        extensions=getattr(settings, "MARKDOWNX_MARKDOWN_EXTENSIONS", []),
        extension_configs=getattr(settings, "MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS", {}),
    )

    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        allowed_classes=ALLOWED_CLASSES,
        attribute_filter=_filter_attribute,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer nofollow",
    )

