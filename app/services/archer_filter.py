"""Match archers in Betweenends API rows by name and membership number."""

import re
from dataclasses import dataclass, field
from typing import Any, Optional

_MATCH_RANK_SUFFIX = re.compile(r"\s+\(\d+\)$")


@dataclass
class MembershipEntry:
    organization: str
    number: str


@dataclass
class ArcherIdentity:
    first_name: str
    last_name: str
    name_aliases: list[str] = field(default_factory=list)
    membership_numbers: list[MembershipEntry] = field(default_factory=list)

    @property
    def primary_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def is_configured(self) -> bool:
        return bool(self.first_name.strip() and self.last_name.strip())


def normalize_archer_name(name: str) -> str:
    """Normalize display names for exact matching."""
    normalized = " ".join((name or "").split())
    normalized = _MATCH_RANK_SUFFIX.sub("", normalized)
    return normalized.casefold()


def _team_field(raw: dict) -> str:
    return (raw.get("fnm") or raw.get("fname") or "").strip()


def _roster_member_names(fnm: str) -> list[str]:
    """Names listed on a team entry after the newline roster suffix."""
    if "\n[" not in fnm:
        return []
    roster = fnm.split("\n[", 1)[1].rstrip("]").strip()
    if not roster:
        return []
    parts = re.split(r"\s*[,&]\s*", roster)
    return [p.strip() for p in parts if p.strip()]


def _name_from_row(raw: dict) -> str:
    fnm = _team_field(raw)
    lnm = (raw.get("lnm") or raw.get("lname") or "").strip()
    if fnm and "\n[" in fnm:
        fnm = fnm.split("\n[", 1)[0].strip()
    return f"{fnm} {lnm}".strip()


def _matches_team_roster(raw: dict, identity: ArcherIdentity) -> bool:
    for member in _roster_member_names(_team_field(raw)):
        normalized = normalize_archer_name(member)
        if normalized == normalize_archer_name(identity.primary_full_name):
            return True
        for alias in identity.name_aliases:
            if normalized == normalize_archer_name(alias):
                return True
    return False


_DEFAULT_MEMBERSHIP_FIELDS = [
    "mid",
    "mem",
    "usaid",
    "aid_ext",
    "member_id",
    "membership",
]


def _membership_fields_from_config() -> list[str]:
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            fields = current_app.config.get("ARCHER_MEMBERSHIP_API_FIELDS")
            if fields:
                return list(fields)
    except RuntimeError:
        pass
    return list(_DEFAULT_MEMBERSHIP_FIELDS)


def _normalize_membership(value: str) -> str:
    return re.sub(r"[\s\-]", "", (value or "").strip().upper())


def _row_membership_values(raw: dict, api_fields: list[str]) -> list[str]:
    values: list[str] = []
    for key in api_fields:
        val = raw.get(key)
        if val is not None and str(val).strip():
            values.append(_normalize_membership(str(val)))
    return values


def matches_archer(raw: dict, identity: ArcherIdentity) -> tuple[bool, Optional[str]]:
    """Return (matched, reason) where reason is membership|name|alias."""
    if not identity.is_configured():
        return False, None

    api_fields = _membership_fields_from_config()
    row_values = _row_membership_values(raw, api_fields)
    for entry in identity.membership_numbers:
        num = _normalize_membership(entry.number)
        if not num:
            continue
        for row_val in row_values:
            if row_val == num:
                return True, "membership"

    if _matches_team_roster(raw, identity):
        return True, "team_roster"

    row_name = normalize_archer_name(_name_from_row(raw))
    primary = normalize_archer_name(identity.primary_full_name)
    if row_name and row_name == primary:
        return True, "name"

    for alias in identity.name_aliases:
        if row_name and row_name == normalize_archer_name(alias):
            return True, "alias"

    return False, None


def identity_from_user(user) -> ArcherIdentity:
    from app.models import ArcherNameAlias, MembershipNumber

    aliases = [
        a.alias
        for a in ArcherNameAlias.query.filter_by(user_id=user.id).order_by(ArcherNameAlias.id)
    ]
    memberships = [
        MembershipEntry(organization=m.organization, number=m.number)
        for m in MembershipNumber.query.filter_by(user_id=user.id).order_by(
            MembershipNumber.id
        )
    ]
    return ArcherIdentity(
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        name_aliases=aliases,
        membership_numbers=memberships,
    )
