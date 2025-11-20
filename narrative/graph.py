"""Модуль для визуализации сюжетных графов (story graphs)."""

from typing import Dict, List, Optional

# Защита импорта для plotly
try:
    import plotly.graph_objects as go
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "Библиотека plotly не установлена.\n\n"
        "РЕШЕНИЕ:\n"
        "1. Убедитесь, что виртуальное окружение активировано:\n"
        "   source .venv/bin/activate  # macOS/Linux\n"
        "   .venv\\Scripts\\activate     # Windows\n\n"
        "2. Установите библиотеку:\n"
        "   pip install plotly\n\n"
        "Или установите все зависимости сразу:\n"
        "   pip install -r requirements.txt"
    )

# Защита импорта для networkx
try:
    import networkx as nx
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "Библиотека networkx не установлена.\n\n"
        "РЕШЕНИЕ:\n"
        "1. Убедитесь, что виртуальное окружение активировано:\n"
        "   source .venv/bin/activate  # macOS/Linux\n"
        "   .venv\\Scripts\\activate     # Windows\n\n"
        "2. Установите библиотеку:\n"
        "   pip install networkx\n\n"
        "Или установите все зависимости сразу:\n"
        "   pip install -r requirements.txt"
    )


def build_story_graph(plot_structure: Dict) -> go.Figure:
    """
    Строит визуализацию сюжетного графа на основе структуры.
    
    Args:
        plot_structure: Словарь с узлами и связями структуры
        
    Returns:
        go.Figure: Интерактивный граф Plotly
    """
    # Создаём граф NetworkX
    G = nx.DiGraph()  # Направленный граф
    
    nodes = plot_structure.get("nodes", [])
    structure_type = plot_structure.get("metadata", {}).get("structure_type", "linear")
    
    # Добавляем узлы и связи
    node_positions = {}
    node_labels = {}
    
    for node in nodes:
        node_id = node.get("node_id")
        title = node.get("title", f"Узел {node_id}")
        description = node.get("description", "")
        
        if node_id is not None:
            G.add_node(node_id, title=title, description=description)
            node_labels[node_id] = f"{node_id}: {title}"
            
            # Добавляем связи
            connections = node.get("connections", [])
            for conn_id in connections:
                if isinstance(conn_id, int):
                    G.add_edge(node_id, conn_id)
    
    # Выбираем алгоритм размещения в зависимости от типа структуры
    if structure_type == "circular":
        pos = nx.circular_layout(G)
    elif structure_type == "linear":
        pos = nx.spring_layout(G, k=2, iterations=50)
    elif structure_type == "branching":
        pos = nx.spring_layout(G, k=3, iterations=100)
    else:
        pos = nx.spring_layout(G, k=2.5, iterations=100)
    
    # Преобразуем позиции в список координат
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    # Создаём линии для рёбер
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Создаём узлы
    node_x = []
    node_y = []
    node_text = []
    node_hover = []
    
    for node_id in G.nodes():
        x, y = pos[node_id]
        node_x.append(x)
        node_y.append(y)
        
        node_data = G.nodes[node_id]
        title = node_data.get("title", f"Узел {node_id}")
        description = node_data.get("description", "")
        
        node_text.append(node_labels.get(node_id, str(node_id)))
        node_hover.append(f"<b>{title}</b><br>{description}")
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=node_text,
        textposition="middle center",
        textfont=dict(size=10, color='white'),
        hovertext=node_hover,
        marker=dict(
            showscale=False,
            color='#1f77b4',
            size=40,
            line=dict(width=2, color='white')
        )
    )
    
    # Создаём фигуру
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=dict(
                text=f"Сюжетный граф ({structure_type})",
                x=0.5,
                font=dict(size=16)
            ),
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="Перемещайте узлы для лучшей видимости",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.005, y=-0.002,
                    xanchor="left", yanchor="bottom",
                    font=dict(size=10, color='gray')
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white',
            height=600
        )
    )
    
    return fig


def get_graph_statistics(plot_structure: Dict) -> Dict:
    """
    Вычисляет статистику сюжетного графа.
    
    Args:
        plot_structure: Словарь с узлами и связями структуры
        
    Returns:
        Dict: Статистика графа
    """
    G = nx.DiGraph()
    
    nodes = plot_structure.get("nodes", [])
    
    for node in nodes:
        node_id = node.get("node_id")
        if node_id is not None:
            G.add_node(node_id)
            connections = node.get("connections", [])
            for conn_id in connections:
                if isinstance(conn_id, int):
                    G.add_edge(node_id, conn_id)
    
    stats = {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "average_degree": sum(dict(G.degree()).values()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,
        "is_connected": nx.is_weakly_connected(G) if G.number_of_nodes() > 0 else False,
        "has_cycles": len(list(nx.simple_cycles(G))) > 0 if G.number_of_nodes() > 0 else False
    }
    
    return stats


def export_to_hypertext(tree: dict) -> dict:
    """
    Превращает дерево ветвлений в гипертекстовую структуру.
    
    Args:
        tree: Словарь с узлами дерева {node_id: {text, choices: [{label, target}]}}
        
    Returns:
        dict: Словарь узлов для гипертекстового просмотра {node_id: {text, choices: [{label, target}]}}
    """
    story_nodes = {}
    
    for node_id, node_data in tree.items():
        story_nodes[node_id] = {
            "text": node_data.get("text", ""),
            "choices": []
        }
        
        # ИСПРАВЛЕНИЕ: используем "choices" вместо "children"
        # Поддерживаем оба варианта для обратной совместимости
        choices = node_data.get("choices", [])
        if not choices:
            # Если нет choices, проверяем children (для обратной совместимости)
            choices = node_data.get("children", [])
        
        # Обрабатываем choices напрямую (они уже в правильном формате)
        for choice in choices:
            if isinstance(choice, dict):
                # Формат: {"label": "...", "target": "..."}
                story_nodes[node_id]["choices"].append({
                    "label": choice.get("label", "Продолжить"),
                    "target": choice.get("target", choice.get("id", ""))
                })
            elif isinstance(choice, str):
                # Если дочерний элемент - просто строка (ID следующего узла)
                story_nodes[node_id]["choices"].append({
                    "label": "Продолжить",
                    "target": choice
                })
    
    return story_nodes
