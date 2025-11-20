"""Модуль оптимизации для многопользовательской работы с Narrative Playground."""

import time
import streamlit as st
from typing import Optional, Callable

# Максимальная длина вводимого текста (символов)
MAX_CHARS = 2500

# Задержка между запросами (секунды) для предотвращения одновременных запросов от множества пользователей
REQUEST_DELAY = 1.5


def validate_text_length(text: str) -> tuple[bool, Optional[str]]:
    """
    Проверяет длину текста и возвращает результат валидации.
    
    Args:
        text: Текст для проверки
        
    Returns:
        tuple: (is_valid, error_message)
        - is_valid: True, если текст валиден
        - error_message: Сообщение об ошибке, если текст слишком длинный
    """
    if not text:
        return False, "Текст не может быть пустым."
    
    if len(text) > MAX_CHARS:
        return False, (
            f"⚠️ Текст слишком длинный ({len(text)} символов). "
            f"Максимальная длина: {MAX_CHARS} символов. "
            f"Пожалуйста, сократите текст до {MAX_CHARS} символов."
        )
    
    return True, None


def request_with_delay(
    func: Callable,
    *args,
    delay: float = REQUEST_DELAY,
    **kwargs
):
    """
    Выполняет функцию с задержкой для предотвращения одновременных запросов.
    
    Args:
        func: Функция для выполнения
        *args: Позиционные аргументы для функции
        delay: Задержка в секундах (по умолчанию REQUEST_DELAY)
        **kwargs: Именованные аргументы для функции
        
    Returns:
        Результат выполнения функции
    """
    # Задержка перед выполнением запроса
    time.sleep(delay)
    
    return func(*args, **kwargs)


def handle_grok_error(func: Callable, *args, **kwargs):
    """
    Обёртка для обработки ошибок Grok API с fallback-ответами.
    
    Args:
        func: Функция для выполнения
        *args: Позиционные аргументы для функции
        **kwargs: Именованные аргументы для функции
        
    Returns:
        Результат выполнения функции или None при ошибке
        
    Raises:
        RuntimeError: При ошибках API (с обработкой таймаутов и перегрузки)
    """
    try:
        return func(*args, **kwargs)
    except TimeoutError:
        raise RuntimeError(
            "⏱️ Сервер не отвечает. Возможно, он перегружен. "
            "Пожалуйста, подождите немного и попробуйте ещё раз."
        )
    except RuntimeError as e:
        error_str = str(e)
        # Проверяем, является ли это ошибкой перегрузки или таймаута
        if "timeout" in error_str.lower() or "overload" in error_str.lower() or "503" in error_str:
            raise RuntimeError(
                "📡 Сервер загружен, попробуйте ещё раз через несколько секунд."
            )
        # Если это другая ошибка, пробрасываем её дальше
        raise
    except Exception as e:
        raise RuntimeError(
            f"❌ Неожиданная ошибка: {str(e)}. "
            "Пожалуйста, попробуйте ещё раз."
        )


def disable_button_on_click(button_key: str):
    """
    Отключает кнопку после клика для предотвращения двойных кликов.
    
    Args:
        button_key: Ключ кнопки в session_state
    """
    if button_key not in st.session_state:
        st.session_state[button_key] = False
    
    # Устанавливаем флаг, что кнопка была нажата
    st.session_state[button_key] = True


def is_button_disabled(button_key: str) -> bool:
    """
    Проверяет, должна ли кнопка быть отключена.
    
    Args:
        button_key: Ключ кнопки в session_state
        
    Returns:
        bool: True, если кнопка должна быть отключена
    """
    return st.session_state.get(button_key, False)
