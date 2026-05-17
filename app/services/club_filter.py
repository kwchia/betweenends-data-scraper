import re
from dataclasses import dataclass
from typing import Iterable, Optional

_MIN_REVERSE_CONTAINS_LEN = 8


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
        elif alias in club_text or (
            len(club_text) >= _MIN_REVERSE_CONTAINS_LEN and club_text in alias
        ):
            return True
    return False


def archer_club_from_row(tm: Optional[str], fnm: Optional[str] = None) -> str:
    tm = normalize_club_text(tm)
    if tm:
        return tm
    if fnm:
        return extract_team_name(fnm)
    return ""
