"""Allowlist of official public identifiers (data/public_identifiers.json), used by CE-3."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "public_identifiers.json"


class PublicIdentifiers:
    def __init__(self, entries: list[dict], version: str = "unknown"):
        self.version = version
        self._phones = {e["canonical"]: e for e in entries if e["type"] == "PHONE"}
        self._domains = {e["canonical"].lower(): e for e in entries if e["type"] == "DOMAIN"}

    @classmethod
    def load(cls, path: Path | str = DEFAULT_PATH) -> "PublicIdentifiers":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data["identifiers"], data.get("version", "unknown"))

    def lookup(self, entity_type: str, canonical: str) -> dict | None:
        """The allowlist entry for an identifier, or None. Domains match exactly or as a subdomain of an
        entry ('netbanking.sbi.co.in' matches 'sbi.co.in'); a look-alike such as 'sbi.co.in.evil.example'
        does not."""
        if entity_type == "PHONE":
            return self._phones.get(canonical)
        if entity_type in ("DOMAIN", "URL"):
            host = canonical.lower()
            if entity_type == "URL":
                host = host.split("://", 1)[-1].split("/", 1)[0]
            for domain, entry in self._domains.items():
                if host == domain or host.endswith("." + domain):
                    return entry
        return None


@lru_cache(maxsize=1)
def get_public_identifiers() -> PublicIdentifiers:
    return PublicIdentifiers.load()
