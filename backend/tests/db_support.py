"""Destructive integration tests are allowed only in explicitly named test databases."""
import re
from urllib.parse import unquote, urlsplit


def require_test_database(url, actual_name=None):
    parsed = urlsplit(url)
    name = unquote(parsed.path.removeprefix("/"))
    if (parsed.scheme not in {"postgres", "postgresql"} or parsed.query or parsed.fragment
            or not re.fullmatch(r"agniview_test(?:_[a-z0-9_]+)?", name)
            or (actual_name is not None and actual_name != name)):
        raise ValueError("A dedicated agniview_test or agniview_test_* database URL is required (no query/fragment)")
    return name
