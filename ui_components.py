"""Переиспользуемые UI-компоненты Streamlit."""

from __future__ import annotations

import streamlit as st


def render_hero() -> None:
    st.markdown(
        """
<div class="hero-section">
    <h1>✨ NARRALAB</h1>
    <p style="font-size: 1.2rem; margin-bottom: 0.5rem; color: #374151;">Платформа интерактивного сторителлинга с использованием ИИ</p>
    <p style="font-size: 1.05rem; color: #6b7280; margin: 0;">Создавайте, анализируйте и экспериментируйте с историями нового поколения</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_platform_description() -> None:
    st.markdown(
        """
<div style="text-align: center; margin: 1.5rem 0; padding: 1.25rem; background: #ffffff; border-radius: 6px; border: 1px solid #e2e8f0;">
    <p style="font-size: 1.0625rem; color: #374151; margin: 0; line-height: 1.65;">
        <strong style="color: #111827;">NARRALAB</strong> — профессиональная платформа для создания интерактивных историй,
        анализа литературных жанров и экспериментов с трансмедиальным сторителлингом.
        Используйте ИИ для генерации, анализа и трансформации текстов.
    </p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_api_setup_help(active_provider: str, api_key_hints: str) -> None:
    st.warning("⚠️ **API ключ не найден!**")
    with st.expander("📋 Как настроить API ключ", expanded=True):
        st.markdown(
            f"""
Для работы приложения необходим API ключ LLM-провайдера.
По умолчанию используется **DeepSeek**.

1. Создайте файл `.env` в корне проекта  
2. Добавьте строку: `DEEPSEEK_API_KEY=your_actual_deepseek_api_key_here`
3. Получите ключ:
   - DeepSeek: [platform.deepseek.com](https://platform.deepseek.com/api_keys)
   - Grok: [console.x.ai](https://console.x.ai)
4. Перезапустите приложение

Поддерживаются ключи: `{api_key_hints}`  
Текущий провайдер: `{active_provider}`
            """
        )


def render_api_key_error_block() -> None:
    """Компактный переиспользуемый блок-инструкция при ошибке ключа."""
    with st.expander("📋 Инструкция по настройке API ключа"):
        st.markdown(
            """
**Шаг 1:** Создайте файл `.env` в корне проекта (если его нет)

**Шаг 2:** Добавьте строку:
```env
DEEPSEEK_API_KEY=your_actual_deepseek_api_key_here
```

**Шаг 3:** Получите ключ:
- DeepSeek: https://platform.deepseek.com/api_keys
- Grok: https://console.x.ai

**Шаг 4:** Перезапустите приложение после изменения `.env`
"""
        )
