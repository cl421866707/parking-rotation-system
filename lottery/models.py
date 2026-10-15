"""JSON persistence and structure validation."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

from lottery.constants import (
    CAMPUS_SPOT_COUNT,
    DEFAULT_PEOPLE,
    DEFAULT_RULES_TEXT,
    DEFAULT_SPOTS,
    PARK_SPOT_COUNT,
    PERSON_COUNT,
    SPOT_TYPE_CAMPUS,
    SPOT_TYPE_PARK,
)

_lock = threading.Lock()


class ConfigError(ValueError):
    """Raised when config violates locked phase-A structure."""


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_settings(root: Path | None = None) -> dict[str, Any]:
    root = root or project_root()
    settings_path = root / "settings.json"
    if not settings_path.exists():
        settings = {"data_dir": "data"}
        settings_path.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return settings
    with settings_path.open(encoding="utf-8") as f:
        return json.load(f)


def resolve_data_dir(root: Path | None = None) -> Path:
    root = root or project_root()
    settings = load_settings(root)
    data_dir = Path(settings.get("data_dir", "data"))
    if not data_dir.is_absolute():
        data_dir = root / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return deepcopy(default)
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def default_app_config() -> dict[str, Any]:
    return {
        "people": deepcopy(DEFAULT_PEOPLE),
        "spots": deepcopy(DEFAULT_SPOTS),
        "rules_text": DEFAULT_RULES_TEXT,
    }


def default_state(people: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    people = people or DEFAULT_PEOPLE
    return {
        "draw_count": 0,
        "people_state": {
            p["id"]: {"consecutive_wins": 0, "is_bye_next": False} for p in people
        },
        "current": None,
        "last_winners": [],
    }


def default_history() -> list[Any]:
    return []


def validate_app_config(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise ConfigError("配置必须是对象")

    people = config.get("people")
    if not isinstance(people, list) or len(people) != PERSON_COUNT:
        raise ConfigError(f"参与人数必须为 {PERSON_COUNT} 人")

    ids: set[str] = set()
    normalized_people: list[dict[str, str]] = []
    for i, person in enumerate(people):
        if not isinstance(person, dict):
            raise ConfigError(f"第 {i + 1} 个参与人格式错误")
        pid = str(person.get("id", "")).strip()
        name = str(person.get("name", "")).strip()
        if not pid:
            raise ConfigError(f"第 {i + 1} 个参与人缺少 id")
        if not name:
            raise ConfigError(f"第 {i + 1} 个参与人姓名不能为空")
        if pid in ids:
            raise ConfigError(f"参与人 id 重复: {pid}")
        ids.add(pid)
        normalized_people.append({"id": pid, "name": name})

    spots = config.get("spots")
    if not isinstance(spots, list) or len(spots) != 2:
        raise ConfigError("车位配置必须包含园区与公园两类")

    by_type = {s.get("type"): s for s in spots if isinstance(s, dict)}
    if SPOT_TYPE_CAMPUS not in by_type or SPOT_TYPE_PARK not in by_type:
        raise ConfigError("车位类型必须包含 campus 与 park")

    campus = by_type[SPOT_TYPE_CAMPUS]
    park = by_type[SPOT_TYPE_PARK]
    if int(campus.get("count", -1)) != CAMPUS_SPOT_COUNT:
        raise ConfigError(f"园区车位数必须为 {CAMPUS_SPOT_COUNT}")
    if int(park.get("count", -1)) != PARK_SPOT_COUNT:
        raise ConfigError(f"公园车位数必须为 {PARK_SPOT_COUNT}")

    campus_label = str(campus.get("label", "园区车位")).strip() or "园区车位"
    park_label = str(park.get("label", "公园车位")).strip() or "公园车位"

    rules_text = config.get("rules_text", DEFAULT_RULES_TEXT)
    if not isinstance(rules_text, str) or not rules_text.strip():
        raise ConfigError("规则说明不能为空")

    return {
        "people": normalized_people,
        "spots": [
            {"type": SPOT_TYPE_CAMPUS, "label": campus_label, "count": CAMPUS_SPOT_COUNT},
            {"type": SPOT_TYPE_PARK, "label": park_label, "count": PARK_SPOT_COUNT},
        ],
        "rules_text": rules_text.strip(),
    }


def ensure_state_shape(state: dict[str, Any], people: list[dict[str, Any]]) -> dict[str, Any]:
    """Reconcile people_state keys with current people ids (names may change)."""
    people_state = state.get("people_state") or {}
    new_ps: dict[str, dict[str, Any]] = {}
    for p in people:
        pid = p["id"]
        existing = people_state.get(pid) or {}
        new_ps[pid] = {
            "consecutive_wins": int(existing.get("consecutive_wins", 0)),
            "is_bye_next": bool(existing.get("is_bye_next", False)),
        }
    return {
        "draw_count": int(state.get("draw_count", 0)),
        "people_state": new_ps,
        "current": state.get("current"),
        "last_winners": list(state.get("last_winners") or []),
    }


class DataStore:
    """Thread-safe access to app_config / state / history under data_dir."""

    def __init__(self, root: Path | None = None):
        self.root = root or project_root()
        self.data_dir = resolve_data_dir(self.root)
        self.config_path = self.data_dir / "app_config.json"
        self.state_path = self.data_dir / "state.json"
        self.history_path = self.data_dir / "history.json"
        self.ensure_files()

    def ensure_files(self) -> None:
        with _lock:
            if not self.config_path.exists():
                _write_json(self.config_path, default_app_config())
            config = validate_app_config(_read_json(self.config_path, default_app_config()))
            if not self.state_path.exists():
                _write_json(self.state_path, default_state(config["people"]))
            else:
                state = ensure_state_shape(
                    _read_json(self.state_path, default_state(config["people"])),
                    config["people"],
                )
                _write_json(self.state_path, state)
            if not self.history_path.exists():
                _write_json(self.history_path, default_history())

    def load_all(self) -> tuple[dict[str, Any], dict[str, Any], list[Any]]:
        with _lock:
            config = validate_app_config(_read_json(self.config_path, default_app_config()))
            state = ensure_state_shape(
                _read_json(self.state_path, default_state(config["people"])),
                config["people"],
            )
            history = _read_json(self.history_path, default_history())
            if not isinstance(history, list):
                history = []
            return config, state, history

    def save_config(self, config: dict[str, Any]) -> dict[str, Any]:
        normalized = validate_app_config(config)
        with _lock:
            old_config = validate_app_config(_read_json(self.config_path, default_app_config()))
            old_ids = [p["id"] for p in old_config["people"]]
            new_ids = [p["id"] for p in normalized["people"]]
            if old_ids != new_ids:
                raise ConfigError("不允许增删或重排参与人 id，仅可修改姓名")
            _write_json(self.config_path, normalized)
            state = ensure_state_shape(
                _read_json(self.state_path, default_state(normalized["people"])),
                normalized["people"],
            )
            _write_json(self.state_path, state)
        return normalized

    def save_state_and_history(self, state: dict[str, Any], history: list[Any]) -> None:
        with _lock:
            config = validate_app_config(_read_json(self.config_path, default_app_config()))
            state = ensure_state_shape(state, config["people"])
            _write_json(self.state_path, state)
            _write_json(self.history_path, history)

    def replace_state_and_history(self, state: dict[str, Any], history: list[Any]) -> None:
        """Used by undo: write snapshot state and truncated history."""
        with _lock:
            config = validate_app_config(_read_json(self.config_path, default_app_config()))
            state = ensure_state_shape(state, config["people"])
            _write_json(self.state_path, state)
            _write_json(self.history_path, history)
