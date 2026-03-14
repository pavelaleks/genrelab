"""Модуль для трансформации текста между различными медиаформатами (Form Shifter)."""

import json
from pathlib import Path
from typing import Dict, Optional
from services.grok_client import call_grok_chat, DEFAULT_MODEL, refine_generation_if_needed
from narrative.load_balance import handle_grok_error, validate_text_length


def load_transform_prompt() -> str:
    """
    Загружает системный промпт для трансформации медиума.
    
    Returns:
        str: Содержимое промпта
    """
    prompt_path = Path("narrative/prompts/transform_prompt.txt")
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return (
            "Ты — эксперт по медиатеории. Преобразуй текст в новый медиаформат, "
            "адаптируя структуру, фокализацию и стиль. Верни ТОЛЬКО валидный JSON."
        )


def transform_text(
    text: str,
    target_format: str,
    genre: Optional[str] = None,
    tonality: Optional[str] = None,
    model: str = DEFAULT_MODEL
) -> Dict:
    """
    Преобразует текст в новый медиаформат.
    
    Args:
        text: Исходный текст для преобразования
        target_format: Целевой формат (пьеса, сценарий, подкаст, комикс, визуальный роман, 
                      игровая сцена, дневниковая запись, соцсетевой пост, поэтическая версия)
        genre: Жанр из панели настроек (опционально), чтобы сохранять жанровую окраску
        tonality: Тональность из панели настроек (опционально)
        model: Модель для генерации (по умолчанию deepseek-chat)
        
    Returns:
        Dict: Преобразованный текст и объяснение изменений в формате JSON
        
    Raises:
        ValueError: При ошибках валидации или парсинга JSON
        RuntimeError: При ошибках API
    """
    # Валидация длины текста
    is_valid, error_msg = validate_text_length(text)
    if not is_valid:
        raise ValueError(error_msg)
    
    system_prompt = load_transform_prompt()
    
    style_context = ""
    if genre or tonality:
        parts = []
        if genre:
            parts.append(f"Жанр: {genre}")
        if tonality:
            parts.append(f"Тональность: {tonality}")
        style_context = f"\nСохраняй при преобразовании: {', '.join(parts)}.\n\n"
    
    format_descriptions = {
        "пьеса": "Пьеса: диалоги, ремарки, списки персонажей, акты и сцены",
        "сценарий": "Сценарий: формат киносценария, кадры, ракурсы, диалоги",
        "подкаст": "Подкаст: разговорный стиль, обращение к слушателю, естественные паузы",
        "комикс": "Комикс: короткие описания панелей, реплики в пузырях, визуальные указания",
        "визуальный роман": "Визуальный роман: описание сцен, выборы, внутренние монологи",
        "игровая сцена": "Игровая сцена: интерактивные элементы, описания действий, ветвления",
        "дневниковая запись": "Дневниковая запись: персональный тон, датирование, рефлексия",
        "соцсетевой пост": "Соцсетевой пост: краткость, хештеги, обращение к аудитории",
        "поэтическая версия": "Поэтическая версия: стихотворная форма, ритм, образность"
    }
    
    format_desc = format_descriptions.get(target_format.lower(), target_format)
    
    user_prompt = f"""Преобразуй следующий текст в формат: {target_format}

{format_desc}
{style_context}Исходный текст:

{text}

Преобразуй текст в новый формат, адаптируя структуру, фокализацию и стиль под специфику формата.

Верни ТОЛЬКО валидный JSON в следующем формате:
{{
  "result_text": "Преобразованный текст в новом формате",
  "explanation": {{
    "changed_structure": "Как изменилась структура текста при переходе к новому формату (30-80 слов)",
    "changed_focalization": "Как изменилась фокализация (перспектива, точка зрения) (30-80 слов)",
    "changed_style": "Как изменился стиль (регистр, лексика, синтаксис) (30-80 слов)",
    "new_effect": "Какой новый эффект создаёт новый формат, что добавляет или убирает (30-80 слов)"
  }}
}}

Верни ТОЛЬКО валидный JSON, без markdown-разметки."""

    try:
        response = handle_grok_error(
            call_grok_chat,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=2000
        )
        
        # Парсим JSON из ответа
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            transformation = json.loads(response)
        except json.JSONDecodeError as e:
            # Если не удалось распарсить, пробуем найти JSON внутри текста
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                transformation = json.loads(json_match.group())
            else:
                raise ValueError(
                    f"Не удалось распарсить JSON из ответа модели. "
                    f"Ошибка: {str(e)}. Ответ: {response[:200]}..."
                )
        
        # Валидация структуры
        if not isinstance(transformation, dict):
            raise ValueError("Трансформация должна быть словарём.")
        
        if "result_text" not in transformation:
            raise ValueError("Трансформация должна содержать поле 'result_text'.")
        
        if "explanation" not in transformation:
            raise ValueError("Трансформация должна содержать поле 'explanation'.")
        
        # Улучшаем завершённость преобразованного текста
        result_text = transformation.get("result_text", "")
        if result_text:
            result_text = refine_generation_if_needed(result_text, model=model)
            transformation["result_text"] = result_text
        
        return transformation
        
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Ошибка при трансформации текста: {str(e)}")
