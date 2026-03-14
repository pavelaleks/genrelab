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


def _html_esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_api_setup_help(active_provider: str, api_key_hints: str) -> None:
    st.warning("⚠️ **API ключ не найден!**")
    hints_esc = _html_esc(api_key_hints)
    prov_esc = _html_esc(active_provider)
    st.markdown(
        f"""
        <details open style="margin-bottom:1rem;">
            <summary style="cursor:pointer; font-weight:600;">📋 Как настроить API ключ</summary>
            <div style="margin-top:0.75rem; padding-left:0.5rem;">
                <p>Для работы приложения необходим API ключ LLM-провайдера. По умолчанию используется <strong>DeepSeek</strong>.</p>
                <ol style="margin:0.25rem 0 0 1.25rem; padding:0;">
                    <li>Создайте файл <code>.env</code> в корне проекта</li>
                    <li>Добавьте строку: <code>DEEPSEEK_API_KEY=your_actual_deepseek_api_key_here</code></li>
                    <li>Получите ключ: <a href="https://platform.deepseek.com/api_keys" target="_blank">DeepSeek</a>, <a href="https://console.x.ai" target="_blank">Grok</a></li>
                    <li>Перезапустите приложение</li>
                </ol>
                <p style="margin-top:0.5rem;">Поддерживаются ключи: <code>{hints_esc}</code>. Текущий провайдер: <code>{prov_esc}</code></p>
            </div>
        </details>
        """,
        unsafe_allow_html=True,
    )


def render_api_key_error_block() -> None:
    """Компактный переиспользуемый блок-инструкция при ошибке ключа."""
    st.markdown(
        """
        <details style="margin-bottom:1rem;">
            <summary style="cursor:pointer; font-weight:600;">📋 Инструкция по настройке API ключа</summary>
            <div style="margin-top:0.75rem; padding-left:0.5rem;">
                <p><strong>Шаг 1:</strong> Создайте файл <code>.env</code> в корне проекта (если его нет).</p>
                <p><strong>Шаг 2:</strong> Добавьте строку: <code>DEEPSEEK_API_KEY=your_actual_deepseek_api_key_here</code></p>
                <p><strong>Шаг 3:</strong> Получите ключ: <a href="https://platform.deepseek.com/api_keys" target="_blank">DeepSeek</a>, <a href="https://console.x.ai" target="_blank">Grok</a></p>
                <p><strong>Шаг 4:</strong> Перезапустите приложение после изменения <code>.env</code></p>
            </div>
        </details>
        """,
        unsafe_allow_html=True,
    )
