"""Модуль для генерации сюжетных структур (Plot Builder)."""

import json
from pathlib import Path
from typing import Dict, List, Optional
from services.grok_client import call_grok_chat, DEFAULT_MODEL
from narrative.load_balance import handle_grok_error


def load_plot_prompt() -> str:
    """
    Загружает системный промпт для генерации сюжетных структур.
    
    Returns:
        str: Содержимое промпта
    """
    prompt_path = Path("narrative/prompts/plot_prompt.txt")
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return (
            "Ты — профессиональный нарратолог. Создай структурированную сюжетную схему в формате JSON, "
            "где каждый узел представляет ключевую сцену, событие или поворот сюжета. "
            "Верни ТОЛЬКО валидный JSON, без дополнительных комментариев."
        )


def generate_plot_structure(
    structure_type: str,
    num_nodes: int,
    genre: str,
    style: str,
    era: str,
    model: str = DEFAULT_MODEL
) -> Dict:
    """
    Генерирует сюжетную структуру на основе параметров.
    
    Args:
        structure_type: Тип структуры (linear, branching, circular, mosaic, Rashomon, split-perspective, epistolary)
        num_nodes: Количество узлов (3-15)
        genre: Жанр
        style: Стилистика
        era: Эпоха
        model: Модель для генерации (по умолчанию grok-4-fast-reasoning)
        
    Returns:
        Dict: Структура сюжета в формате JSON с узлами и связями
        
    Raises:
        ValueError: При ошибках парсинга JSON
        RuntimeError: При ошибках API
    """
    system_prompt = load_plot_prompt()
    
    user_prompt = f"""Создай сюжетную структуру со следующими параметрами:

- Тип структуры: {structure_type}
- Количество узлов: {num_nodes}
- Жанр: {genre}
- Стилистика: {style}
- Эпоха: {era}

Создай JSON-структуру с узлами и связями. Каждый узел должен иметь:
- node_id (уникальный идентификатор)
- title (заголовок узла, 3-7 слов)
- description (описание сцены, 20-50 слов)
- connections (список ID связанных узлов)

Верни ТОЛЬКО валидный JSON, без markdown-разметки и дополнительных комментариев."""

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
        # Убираем возможные markdown-коды блоков
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            plot_structure = json.loads(response)
        except json.JSONDecodeError as e:
            # Если не удалось распарсить, пробуем найти JSON внутри текста
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                plot_structure = json.loads(json_match.group())
            else:
                raise ValueError(
                    f"Не удалось распарсить JSON из ответа модели. "
                    f"Ошибка: {str(e)}. Ответ: {response[:200]}..."
                )
        
        # Валидация структуры
        if not isinstance(plot_structure, dict):
            raise ValueError("Структура должна быть словарём.")
        
        if "nodes" not in plot_structure:
            raise ValueError("Структура должна содержать поле 'nodes'.")
        
        if not isinstance(plot_structure["nodes"], list):
            raise ValueError("Поле 'nodes' должно быть списком.")
        
        if len(plot_structure["nodes"]) == 0:
            raise ValueError("Структура должна содержать хотя бы один узел.")
        
        # Добавляем metadata, если его нет
        if "metadata" not in plot_structure:
            plot_structure["metadata"] = {
                "structure_type": structure_type,
                "genre": genre,
                "total_nodes": len(plot_structure["nodes"])
            }
        
        return plot_structure
        
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Ошибка при генерации сюжетной структуры: {str(e)}")


def generate_node_text(
    node_id: int,
    node_title: str,
    node_description: str,
    genre: str,
    style: str,
    era: str,
    model: str = DEFAULT_MODEL
) -> str:
    """
    Генерирует текст для конкретного узла сюжета.
    
    Args:
        node_id: ID узла
        node_title: Заголовок узла
        node_description: Описание узла
        genre: Жанр
        style: Стилистика
        era: Эпоха
        model: Модель для генерации (по умолчанию grok-4-fast-reasoning)
        
    Returns:
        str: Сгенерированный текст для узла
        
    Raises:
        RuntimeError: При ошибках API
    """
    system_prompt = (
        "Ты — опытный литературный автор. Создай текст для сцены в заданном жанре "
        "с учётом всех параметров. Текст должен быть завершённым и логически завершённым."
    )
    
    user_prompt = f"""Создай текст для сцены со следующими параметрами:

- Узел: {node_id} — {node_title}
- Описание: {node_description}
- Жанр: {genre}
- Стилистика: {style}
- Эпоха: {era}

Создай завершённый текст этой сцены (100-200 слов). Текст должен быть художественным, 
соответствовать жанру и стилю, и заканчиваться логически завершённым предложением."""

    try:
        response = handle_grok_error(
            call_grok_chat,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.8,
            max_tokens=500
        )
        
        # Проверяем завершённость текста
        from services.grok_client import refine_generation_if_needed
        response = refine_generation_if_needed(response, model=model)
        
        return response
        
    except Exception as e:
        raise RuntimeError(f"Ошибка при генерации текста узла: {str(e)}")
