"""Port of Betweenends scoring.js arrow and tie-breaker logic."""

import re
from typing import Optional

ARROW_VALUES = {
    "M": 0,
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "T": 10,
    "X": 10,
    "W": 5,
    "Y": 11,
    "Z": 6,
    "a": 11,
    "b": 12,
    "d": 14,
    "E": 0,
    "!": 0,
}

TIE_BREAKER_LIST = [
    [{"val": "T", "label": "10s"}, {"val": "9", "label": "9s"}],
    [{"val": "TX", "label": "10s"}, {"val": "X", "label": "Xs"}],
    [{"val": "T", "label": "10s"}],
    [{"val": "6", "label": "6s"}, {"val": "5", "label": "5s"}],
    [{"val": "a", "label": "11s"}],
    [{"val": "bd!", "label": "12s"}],
    [{"val": "W", "label": "Xs"}],
    [],
    [],
    [{"val": "a", "label": "11s"}, {"val": "T", "label": "10s"}],
    [],
    [{"val": "bd!", "label": "Bonus"}],
    [{"val": "W", "label": "Xs"}],
    [{"val": "X", "label": "Xs"}, {"val": "TX", "label": "10s"}, {"val": "9", "label": "9s"}],
    [{"val": "Z", "label": "Xs"}],
    [{"val": "T", "label": "10s"}, {"val": "8", "label": "8s"}],
    [{"val": "a", "label": "11s"}, {"val": "T", "label": "10s"}],
    [{"val": "X", "label": "Xs"}, {"val": "TX", "label": "10s"}],
    [{"val": "a", "label": "11s"}],
]


def calculate_arrows(arr_str: Optional[str]) -> int:
    if not arr_str:
        return 0
    total = 0
    for ch in arr_str:
        total += ARROW_VALUES.get(ch, 0)
    return total


def tb_count(scoring_rule: int) -> int:
    if scoring_rule < 0 or scoring_rule >= len(TIE_BREAKER_LIST):
        return 0
    return len(TIE_BREAKER_LIST[scoring_rule])


def get_tb_value(arrows: Optional[str], scoring_rule: int, tb_priority: int) -> int:
    if arrows is None or tb_priority < 0 or tb_priority >= tb_count(scoring_rule):
        return 0
    vals = TIE_BREAKER_LIST[scoring_rule][tb_priority]["val"]
    return len(re.findall(f"[{re.escape(vals)}]", arrows))


def get_final_tb_value(
    arrows: Optional[str],
    tbs: Optional[str],
    scoring_rule: int,
    tb_priority: int,
    total_arrows: int,
) -> int:
    if tbs and tb_priority >= 0:
        parts = tbs.split("|")
        if tb_priority < len(parts) and parts[tb_priority]:
            tmp = int(parts[tb_priority])
            if arrows and len(arrows) > total_arrows:
                tmp += get_tb_value(arrows[total_arrows:], scoring_rule, tb_priority)
            return tmp
    return get_tb_value(arrows, scoring_rule, tb_priority)


def round_total(arrows: Optional[str], rnd: int, arrows_per_round: int) -> int:
    if not arrows:
        return 0
    start = rnd * arrows_per_round
    return calculate_arrows(arrows[start : start + arrows_per_round])


def get_final_round_total(
    arrows: Optional[str],
    rtl: Optional[str],
    rnd: int,
    arrows_per_round: int,
) -> int:
    if rtl:
        parts = rtl.split("|")
        if rnd < len(parts) and parts[rnd]:
            return int(parts[rnd])
    return round_total(arrows, rnd, arrows_per_round)


def get_set_score(my_arrows: str, opp_arrows: str, ape: int) -> int:
    blank = "E" * ape
    if blank in my_arrows and blank in opp_arrows:
        return 0
    if "E" in my_arrows or "E" in opp_arrows:
        return 0
    my_score = calculate_arrows(my_arrows)
    opp_score = calculate_arrows(opp_arrows)
    if my_score > opp_score:
        return 2
    if my_score == opp_score:
        return 1
    return 0


def get_total_set_score(
    my_arrows: str,
    opp_arrows: str,
    epm: int,
    ape: int,
    sts: int,
) -> int:
    points = 0
    for i in range(epm):
        my_end = my_arrows[i * ape : (i + 1) * ape]
        opp_end = opp_arrows[i * ape : (i + 1) * ape]
        points += get_set_score(my_end, opp_end, ape)
    if points == epm and sts == 1:
        points += 1
    return points


def get_end_score_display(
    my_arrows: str,
    opp_arrows: Optional[str],
    end_index: int,
    ape: int,
    epm: int,
    srl: int,
) -> str:
    blank = "E" * ape
    start = end_index * ape
    my_end = my_arrows[start : start + ape]
    if blank in my_end:
        return ""
    if srl == 1 and opp_arrows is not None:
        opp_end = opp_arrows[start : start + ape]
        if blank in opp_end:
            return ""
        pts = get_set_score(my_end, opp_end, ape)
        return f"{calculate_arrows(my_end)}({pts})"
    return str(calculate_arrows(my_end))


def get_match_total(
    my_arrows: str,
    opp_arrows: Optional[str],
    epm: int,
    ape: int,
    srl: int,
    sts: int,
) -> int:
    if srl == 1 and opp_arrows is not None:
        return get_total_set_score(my_arrows, opp_arrows, epm, ape, sts)
    return calculate_arrows(my_arrows)


def get_round_from_match_number(match_number: int, met: int, str_val: int) -> int:
    if met in (3, 4):
        return match_number // (str_val + (str_val % 2))
    if met == 8:
        round_num = 0
        if str_val > 1 and str_val < 32 and match_number >= 0:
            start = 0
            stop = 2
            while stop <= match_number:
                round_num += 1
                x = round_num + 2
                stop = int((x * (x + 1) * 0.5) - 1)
        return round_num
    thresholds = [4, 8, 16, 32, 64, 128]
    for i, threshold in enumerate(thresholds):
        if match_number < threshold:
            return i
    return 6


def num_rounds(met: int, str_val: int) -> int:
    if met in (3, 4):
        rnds = (str_val + str_val % 2) - 1
        if met == 4:
            rnds *= 2
        return rnds
    if met == 8:
        return str_val - 1
    return str_val + 1


def get_round_name(rnd: int, met: int, str_val: int) -> str:
    if met == 3:
        if rnd >= 0:
            return f"Match {str_val + (str_val % 2) - rnd - 1}"
        return ""
    if met == 4:
        if rnd >= 0:
            tmp = (str_val + (str_val % 2) - 1) * 2
            return f"Match {tmp - rnd}"
        return ""
    if met == 8:
        return f"Match {str_val - rnd - 1}"
    names = [
        "Finals Round",
        "Semi Finals",
        "Quarter Finals",
        "1/8th Round",
        "1/16th Round",
        "1/32nd Round",
        "1/64th Round",
    ]
    return names[rnd] if 0 <= rnd < len(names) else ""
