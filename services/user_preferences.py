"""
Simple persistent storage for per-user bot preferences.
"""

from __future__ import annotations

import json
import logging
from typing import TypedDict

from config import settings

logger = logging.getLogger(__name__)


class UserPreferences(TypedDict):
    mode: str
    voice_enabled: bool


DEFAULT_PREFERENCES: UserPreferences = {
    "mode": "подробно",
    "voice_enabled": False,
}


class UserPreferencesStore:
    def __init__(self) -> None:
        self.path = settings.user_settings_path

    def _load_all(self) -> dict[str, UserPreferences]:
        if not self.path.exists():
            return {}

        try:
            with self.path.open("r", encoding="utf-8") as file:
                raw_data = json.load(file)
        except Exception as error:
            logger.warning("Could not load user preferences from %s: %s", self.path, error)
            return {}

        if not isinstance(raw_data, dict):
            return {}

        preferences: dict[str, UserPreferences] = {}
        for user_id, data in raw_data.items():
            if not isinstance(data, dict):
                continue

            preferences[user_id] = {
                "mode": data.get("mode", DEFAULT_PREFERENCES["mode"]),
                "voice_enabled": bool(data.get("voice_enabled", DEFAULT_PREFERENCES["voice_enabled"])),
            }

        return preferences

    def _save_all(self, data: dict[str, UserPreferences]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def get(self, user_id: int) -> UserPreferences:
        data = self._load_all()
        return data.get(str(user_id), DEFAULT_PREFERENCES.copy())

    def update(self, user_id: int, **changes: object) -> UserPreferences:
        data = self._load_all()
        key = str(user_id)
        current = data.get(key, DEFAULT_PREFERENCES.copy())
        updated: UserPreferences = {
            "mode": str(changes.get("mode", current["mode"])),
            "voice_enabled": bool(changes.get("voice_enabled", current["voice_enabled"])),
        }
        data[key] = updated
        self._save_all(data)
        return updated

    def reset(self, user_id: int) -> UserPreferences:
        return self.update(user_id, **DEFAULT_PREFERENCES)

    def count_users(self) -> int:
        return len(self._load_all())


user_preferences_store = UserPreferencesStore()
