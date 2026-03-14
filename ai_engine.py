"""Тонкий orchestration-слой для AI-вызовов."""

from __future__ import annotations

import time
from typing import Generator

from services.grok_client import call_grok_chat, refine_generation_if_needed


def generate_text(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.8,
    max_tokens: int | None = None,
    ensure_complete: bool = True
) -> str:
    """Единая точка генерации текста."""
    text = call_grok_chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens
    )
    if ensure_complete:
        return refine_generation_if_needed(text)
    return text


def stream_text(text: str, chunk_words: int = 18, delay_s: float = 0.02) -> Generator[str, None, None]:
    """
    Псевдо-стриминг для Streamlit st.write_stream.

    Используется как UX-улучшение, пока API-стриминг не подключён.
    """
    words = (text or "").split()
    if not words:
        return
    for i in range(0, len(words), chunk_words):
        chunk = " ".join(words[i:i + chunk_words]) + " "
        yield chunk
        if delay_s > 0:
            time.sleep(delay_s)
