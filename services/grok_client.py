"""Универсальный LLM-клиент (DeepSeek по умолчанию, совместим с Grok)."""

import os
import json
from typing import Optional
import requests
from dotenv import load_dotenv
import time
import logging

# Загружаем переменные окружения
load_dotenv()

# Провайдер и endpoint по умолчанию (OpenAI-совместимый API)
DEFAULT_PROVIDER = os.getenv("AI_PROVIDER", "deepseek").strip().lower()
AI_API_BASE_URL = os.getenv(
    "AI_API_BASE_URL",
    "https://api.deepseek.com/v1/chat/completions"
)

# Модель по умолчанию
DEFAULT_MODEL = os.getenv("AI_MODEL", "deepseek-chat")
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

_http_session = requests.Session()
logger = logging.getLogger(__name__)


def get_active_provider() -> str:
    """
    Возвращает активного AI-провайдера для подсказок в UI.
    """
    return DEFAULT_PROVIDER


def get_api_key_hints() -> str:
    """
    Возвращает подсказку по доступным переменным API ключа.
    """
    return "DEEPSEEK_API_KEY (рекомендуется), AI_API_KEY, GROK_API_KEY"


def get_client_headers() -> dict:
    """
    Возвращает заголовки для запросов к LLM API.
    
    Returns:
        dict: Словарь с заголовками Authorization и Content-Type
        
    Raises:
        ValueError: Если API ключ не установлен
    """
    api_key = (
        os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("AI_API_KEY")
        or os.getenv("GROK_API_KEY")
    )
    if not api_key:
        raise ValueError(
            "API ключ не найден в переменных окружения. "
            f"Добавьте одну из переменных: {get_api_key_hints()}."
        )
    
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


def call_grok_chat(
    model: str = DEFAULT_MODEL,
    system_prompt: str = "",
    user_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> str:
    """
    Выполняет запрос к OpenAI-совместимому LLM API для генерации текста.
    
    Args:
        model: Название модели (по умолчанию deepseek-chat)
        system_prompt: Системный промпт, определяющий роль модели
        user_prompt: Пользовательский промпт с заданием
        temperature: Температура генерации (0.0-2.0)
        max_tokens: Максимальное количество токенов в ответе
        
    Returns:
        str: Сгенерированный текст из ответа API
        
    Raises:
        ValueError: Если API ключ отсутствует
        requests.RequestException: При ошибках HTTP-запроса
        RuntimeError: При неожиданном формате ответа API
    """
    try:
        headers = get_client_headers()
    except ValueError as e:
        raise ValueError(str(e))
    
    # Формируем сообщения для API
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    
    # Параметры запроса
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    
    if max_tokens:
        payload["max_tokens"] = max_tokens
    
    try:
        response = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = _http_session.post(
                    AI_API_BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT
                )
                if response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                    logger.warning(
                        "Retryable LLM status %s on attempt %s/%s",
                        response.status_code,
                        attempt,
                        MAX_RETRIES
                    )
                    time.sleep(0.8 * attempt)
                    continue
                response.raise_for_status()
                break
            except requests.exceptions.Timeout:
                if attempt < MAX_RETRIES:
                    logger.warning("LLM timeout on attempt %s/%s", attempt, MAX_RETRIES)
                    time.sleep(0.8 * attempt)
                    continue
                raise
        if response is None:
            raise RuntimeError("LLM API не вернул ответ.")
        
        data = response.json()
        
        # Извлекаем текст из ответа
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "")
            if not content:
                raise RuntimeError("API вернул пустой ответ")
            return content.strip()
        else:
            raise RuntimeError(f"Неожиданный формат ответа API: {data}")
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Ошибка при обращении к LLM API: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            if status_code == 401:
                # Специальная обработка для ошибки авторизации
                error_msg = (
                    "❌ Ошибка авторизации (401 Unauthorized)\n\n"
                    "Возможные причины:\n"
                    "1. API ключ не установлен или неверный\n"
                    "2. Файл .env отсутствует или не загружается\n"
                    "3. API ключ истёк или был отозван\n"
                    "4. Используется не тот endpoint для выбранного провайдера\n\n"
                    "Решение:\n"
                    "1. Убедитесь, что файл .env существует в корне проекта\n"
                    f"2. Добавьте ключ в .env: {get_api_key_hints()}\n"
                    "3. Для DeepSeek используйте https://api.deepseek.com/v1/chat/completions\n"
                    "4. Для Grok используйте https://api.x.ai/v1/chat/completions\n"
                    "5. Перезапустите приложение после изменения .env"
                )
            else:
                try:
                    error_detail = e.response.json()
                    error_msg += f"\nДетали: {error_detail}"
                except:
                    error_msg += f"\nHTTP статус: {status_code}"
        raise RuntimeError(error_msg)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Ошибка парсинга JSON ответа: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Неожиданная ошибка: {str(e)}")


def is_text_complete(text: str) -> bool:
    """
    Проверяет, завершён ли текст корректно.
    
    Текст считается завершённым, если последний символ (после пробелов)
    является одним из: '.', '!', '?'
    
    Args:
        text: Текст для проверки
        
    Returns:
        bool: True, если текст завершён, False иначе
    """
    if not text or not text.strip():
        return False
    
    # Убираем пробелы в конце и проверяем последний символ
    text_stripped = text.rstrip()
    if not text_stripped:
        return False
    
    last_char = text_stripped[-1]
    return last_char in ('.', '!', '?')


def refine_generation_if_needed(
    text: str,
    model: str = DEFAULT_MODEL
) -> str:
    """
    Проверяет, завершён ли текст, и если нет — догенерирует завершение.
    
    Эта функция вызывается ТОЛЬКО если текст оборвался (не заканчивается на точку/вопрос/восклицание).
    Она делает дополнительный запрос к модели для завершения текста до ближайшего
    смыслового завершения, не переписывая уже написанное.
    
    Args:
        text: Текст, который может быть оборван
        model: Модель для догенерации (по умолчанию deepseek-chat)
        
    Returns:
        str: Завершённый текст (исходный + дополнение, если было нужно)
        
    Raises:
        ValueError: Если API ключ отсутствует
        RuntimeError: При ошибках API или если догенерация не удалась
    """
    # Проверяем, завершён ли текст
    if is_text_complete(text):
        return text
    
    # Текст оборван — делаем догенерацию
    system_prompt = "Ты — литературный редактор."
    
    user_prompt = f"""Вот текст: 

{text}

Он оборван. Пожалуйста, продолжи его буквально до ближайшего смыслового завершения, одним коротким логичным абзацем. Не начинай текст заново. Не меняй уже написанное. Просто доведи последнюю мысль до конца, закончив на точке."""

    try:
        # Делаем запрос для догенерации
        continuation = call_grok_chat(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=200  # Ограничиваем догенерацию небольшим объёмом
        )
        
        # Убираем пробелы в начале продолжения, если они есть
        continuation = continuation.lstrip()
        
        # Соединяем исходный текст и продолжение
        # Если исходный текст не заканчивается пробелом, добавляем его
        if text.rstrip() and not text.rstrip().endswith((' ', '\n', '\t')):
            result = text.rstrip() + " " + continuation
        else:
            result = text.rstrip() + continuation
        
        # Проверяем, что результат теперь завершён
        if is_text_complete(result):
            return result
        else:
            # Если даже после догенерации текст не завершён, добавляем точку
            return result.rstrip() + "."
            
    except Exception as e:
        # Если догенерация не удалась, просто добавляем точку к исходному тексту
        # Это лучше, чем оставлять текст оборванным
        return text.rstrip() + "."
