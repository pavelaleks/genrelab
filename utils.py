"""Общие утилиты приложения."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json


PROJECT_ROOT = Path(__file__).resolve().parent


def load_prompt(relative_path: str, fallback: str = "") -> str:
    """Читает текстовый промпт от корня проекта."""
    prompt_path = PROJECT_ROOT / relative_path
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return fallback


def extract_json_object(raw_text: str) -> Dict[str, Any]:
    """
    Извлекает первый корректный JSON-объект из текстового ответа модели.
    """
    text = (raw_text or "").strip()
    if not text:
        raise json.JSONDecodeError("Пустой ответ модели", "", 0)

    # Быстрый путь: ответ уже чистый JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Надёжный путь: поиск объекта по балансу фигурных скобок
    start = -1
    depth = 0
    for idx, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start != -1:
                    candidate = text[start:idx + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        start = -1
                        continue

    raise json.JSONDecodeError("Не удалось извлечь JSON-объект из ответа", text, 0)


def init_session_state(defaults: Dict[str, Any]) -> None:
    """Инициализирует значения в st.session_state по словарю defaults."""
    # Локальный импорт, чтобы модуль оставался независимым вне Streamlit runtime.
    import streamlit as st

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def trim_list_state(key: str, max_items: int) -> None:
    """Обрезает list в session_state до последних max_items элементов."""
    import streamlit as st

    value = st.session_state.get(key)
    if isinstance(value, list) and len(value) > max_items:
        st.session_state[key] = value[-max_items:]
