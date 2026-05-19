"""User-editable metadata for saved archer tournaments."""

from typing import Any, Optional


def default_metadata() -> dict:
    return {"events": []}


def get_event_metadata(metadata: Optional[dict], event_id: int) -> dict:
    meta = metadata or default_metadata()
    for event in meta.get("events") or []:
        if event.get("event_id") == event_id:
            return event
    return {"event_id": event_id, "rounds": [], "notes": ""}


def get_round_metadata(
    metadata: Optional[dict], event_id: int, round_index: int
) -> dict:
    event = get_event_metadata(metadata, event_id)
    for rnd in event.get("rounds") or []:
        if rnd.get("round_index") == round_index:
            return rnd
    return {"round_index": round_index, "distance": "", "conditions": ""}


def update_round_metadata(
    metadata: Optional[dict],
    event_id: int,
    round_index: int,
    distance: str,
    conditions: str,
    notes: str = "",
) -> dict:
    meta = dict(metadata) if metadata else default_metadata()
    events = list(meta.get("events") or [])
    event = None
    for e in events:
        if e.get("event_id") == event_id:
            event = e
            break
    if event is None:
        event = {"event_id": event_id, "rounds": [], "notes": notes}
        events.append(event)
    else:
        event = dict(event)
        event["notes"] = notes

    rounds = list(event.get("rounds") or [])
    updated = False
    for i, rnd in enumerate(rounds):
        if rnd.get("round_index") == round_index:
            rounds[i] = {
                "round_index": round_index,
                "distance": distance.strip(),
                "conditions": conditions.strip(),
            }
            updated = True
            break
    if not updated:
        rounds.append(
            {
                "round_index": round_index,
                "distance": distance.strip(),
                "conditions": conditions.strip(),
            }
        )
    event["rounds"] = rounds
    new_events = [e for e in events if e.get("event_id") != event_id]
    new_events.append(event)
    meta["events"] = new_events
    return meta


def distance_for_round(
    metadata: Optional[dict], event_id: int, round_index: int
) -> str:
    rnd = get_round_metadata(metadata, event_id, round_index)
    return rnd.get("distance") or "Unknown distance"
