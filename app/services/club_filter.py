import re
from dataclasses import dataclass
from typing import Iterable, Optional

_MIN_CONTAINS_ALIAS_LEN = 5


@dataclass
class AliasRule:
    alias: str
    match_mode: str  # exact | contains


def normalize_club_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return text.strip()


def normalize_for_match(text: str) -> str:
    """Lowercase and strip punctuation so 'UC, San Diego' matches 'UC San Diego'."""
    text = text.strip().lower()
    text = re.sub(r"[,.\-_'\"()]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_team_name(fnm: str) -> str:
    """Team events embed roster after newline; club name is the first line."""
    if not fnm:
        return ""
    return fnm.split("\n", 1)[0].strip()


def is_team_shaped_fnm(fnm: Optional[str]) -> bool:
    if not fnm:
        return False
    if "\n[" in fnm:
        return True
    return fnm.strip().endswith(" Team")


def matches_club(
    club_text: str,
    aliases: Iterable[AliasRule],
) -> bool:
    club_text = normalize_for_match(normalize_club_text(club_text))
    if not club_text:
        return False
    for rule in aliases:
        alias = normalize_for_match(rule.alias)
        if not alias:
            continue
        if rule.match_mode == "exact":
            if club_text == alias:
                return True
        elif len(alias) >= _MIN_CONTAINS_ALIAS_LEN and alias in club_text:
            return True
    return False


def archer_club_from_row(tm: Optional[str], fnm: Optional[str] = None) -> str:
    tm = normalize_club_text(tm)
    if tm:
        return tm
    if fnm and is_team_shaped_fnm(fnm):
        return extract_team_name(fnm)
    return ""
