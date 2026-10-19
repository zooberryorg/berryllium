"""
Markdown rendering and sanitization utilities.
"""

import markdown
import nh3
from django.conf import settings

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

# Whitelisted CSS classes
ALLOWED_CLASSES = {
    "div": {"highlight", "linenodiv"},
    "table": {"highlighttable"},
    "td": {"linenos", "code"},
    "span": PYGMENTS_CLASSES | {"normal", "special"},
}