"""Компонент для построения Radar Chart (радарной диаграммы)."""

import plotly.graph_objects as go
from typing import Dict, Optional


def build_radar_chart(
    base_profile: Dict[str, int],
    text_profile: Optional[Dict[str, int]] = None
) -> go.Figure:
    """
    Строит радарную диаграмму для сравнения профилей жанра и текста.
    
    Args:
        base_profile: Базовый профиль жанра (ось -> значение 0-100)
        text_profile: Профиль текста для сравнения (опционально)
        
    Returns:
        go.Figure: Объект Figure для отображения в Streamlit
    """
    # Получаем все оси (ключи словаря)
    categories = list(base_profile.keys())
    
    # Значения базового профиля
    base_values = [base_profile[cat] for cat in categories]
    
    # Создаём фигуру
    fig = go.Figure()
    
    # Добавляем базовый профиль (идеальный профиль жанра)
    fig.add_trace(go.Scatterpolar(
        r=base_values + [base_values[0]],  # Замыкаем полигон
        theta=categories + [categories[0]],
        fill='toself',
        name='Профиль жанра',
        line=dict(color='rgb(31, 119, 180)', width=2),
        fillcolor='rgba(31, 119, 180, 0.25)'
    ))
    
    # Если передан профиль текста, добавляем его
    if text_profile:
        text_values = [text_profile.get(cat, 0) for cat in categories]
        fig.add_trace(go.Scatterpolar(
            r=text_values + [text_values[0]],  # Замыкаем полигон
            theta=categories + [categories[0]],
            fill='toself',
            name='Профиль текста',
            line=dict(color='rgb(255, 127, 14)', width=2),
            fillcolor='rgba(255, 127, 14, 0.25)'
        ))
    
    # Настраиваем layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10),
                gridcolor='rgba(200, 200, 200, 0.3)'
            ),
            angularaxis=dict(
                tickfont=dict(size=11),
                rotation=90
            )
        ),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.15
        ),
        margin=dict(l=50, r=150, t=30, b=50),
        height=500
    )
    
    return fig





