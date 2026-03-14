"""Модуль для работы с ветвящимися нарративами (Branching Narrative Lab)."""

import json
from pathlib import Path
from typing import Dict, List, Optional
from services.grok_client import call_grok_chat, DEFAULT_MODEL, refine_generation_if_needed
from narrative.load_balance import handle_grok_error


def load_branching_prompt() -> str:
    """
    Загружает системный промпт для генерации ветвлений.
    
    Returns:
        str: Содержимое промпта
    """
    prompt_path = Path("narrative/prompts/branching_prompt.txt")
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return (
            "Ты — эксперт по интерактивным историям. Создай ветвление истории на основе "
            "начальной сцены и варианта выбора. Верни ТОЛЬКО валидный JSON."
        )


def generate_branch(
    initial_scene: str,
    choice: str,
    previous_branches: Optional[List[Dict]] = None,
    genre: Optional[str] = None,
    tonality: Optional[str] = None,
    setting: Optional[str] = None,
    model: str = DEFAULT_MODEL
) -> Dict:
    """
    Генерирует ветвление истории на основе выбора.
    
    Args:
        initial_scene: Начальная сцена или текущее состояние истории
        choice: Вариант выбора, который приводит к ветвлению
        previous_branches: Предыдущие ветвления (для контекста)
        genre: Жанр (из панели настроек), чтобы сохранять стиль
        tonality: Тональность (из панели настроек)
        setting: Сеттинг/эпоха (из панели настроек)
        model: Модель для генерации (по умолчанию deepseek-chat)
        
    Returns:
        Dict: Ветвление с текстом и анализом в формате JSON
        
    Raises:
        ValueError: При ошибках парсинга JSON
        RuntimeError: При ошибках API
    """
    system_prompt = load_branching_prompt()
    
    context_text = ""
    if previous_branches:
        context_text = "\n\nПредыдущие ветвления:\n"
        for i, branch in enumerate(previous_branches[-3:], 1):  # Берём последние 3 ветвления
            context_text += f"{i}. {branch.get('choice', '')} -> {branch.get('branch_text', '')[:100]}...\n"
    
    genre_context = ""
    if genre or tonality or setting:
        parts = []
        if genre:
            parts.append(f"Жанр: {genre}")
        if tonality:
            parts.append(f"Тональность: {tonality}")
        if setting:
            parts.append(f"Сеттинг/эпоха: {setting}")
        genre_context = "\nКонтекст из настроек (сохраняй при продолжении): " + "; ".join(parts) + "\n\n"
    
    user_prompt = f"""{genre_context}Вот начальная сцена или текущее состояние истории:

{initial_scene}

Вариант выбора: {choice}
{context_text}

Создай ветвление истории на основе этого выбора. Продолжи историю, показывая последствия выбора.

Верни ТОЛЬКО валидный JSON в следующем формате:
{{
  "branch_text": "Продолжение истории после выбора (50-200 слов)",
  "analysis": {{
    "genre_shift": "Как выбор повлиял на жанровую окраску (если изменилось)",
    "focalization_change": "Как изменилась фокализация после выбора",
    "style_change": "Как изменился стиль повествования",
    "tension_change": "Как изменилось напряжение и темп (возросло/снизилось/осталось)",
    "branch_effect": "Общий эффект этого ветвления на историю"
  }}
}}

Верни ТОЛЬКО валидный JSON, без markdown-разметки."""

    try:
        response = handle_grok_error(
            call_grok_chat,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.8,
            max_tokens=800
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
            branch = json.loads(response)
        except json.JSONDecodeError as e:
            # Если не удалось распарсить, пробуем найти JSON внутри текста
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                branch = json.loads(json_match.group())
            else:
                raise ValueError(
                    f"Не удалось распарсить JSON из ответа модели. "
                    f"Ошибка: {str(e)}. Ответ: {response[:200]}..."
                )
        
        # Валидация структуры
        if not isinstance(branch, dict):
            raise ValueError("Ветвление должно быть словарём.")
        
        if "branch_text" not in branch:
            raise ValueError("Ветвление должно содержать поле 'branch_text'.")
        
        if "analysis" not in branch:
            raise ValueError("Ветвление должно содержать поле 'analysis'.")
        
        # Улучшаем завершённость текста ветвления
        branch_text = branch.get("branch_text", "")
        if branch_text:
            branch_text = refine_generation_if_needed(branch_text, model=model)
            branch["branch_text"] = branch_text
        
        return branch
        
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Ошибка при генерации ветвления: {str(e)}")


def compare_branches(branches: List[Dict]) -> Dict:
    """
    Сравнивает разные ветвления и анализирует их различия.
    
    Args:
        branches: Список ветвлений для сравнения
        
    Returns:
        Dict: Сравнительный анализ ветвлений
    """
    if not branches:
        return {
            "error": "Нет ветвлений для сравнения"
        }
    
    comparison = {
        "total_branches": len(branches),
        "genre_shifts": [],
        "focalization_changes": [],
        "style_changes": [],
        "tension_changes": [],
        "branch_effects": []
    }
    
    for i, branch in enumerate(branches, 1):
        analysis = branch.get("analysis", {})
        
        comparison["genre_shifts"].append({
            "branch": i,
            "shift": analysis.get("genre_shift", "Не указано")
        })
        
        comparison["focalization_changes"].append({
            "branch": i,
            "change": analysis.get("focalization_change", "Не указано")
        })
        
        comparison["style_changes"].append({
            "branch": i,
            "change": analysis.get("style_change", "Не указано")
        })
        
        comparison["tension_changes"].append({
            "branch": i,
            "change": analysis.get("tension_change", "Не указано")
        })
        
        comparison["branch_effects"].append({
            "branch": i,
            "effect": analysis.get("branch_effect", "Не указано")
        })
    
    return comparison


# ==================== НОВАЯ СИСТЕМА УЗЛОВ ====================

def add_choice_to_node(
    parent_id: str,
    choice_label: str,
    new_node_text: str,
    previous_nodes: Optional[Dict] = None,
    model: str = DEFAULT_MODEL
) -> Dict:
    """
    Добавляет выбор к узлу и создаёт новый дочерний узел.
    
    Args:
        parent_id: ID родительского узла
        choice_label: Текст выбора
        new_node_text: Текст нового узла (последствия выбора)
        previous_nodes: Словарь всех существующих узлов для контекста
        model: Модель для генерации
        
    Returns:
        Dict: Новый узел с текстом и анализом
    """
    system_prompt = load_branching_prompt()
    
    # Получаем контекст родительского узла
    parent_context = ""
    if previous_nodes and parent_id in previous_nodes:
        parent_node = previous_nodes[parent_id]
        parent_context = f"Родительский узел ({parent_id}):\n{parent_node.get('text', '')}\n\n"
    
    user_prompt = f"""{parent_context}Вариант выбора: {choice_label}

Текст нового узла (последствия выбора): {new_node_text}

Создай продолжение истории на основе этого выбора. Развивай сюжет, показывая последствия выбора.

Верни ТОЛЬКО валидный JSON в следующем формате:
{{
  "branch_text": "Продолжение истории после выбора (50-200 слов)",
  "analysis": {{
    "genre_shift": "Как выбор повлиял на жанровую окраску (если изменилось)",
    "focalization_change": "Как изменилась фокализация после выбора",
    "style_change": "Как изменился стиль повествования",
    "tension_change": "Как изменилось напряжение и темп (возросло/снизилось/осталось)",
    "branch_effect": "Общий эффект этого ветвления на историю"
  }}
}}

Верни ТОЛЬКО валидный JSON, без markdown-разметки."""

    try:
        response = handle_grok_error(
            call_grok_chat,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.8,
            max_tokens=800
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
            branch = json.loads(response)
        except json.JSONDecodeError as e:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                branch = json.loads(json_match.group())
            else:
                raise ValueError(
                    f"Не удалось распарсить JSON из ответа модели. "
                    f"Ошибка: {str(e)}. Ответ: {response[:200]}..."
                )
        
        # Валидация структуры
        if not isinstance(branch, dict):
            raise ValueError("Ветвление должно быть словарём.")
        
        if "branch_text" not in branch:
            raise ValueError("Ветвление должно содержать поле 'branch_text'.")
        
        if "analysis" not in branch:
            branch["analysis"] = {}
        
        # Улучшаем завершённость текста
        branch_text = branch.get("branch_text", new_node_text)
        if branch_text:
            branch_text = refine_generation_if_needed(branch_text, model=model)
            branch["branch_text"] = branch_text
        else:
            branch["branch_text"] = new_node_text
        
        return branch
        
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Ошибка при создании узла: {str(e)}")


def get_all_nodes(nodes_dict: Dict) -> List[Dict]:
    """
    Возвращает список всех узлов в структурированном виде.
    
    Args:
        nodes_dict: Словарь узлов {node_id: {text, choices: [...]}}
        
    Returns:
        List[Dict]: Список узлов с метаданными
    """
    result = []
    
    for node_id, node_data in nodes_dict.items():
        choices = node_data.get("choices", [])
        result.append({
            "id": node_id,
            "text": node_data.get("text", ""),
            "choices_count": len(choices),
            "choices": choices
        })
    
    return result


def create_node_structure(node_id: str, text: str, choices: Optional[List[Dict]] = None) -> Dict:
    """
    Создаёт структуру узла в стандартном формате.
    
    Args:
        node_id: ID узла
        text: Текст узла
        choices: Список выборов [{"label": "...", "target": "..."}]
        
    Returns:
        Dict: Структура узла
    """
    return {
        "id": node_id,
        "text": text,
        "choices": choices or []
    }
