"""Lottery pools, draw, settle, and undo."""

from __future__ import annotations

import random
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any

from lottery.constants import (
    CAMPUS_SPOT_COUNT,
    PARK_SPOT_COUNT,
    SPOT_TYPE_CAMPUS,
    SPOT_TYPE_PARK,
    TOTAL_SPOT_COUNT,
)
from lottery.models import ConfigError, DataStore


class DrawError(ValueError):
    """Raised when a draw or undo cannot proceed."""


def _name_map(config: dict[str, Any]) -> dict[str, str]:
    return {p["id"]: p["name"] for p in config["people"]}


def _ids(config: dict[str, Any]) -> list[str]:
    return [p["id"] for p in config["people"]]


def compute_pools(config: dict[str, Any], state: dict[str, Any]) -> dict[str, list[str]]:
    """Return must_win / bye / candidate person ids for the upcoming draw."""
    people_ids = _ids(config)
    people_state = state.get("people_state") or {}
    bye = [pid for pid in people_ids if people_state.get(pid, {}).get("is_bye_next")]

    draw_count = int(state.get("draw_count", 0))
    last_winners = list(state.get("last_winners") or [])

    if draw_count == 0 or not last_winners:
        # First round: everyone in candidate pool
        return {
            "must_win": [],
            "bye": [],
            "candidate": list(people_ids),
        }

    last_set = set(last_winners)
    must_win = [pid for pid in people_ids if pid not in last_set]
    bye_set = set(bye)
    candidate = [pid for pid in last_winners if pid not in bye_set]

    return {
        "must_win": must_win,
        "bye": bye,
        "candidate": candidate,
    }


def _resolve_names(ids: list[str], names: dict[str, str]) -> list[dict[str, str]]:
    return [{"id": pid, "name": names.get(pid, pid)} for pid in ids]


def pools_with_names(pools: dict[str, list[str]], config: dict[str, Any]) -> dict[str, Any]:
    names = _name_map(config)
    return {
        "must_win": _resolve_names(pools["must_win"], names),
        "bye": _resolve_names(pools["bye"], names),
        "candidate": _resolve_names(pools["candidate"], names),
    }


def _select_winners(pools: dict[str, list[str]], draw_count: int) -> list[str]:
    if draw_count == 0 or not pools["must_win"]:
        # First round or no prior losers: random TOTAL_SPOT_COUNT from candidate
        candidate = list(pools["candidate"])
        if len(candidate) < TOTAL_SPOT_COUNT:
            raise DrawError("候选人数不足，无法抽签")
        return random.sample(candidate, TOTAL_SPOT_COUNT)

    must_win = list(pools["must_win"])
    candidate = list(pools["candidate"])
    retain_needed = TOTAL_SPOT_COUNT - len(must_win)
    if retain_needed < 0:
        raise DrawError("必中人数超过车位数，配置与规则不兼容")
    if len(candidate) < retain_needed:
        raise DrawError("候选池人数不足，无法抽取保留名额")
    retained = random.sample(candidate, retain_needed) if retain_needed else []
    winners = must_win + retained
    if len(winners) != TOTAL_SPOT_COUNT:
        raise DrawError("中签人数异常")
    if set(winners) & set(pools["bye"]):
        raise DrawError("轮空池人员不应出现在中签结果中")
    return winners


def _assign_spots(winners: list[str]) -> dict[str, str]:
    types = [SPOT_TYPE_CAMPUS] * CAMPUS_SPOT_COUNT + [SPOT_TYPE_PARK] * PARK_SPOT_COUNT
    shuffled_winners = list(winners)
    random.shuffle(shuffled_winners)
    random.shuffle(types)
    return dict(zip(shuffled_winners, types))


def _campus_plate_holders(people_ids: list[str], assignments: dict[str, str]) -> list[str]:
    park_holders = {pid for pid, spot in assignments.items() if spot == SPOT_TYPE_PARK}
    return [pid for pid in people_ids if pid not in park_holders]


def _settle(
    config: dict[str, Any],
    state: dict[str, Any],
    winners: list[str],
    assignments: dict[str, str],
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """Update consecutive wins / bye flags; return new state and pools_after preview."""
    people_ids = _ids(config)
    winner_set = set(winners)
    new_ps: dict[str, dict[str, Any]] = {}
    for pid in people_ids:
        if pid in winner_set:
            wins = int(state["people_state"].get(pid, {}).get("consecutive_wins", 0)) + 1
        else:
            wins = 0
        new_ps[pid] = {
            "consecutive_wins": wins,
            "is_bye_next": wins >= 2,
        }

    park_holder = next(pid for pid, spot in assignments.items() if spot == SPOT_TYPE_PARK)
    campus_plates = _campus_plate_holders(people_ids, assignments)
    names = _name_map(config)

    new_state = {
        "draw_count": int(state.get("draw_count", 0)) + 1,
        "people_state": new_ps,
        "last_winners": list(winners),
        "current": {
            "winners": _resolve_names(winners, names),
            "assignments": {
                pid: {"spot": spot, "name": names[pid]} for pid, spot in assignments.items()
            },
            "campus_plate_holders": _resolve_names(campus_plates, names),
            "park_holder": {"id": park_holder, "name": names[park_holder]},
        },
    }

    pools_after = compute_pools(config, new_state)
    return new_state, pools_after


def preview_pools(store: DataStore | None = None) -> dict[str, Any]:
    store = store or DataStore()
    config, state, _ = store.load_all()
    pools = compute_pools(config, state)
    return {
        "pools": pools_with_names(pools, config),
        "draw_count": state.get("draw_count", 0),
        "next_period_number": int(state.get("draw_count", 0)) + 1,
    }


def perform_draw(store: DataStore | None = None) -> dict[str, Any]:
    store = store or DataStore()
    config, state, history = store.load_all()
    # Re-validate locked structure
    if len(config["people"]) != 5:
        raise ConfigError("参与人数必须为 5")

    snapshot_before = deepcopy(state)
    pools_before = compute_pools(config, state)
    winners = _select_winners(pools_before, int(state.get("draw_count", 0)))
    assignments = _assign_spots(winners)
    new_state, pools_after = _settle(config, state, winners, assignments)

    names = _name_map(config)
    people_ids = _ids(config)
    park_holder = next(pid for pid, spot in assignments.items() if spot == SPOT_TYPE_PARK)
    campus_plates = _campus_plate_holders(people_ids, assignments)

    now = datetime.now()
    period_n = new_state["draw_count"]
    period_label = f"{now.strftime('%Y-%m-%d')} #{period_n}"

    entry = {
        "id": str(uuid.uuid4()),
        "period_label": period_label,
        "drawn_at": now.isoformat(timespec="seconds"),
        "pools_before": pools_with_names(pools_before, config),
        "pools_after": pools_with_names(pools_after, config),
        "result": {
            "winners": _resolve_names(winners, names),
            "assignments": {
                pid: {"spot": spot, "name": names[pid]} for pid, spot in assignments.items()
            },
            "campus_plate_holders": _resolve_names(campus_plates, names),
            "park_holder": {"id": park_holder, "name": names[park_holder]},
        },
        "state_snapshot_before": snapshot_before,
    }

    history = list(history) + [entry]
    store.save_state_and_history(new_state, history)
    return {
        "entry": entry,
        "state": new_state,
        "config": config,
        "history": history,
    }


def undo_last(store: DataStore | None = None) -> dict[str, Any]:
    store = store or DataStore()
    config, state, history = store.load_all()
    if not history:
        raise DrawError("没有可撤销的抽签记录")

    last = history[-1]
    snapshot = last.get("state_snapshot_before")
    if snapshot is None:
        raise DrawError("历史记录缺少 state_snapshot_before，无法撤销")

    new_history = history[:-1]
    restored = deepcopy(snapshot)
    store.replace_state_and_history(restored, new_history)
    return {
        "undone": last,
        "state": restored,
        "config": config,
        "history": new_history,
        "pools": pools_with_names(compute_pools(config, restored), config),
    }


def bootstrap(store: DataStore | None = None) -> dict[str, Any]:
    store = store or DataStore()
    config, state, history = store.load_all()
    pools = compute_pools(config, state)
    return {
        "config": config,
        "state": state,
        "history": history,
        "pools": pools_with_names(pools, config),
        "next_period_number": int(state.get("draw_count", 0)) + 1,
    }
