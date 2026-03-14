"""Модуль для анализа соответствия текстов жанрам и параметрам."""

import json
from dataclasses import dataclass
from typing import Dict, Optional, List
from genres.schema import Genre
from services.grok_client import call_grok_chat
from utils import extract_json_object


@dataclass
class AnalysisParams:
    """Параметры для анализа текста."""
    
    tonality: str
    focus: str
    descriptiveness: int  # 0-100
    characters_count: int
    has_moral: bool
    setting: str
    target_length: int


def build_analysis_prompt(genre: Genre, params: AnalysisParams, text: str) -> str:
    """
    Собирает промпт для анализа текста.
    
    Args:
        genre: Объект Genre с описанием жанра
        params: Параметры, которые должны были быть учтены при генерации
        text: Текст для анализа
        
    Returns:
        str: Собранный промпт для LLM
    """
    moral_text = "да" if params.has_moral else "нет"
    
    prompt = f"""Проанализируй следующий текст как пример жанра "{genre.name}".

ЖАНР:
Название: {genre.name}
Описание: {genre.description}
Типичные признаки: {', '.join(genre.typical_features)}
Структурная схема: {' → '.join(genre.structural_schema)}

ЗАДАННЫЕ ПАРАМЕТРЫ:
- Тональность: {params.tonality}
- Фокус повествования: {params.focus}
- Уровень описательности: {params.descriptiveness}/100
- Количество персонажей: {params.characters_count}
- Наличие моральной развязки: {moral_text}
- Сеттинг/эпоха: {params.setting}
- Целевой объём: {params.target_length} слов

ТЕКСТ ДЛЯ АНАЛИЗА:
{text}

ЗАДАНИЕ:
Оцени текст по следующим критериям:
1. Соответствие жанру (genre_fit): насколько текст соответствует жанру "{genre.name}" и его типичным признакам
2. Соответствие тональности (tonality_fit): насколько текст соответствует заданной тональности "{params.tonality}"
3. Соответствие структуре (structure_fit): насколько текст следует структурной схеме жанра
4. Соответствие стилю (style_fit): общее соответствие стилистическим требованиям

Также оцени текст по осям радара (0-100):
- сюжетность: насколько развит сюжет
- описательность: насколько детально описаны места, люди, события
- конфликтность: насколько выражен конфликт
- лиричность: насколько выражены эмоции, лирические отступления
- условность: насколько условен/фантастичен текст
- нравственная окраска: насколько выражена моральная позиция
- социальность: насколько выражен социальный контекст

Верни ТОЛЬКО валидный JSON без дополнительного текста, со следующей структурой:
{{
  "scores": {{
    "genre_fit": <число 0-100>,
    "tonality_fit": <число 0-100>,
    "structure_fit": <число 0-100>,
    "style_fit": <число 0-100>
  }},
  "radar": {{
    "сюжетность": <число 0-100>,
    "описательность": <число 0-100>,
    "конфликтность": <число 0-100>,
    "лиричность": <число 0-100>,
    "условность": <число 0-100>,
    "нравственная окраска": <число 0-100>,
    "социальность": <число 0-100>
  }},
  "commentary": {{
    "overall": "<общее объяснение соответствия текста жанру и параметрам>",
    "strengths": ["<сильная сторона 1>", "<сильная сторона 2>", ...],
    "weaknesses": ["<слабая сторона 1>", "<слабая сторона 2>", ...],
    "recommendations": ["<рекомендация 1>", "<рекомендация 2>", ...]
  }}
}}"""
    
    return prompt


def analyze_text_with_llm(
    genre: Genre,
    params: AnalysisParams,
    text: str
) -> Dict:
    """
    Анализирует текст с помощью LLM на соответствие жанру и параметрам.
    
    Args:
        genre: Объект Genre
        params: Параметры анализа
        text: Текст для анализа
        
    Returns:
        Dict: Словарь с результатами анализа (scores, radar, commentary)
    """
    system_prompt = """Ты — опытный литературовед и преподаватель литературы. 
Твоя задача — анализировать тексты на соответствие литературным жанрам и заданным параметрам.
Будь точным, объективным и конструктивным в своих оценках.
Всегда возвращай валидный JSON без дополнительного текста."""
    
    user_prompt = build_analysis_prompt(genre, params, text)
    
    try:
        response = call_grok_chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3  # Низкая температура для более точного анализа
        )
        
        result = extract_json_object(response)
        
        # Валидация и нормализация результата
        return _normalize_analysis_result(result)
        
    except json.JSONDecodeError as e:
        # Если не удалось распарсить JSON, возвращаем безопасную структуру
        return _get_safe_analysis_result(
            error=f"Ошибка парсинга JSON: {str(e)}. Ответ модели: {response[:200]}"
        )
    except Exception as e:
        return _get_safe_analysis_result(error=str(e))


def _normalize_analysis_result(result: Dict) -> Dict:
    """
    Нормализует результат анализа, заполняя недостающие поля.
    
    Args:
        result: Словарь с результатом анализа
        
    Returns:
        Dict: Нормализованный словарь
    """
    # Базовые значения по умолчанию
    default_scores = {
        "genre_fit": 50,
        "tonality_fit": 50,
        "structure_fit": 50,
        "style_fit": 50
    }
    
    default_radar = {
        "сюжетность": 50,
        "описательность": 50,
        "конфликтность": 50,
        "лиричность": 50,
        "условность": 50,
        "нравственная окраска": 50,
        "социальность": 50
    }
    
    default_commentary = {
        "overall": "Анализ выполнен.",
        "strengths": [],
        "weaknesses": [],
        "recommendations": []
    }
    
    # Объединяем с переданными значениями
    normalized = {
        "scores": {**default_scores, **result.get("scores", {})},
        "radar": {**default_radar, **result.get("radar", {})},
        "commentary": {**default_commentary, **result.get("commentary", {})}
    }
    
    # Ограничиваем значения 0-100
    for key in normalized["scores"]:
        normalized["scores"][key] = max(0, min(100, int(normalized["scores"][key])))
    
    for key in normalized["radar"]:
        normalized["radar"][key] = max(0, min(100, int(normalized["radar"][key])))
    
    return normalized


def _get_safe_analysis_result(error: str = "") -> Dict:
    """
    Возвращает безопасную структуру результата при ошибке.
    
    Args:
        error: Сообщение об ошибке
        
    Returns:
        Dict: Безопасная структура с сообщением об ошибке
    """
    return {
        "error": bool(error),
        "scores": {
            "genre_fit": 0,
            "tonality_fit": 0,
            "structure_fit": 0,
            "style_fit": 0
        },
        "radar": {
            "сюжетность": 50,
            "описательность": 50,
            "конфликтность": 50,
            "лиричность": 50,
            "условность": 50,
            "нравственная окраска": 50,
            "социальность": 50
        },
        "commentary": {
            "overall": f"Ошибка при анализе: {error}" if error else "Не удалось выполнить анализ.",
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }
    }


def build_break_genre_prompt(genre: Genre, params: AnalysisParams, text: str) -> str:
    """
    Собирает промпт для режима "сломать жанр".
    
    Args:
        genre: Объект Genre
        params: Параметры
        text: Исходный текст
        
    Returns:
        str: Промпт для модификации текста
    """
    prompt = f"""Ты — опытный литературный автор и преподаватель. 

ИСХОДНЫЙ ТЕКСТ (написан в жанре "{genre.name}"):
{text}

ЗАДАНИЕ:
Модифицируй этот текст так, чтобы он ОСОЗНАННО НАРУШИЛ жанровые нормы жанра "{genre.name}", 
но при этом сохранил УЗНАВАЕМЫЕ ЭЛЕМЕНТЫ этого жанра.

Что нужно сделать:
1. Нарушь типичные признаки жанра: {', '.join(genre.typical_features[:3])}
2. Измени структурную схему: вместо {' → '.join(genre.structural_schema)} используй другую структуру
3. Сохрани некоторые узнаваемые элементы жанра, чтобы было видно, что это эксперимент с "{genre.name}"
4. Сделай это осознанно и интересно — покажи, как можно "сломать" жанр, сохраняя связь с ним

Цель: помочь студентам понять границы жанра через их нарушение.

Верни только модифицированный текст, без дополнительных пояснений."""
    
    return prompt


def break_genre_with_llm(
    genre: Genre,
    params: AnalysisParams,
    text: str
) -> str:
    """
    Модифицирует текст так, чтобы он нарушал жанровые нормы.
    
    Args:
        genre: Объект Genre
        params: Параметры
        text: Исходный текст
        
    Returns:
        str: Модифицированный текст
    """
    system_prompt = """Ты — опытный литературный автор и преподаватель литературы. 
Твоя задача — создавать экспериментальные тексты, которые нарушают жанровые конвенции, 
но сохраняют связь с исходным жанром. Это учебное упражнение для понимания границ жанров."""
    
    user_prompt = build_break_genre_prompt(genre, params, text)
    
    try:
        response = call_grok_chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.8  # Более высокая температура для креативности
        )
        return response.strip()
    except Exception as e:
        raise RuntimeError(str(e)) from e

