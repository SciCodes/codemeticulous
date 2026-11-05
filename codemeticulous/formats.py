from __future__ import annotations

from codemeticulous.conversion import ConversionError

FORMAT_ALIASES = {
    "codemeta.json": "codemeta",
    "datacite.xml": "datacite",
}

SUPPORTED_VERSIONS: dict[str, tuple[str, ...]] = {
    "software-metadata": ("1",),
    "codemeta": ("3.0",),
    "cff": ("1.2.0",),
    "datacite": ("4.5", "4.6"),
}


def normalize_format(format_name: str) -> str:
    return FORMAT_ALIASES.get(format_name, format_name)


def require_version(format_name: str, version: str) -> str:
    normalized = normalize_format(format_name)
    supported = SUPPORTED_VERSIONS.get(normalized)
    if supported is None:
        raise ConversionError(f"Unsupported format: {format_name}")
    if version not in supported:
        choices = ", ".join(supported)
        raise ConversionError(
            f"Unsupported {format_name} version: {version}. Supported: {choices}"
        )
    return normalized


__all__ = [
    "FORMAT_ALIASES",
    "SUPPORTED_VERSIONS",
    "normalize_format",
    "require_version",
]
