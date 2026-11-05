from __future__ import annotations

import re
from urllib.parse import urlsplit

_DOI = re.compile(r"^10\.\d{4,9}(?:\.\d+)?/\S+$", re.IGNORECASE)


def normalize_doi(value: str) -> str | None:
    """Return a bare DOI for supported DOI spellings, or None if invalid."""
    candidate = value.strip()
    if candidate.lower().startswith("doi:"):
        candidate = candidate[4:]
    else:
        parsed = urlsplit(candidate)
        if parsed.scheme in {"http", "https"}:
            if parsed.netloc.lower() not in {"doi.org", "dx.doi.org"}:
                return None
            candidate = parsed.path.lstrip("/")
    return candidate if _DOI.fullmatch(candidate) else None


__all__ = ["normalize_doi"]
