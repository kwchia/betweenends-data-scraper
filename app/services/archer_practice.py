"""Manual practice session validation and analytics helpers."""

from typing import Any

from app.services import scoring
from app.services.archer_analytics import ScorePoint

VALID_ARROW_CHARS = set(scoring.ARROW_VALUES.keys())
DEFAULT_ARROWS_PER_END = 3


class PracticeValidationError(ValueError):
    pass


def _arrow_string_from_grid(form, idx: int, arrows_per_end: int, num_ends: int) -> str:
    chars = []
    for e in range(num_ends):
        for a in range(arrows_per_end):
            val = (form.get(f"arrow_{idx}_{e}_{a}") or "").strip().upper()
            if val:
                chars.append(val[0])
    return "".join(chars)


def rounds_from_form(form) -> list[dict]:
    """Parse practice round fields from a Flask request form."""
    indices = set()
    for key in form:
        if key.startswith("round_index_"):
            try:
                indices.add(int(key.split("_", 2)[2]))
            except ValueError:
                continue
    rounds = []
    for idx in sorted(indices):
        entry_mode = (form.get(f"entry_mode_{idx}") or "total").strip()
        arrows_per_end = form.get(f"arrows_per_end_{idx}", DEFAULT_ARROWS_PER_END, type=int) or DEFAULT_ARROWS_PER_END
        num_ends = form.get(f"num_ends_{idx}", 1, type=int) or 1
        arrow_string = (form.get(f"arrow_string_{idx}") or "").strip().upper()
        if entry_mode == "arrows" and not arrow_string:
            arrow_string = _arrow_string_from_grid(form, idx, arrows_per_end, num_ends)
        rounds.append(
            {
                "round_index": idx,
                "distance": form.get(f"distance_{idx}", ""),
                "conditions": form.get(f"conditions_{idx}", ""),
                "entry_mode": entry_mode,
                "total_score": form.get(f"total_score_{idx}", type=int),
                "arrow_string": arrow_string,
                "arrows_per_end": arrows_per_end,
                "num_ends": num_ends,
            }
        )
    return rounds


def validate_rounds(rounds: list[dict]) -> list[dict]:
    if not rounds:
        raise PracticeValidationError("Add at least one round.")

    normalized = []
    for i, rnd in enumerate(rounds):
        entry_mode = rnd.get("entry_mode", "total")
        if entry_mode not in ("total", "arrows"):
            raise PracticeValidationError(f"Round {i + 1}: invalid entry mode.")

        distance = (rnd.get("distance") or "").strip()
        conditions = (rnd.get("conditions") or "").strip()
        arrows_per_end = rnd.get("arrows_per_end") or DEFAULT_ARROWS_PER_END
        if arrows_per_end < 1:
            arrows_per_end = DEFAULT_ARROWS_PER_END

        num_ends = rnd.get("num_ends") or 1
        if num_ends < 1:
            num_ends = 1

        item: dict[str, Any] = {
            "round_index": i,
            "distance": distance,
            "conditions": conditions,
            "entry_mode": entry_mode,
            "arrows_per_end": arrows_per_end,
            "num_ends": num_ends,
            "total_score": None,
            "arrow_string": None,
        }

        if entry_mode == "total":
            total = rnd.get("total_score")
            if total is None or total < 0:
                raise PracticeValidationError(f"Round {i + 1}: enter a valid round total.")
            item["total_score"] = int(total)
        else:
            arrow_string = (rnd.get("arrow_string") or "").strip().upper()
            if not arrow_string:
                raise PracticeValidationError(f"Round {i + 1}: enter arrow values.")
            invalid = [c for c in arrow_string if c not in VALID_ARROW_CHARS]
            if invalid:
                raise PracticeValidationError(
                    f"Round {i + 1}: invalid arrow character(s): {', '.join(sorted(set(invalid)))}"
                )
            item["arrow_string"] = arrow_string
            item["total_score"] = scoring.calculate_arrows(arrow_string)

        normalized.append(item)
    return normalized


def practice_round_count(practice) -> int:
    return len(practice.rounds_json or [])


def practice_to_score_points(practice) -> list[ScorePoint]:
    from app.services.archer_analytics import _normalized_score

    points = []
    date = practice.practice_date or ""
    for rnd in practice.rounds_json or []:
        if rnd.get("entry_mode") == "arrows" and rnd.get("arrow_string"):
            score = rnd.get("total_score") or scoring.calculate_arrows(rnd["arrow_string"])
            arrow_count = len(rnd["arrow_string"])
        elif rnd.get("total_score") is not None:
            score = rnd["total_score"]
            arrow_count = 0
        else:
            continue
        distance = rnd.get("distance") or "Unknown distance"
        normalized = _normalized_score(score, arrow_count) if arrow_count else 0.0
        points.append(
            ScorePoint(
                date=date,
                tournament_name=practice.name,
                event_name="Practice",
                division="",
                score=float(score),
                distance=distance,
                normalized=normalized,
                round_index=rnd.get("round_index", 0),
            )
        )
    return points


def practice_arrow_rounds(practice) -> list[tuple[str, str, str, int]]:
    """Return (date, name, arrow_string, arrows_per_end) for consistency analytics."""
    rows = []
    for rnd in practice.rounds_json or []:
        if rnd.get("entry_mode") != "arrows" or not rnd.get("arrow_string"):
            continue
        rows.append(
            (
                practice.practice_date or "",
                practice.name,
                rnd["arrow_string"],
                rnd.get("arrows_per_end") or DEFAULT_ARROWS_PER_END,
            )
        )
    return rows
