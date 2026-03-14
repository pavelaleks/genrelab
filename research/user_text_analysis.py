"""Модуль для анализа пользовательского текста."""

import json
from typing import Dict, List, Optional
from genres.schema import Genre
from services.grok_client import call_grok_chat, DEFAULT_MODEL
from utils import extract_json_object, load_prompt


def build_user_analysis_prompt(text: str, genres: List[Genre], expected_genre_name: Optional[str] = None) -> str:
    """
    Формирует промпт для анализа пользовательского текста.
    
    Args:
        text: Текст для анализа
        genres: Список жанров из проекта
        expected_genre_name: Ожидаемый жанр из панели настроек (для контекста сравнения)
        
    Returns:
        str: Сформированный промпт
    """
    # Формируем список жанров с описаниями
    genres_list = []
    for genre in genres:
        genres_list.append(
            f"- {genre.name} (id: {genre.id}): {genre.description}\n"
            f"  Типичные признаки: {', '.join(genre.typical_features[:3])}..."
        )
    
    genres_text = "\n".join(genres_list)
    
    genre_context = ""
    if expected_genre_name:
        genre_context = f"\nКОНТЕКСТ: Пользователь выбрал в настройках жанр «{expected_genre_name}». В объяснении жанровой принадлежности укажи, насколько текст соответствует этому жанру или отклоняется от него.\n\n"
    
    prompt = f"""Проанализируй следующий текст по всем литературоведческим аспектам.
{genre_context}ДОСТУПНЫЕ ЖАНРЫ ПРОЕКТА:
{genres_text}

ТЕКСТ ДЛЯ АНАЛИЗА:
{text}

ЗАДАНИЕ:
Проведи полный анализ текста и верни результат строго в формате JSON со следующей структурой:

{{
  "genre_prediction": {{
    "main_genre": "название основного жанра из списка",
    "probabilities": {{
      "Сказка": 0-100,
      "Притча": 0-100,
      "Рассказ": 0-100,
      "Путевой очерк (травелог)": 0-100,
      "Антиутопический фрагмент": 0-100,
      "Научная заметка": 0-100,
      "Дневниковая запись": 0-100
    }},
    "elements_of_genres": {{
      "жанр_1": ["признак1", "признак2"],
      "жанр_2": ["признак1"]
    }},
    "explanation": "подробное объяснение, почему текст относится к основному жанру, с указанием конкретных признаков"
  }},
  "structure": {{
    "type": "линейная / фрагментарная / рамочная / кольцевая / ...",
    "phases": {{
      "exposition": "описание экспозиции или её отсутствия",
      "conflict": "описание завязки/конфликта",
      "development": "описание развития действия",
      "climax": "описание кульминации",
      "resolution": "описание развязки/финала"
    }},
    "comment": "общий комментарий о структуре текста"
  }},
  "narrative": {{
    "narrator_type": "я-повествователь / он-повествователь / всеведущий / ...",
    "focalization": "нулевая / внутренняя / внешняя",
    "focalization_explanation": "объяснение выбора фокализации с примерами из текста",
    "temporal_flow": "прошедшее / настоящее / смешанное / ретроспекция / проспекция",
    "temporal_comment": "комментарий о временной организации текста"
  }},
  "style": {{
    "register": "высокий / средний / низкий / разговорный / ...",
    "lexical_features": ["особенность1", "особенность2", ...],
    "syntactic_features": ["особенность1", "особенность2", ...],
    "rhetorical_devices": ["приём1", "приём2", ...],
    "overall_comment": "общая характеристика стиля"
  }},
  "evidence": [
    {{"aspect": "жанр", "quote": "короткая цитата до 40 слов", "explanation": "что доказывает эта цитата"}},
    {{"aspect": "структура", "quote": "короткая цитата до 40 слов", "explanation": "что доказывает эта цитата"}},
    {{"aspect": "фокализация", "quote": "короткая цитата до 40 слов", "explanation": "что доказывает эта цитата"}},
    {{"aspect": "стиль", "quote": "короткая цитата до 40 слов", "explanation": "что доказывает эта цитата"}}
  ]
}}

ТРЕБОВАНИЯ:
- Все цитаты должны быть точными и взятыми из текста
- Каждое утверждение должно быть подкреплено доказательствами
- Используй профессиональную литературоведческую терминологию
- Верни ТОЛЬКО валидный JSON, без дополнительного текста"""
    
    return prompt


def analyze_user_text(text: str, genres: List[Genre], expected_genre_name: Optional[str] = None) -> Dict:
    """
    Анализирует пользовательский текст с помощью LLM API.
    
    Args:
        text: Текст для анализа
        genres: Список жанров из проекта
        expected_genre_name: Ожидаемый жанр из панели настроек (опционально)
        
    Returns:
        Dict: Словарь с результатами анализа
    """
    # Загружаем системный промпт
    system_prompt = load_prompt(
        "prompts/user_analysis_prompt.txt",
        fallback="""Ты — профессиональный литературовед.
Проведи детальный анализ текста и верни результат строго в формате JSON.""",
    )
    
    # Формируем user_prompt
    user_prompt = build_user_analysis_prompt(text, genres, expected_genre_name=expected_genre_name)
    
    try:
        # Вызываем LLM API
        response = call_grok_chat(
            model=DEFAULT_MODEL,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3  # Низкая температура для более точного анализа
        )
        
        result = extract_json_object(response)
        
        # Валидация и нормализация результата
        return _normalize_analysis_result(result, genres)
        
    except json.JSONDecodeError as e:
        # Если не удалось распарсить JSON, возвращаем безопасную структуру
        return _get_safe_analysis_result(
            error=f"Ошибка парсинга JSON: {str(e)}. Ответ модели: {response[:200] if 'response' in locals() else 'Нет ответа'}",
            genres=genres
        )
    except Exception as e:
        return _get_safe_analysis_result(
            error=str(e),
            genres=genres
        )


def _normalize_analysis_result(result: Dict, genres: List[Genre]) -> Dict:
    """
    Нормализует результат анализа, заполняя недостающие поля.
    
    Args:
        result: Словарь с результатом анализа
        genres: Список жанров для валидации
        
    Returns:
        Dict: Нормализованный словарь
    """
    # Базовые значения по умолчанию
    genre_names = [genre.name for genre in genres]
    default_probabilities = {name: 0 for name in genre_names}
    
    # Нормализуем genre_prediction
    genre_prediction = result.get("genre_prediction", {})
    normalized_genre = {
        "main_genre": genre_prediction.get("main_genre", genre_names[0] if genre_names else "Не определен"),
        "probabilities": {**default_probabilities, **genre_prediction.get("probabilities", {})},
        "elements_of_genres": genre_prediction.get("elements_of_genres", {}),
        "explanation": genre_prediction.get("explanation", "Анализ не выполнен.")
    }
    
    # Ограничиваем вероятности 0-100
    for key in normalized_genre["probabilities"]:
        normalized_genre["probabilities"][key] = max(0, min(100, int(normalized_genre["probabilities"][key])))
    
    # Нормализуем structure
    structure = result.get("structure", {})
    normalized_structure = {
        "type": structure.get("type", "не определена"),
        "phases": {
            "exposition": structure.get("phases", {}).get("exposition", ""),
            "conflict": structure.get("phases", {}).get("conflict", ""),
            "development": structure.get("phases", {}).get("development", ""),
            "climax": structure.get("phases", {}).get("climax", ""),
            "resolution": structure.get("phases", {}).get("resolution", "")
        },
        "comment": structure.get("comment", "")
    }
    
    # Нормализуем narrative
    narrative = result.get("narrative", {})
    normalized_narrative = {
        "narrator_type": narrative.get("narrator_type", "не определен"),
        "focalization": narrative.get("focalization", "не определена"),
        "focalization_explanation": narrative.get("focalization_explanation", ""),
        "temporal_flow": narrative.get("temporal_flow", "не определен"),
        "temporal_comment": narrative.get("temporal_comment", "")
    }
    
    # Нормализуем style
    style = result.get("style", {})
    normalized_style = {
        "register": style.get("register", "не определен"),
        "lexical_features": style.get("lexical_features", []),
        "syntactic_features": style.get("syntactic_features", []),
        "rhetorical_devices": style.get("rhetorical_devices", []),
        "overall_comment": style.get("overall_comment", "")
    }
    
    # Нормализуем evidence
    evidence = result.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = []
    
    return {
        "genre_prediction": normalized_genre,
        "structure": normalized_structure,
        "narrative": normalized_narrative,
        "style": normalized_style,
        "evidence": evidence
    }


def _get_safe_analysis_result(error: str = "", genres: List[Genre] = None) -> Dict:
    """
    Возвращает безопасную структуру результата при ошибке.
    
    Args:
        error: Сообщение об ошибке
        genres: Список жанров
        
    Returns:
        Dict: Безопасная структура с сообщением об ошибке
    """
    if genres is None:
        genre_names = ["Сказка", "Притча", "Рассказ", "Путевой очерк (травелог)", 
                      "Антиутопический фрагмент", "Научная заметка", "Дневниковая запись"]
    else:
        genre_names = [genre.name for genre in genres]
    
    return {
        "genre_prediction": {
            "main_genre": "Не определен",
            "probabilities": {name: 0 for name in genre_names},
            "elements_of_genres": {},
            "explanation": f"Ошибка при анализе: {error}" if error else "Не удалось выполнить анализ."
        },
        "structure": {
            "type": "не определена",
            "phases": {
                "exposition": "",
                "conflict": "",
                "development": "",
                "climax": "",
                "resolution": ""
            },
            "comment": ""
        },
        "narrative": {
            "narrator_type": "не определен",
            "focalization": "не определена",
            "focalization_explanation": "",
            "temporal_flow": "не определен",
            "temporal_comment": ""
        },
        "style": {
            "register": "не определен",
            "lexical_features": [],
            "syntactic_features": [],
            "rhetorical_devices": [],
            "overall_comment": ""
        },
        "evidence": []
    }

