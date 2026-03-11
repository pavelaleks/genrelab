"""NARRALAB: Платформа интерактивного сторителлинга с использованием ИИ."""

import streamlit as st
import os
from pathlib import Path
from genres.schema import get_all_genres, get_genre_by_id, Genre
from genres.rules import AnalysisParams, analyze_text_with_llm, break_genre_with_llm
from services.grok_client import call_grok_chat, refine_generation_if_needed
from components.radar import build_radar_chart
from research.user_text_analysis import analyze_user_text
from narrative.builder import generate_plot_structure, generate_node_text
from narrative.graph import build_story_graph, get_graph_statistics
from narrative.branching import generate_branch, compare_branches
from narrative.transformations import transform_text
from narrative.load_balance import validate_text_length, request_with_delay, handle_grok_error, MAX_CHARS
from narrative.qr_utils import display_qr_code

# Элегантный минималистичный дизайн
st.markdown("""
<style>
/* Спокойная цветовая палитра */
:root {
    --primary: #4a5568;
    --primary-light: #718096;
    --accent: #2d3748;
    --bg-main: #f7fafc;
    --bg-card: #ffffff;
    --text-primary: #2d3748;
    --text-secondary: #4a5568;
    --text-muted: #718096;
    --border: #e2e8f0;
    --border-light: #edf2f7;
    --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

/* Базовые стили */
* {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif !important;
}

body {
    background-color: var(--bg-main) !important;
    color: var(--text-primary) !important;
}

/* Заголовки - чистые и читаемые */
h1, h2, h3, h4, h5, h6 {
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    margin-top: 0 !important;
    margin-bottom: 1rem !important;
    line-height: 1.3 !important;
}

h1 {
    font-size: 2rem !important;
    font-weight: 700 !important;
    margin-bottom: 0.75rem !important;
}

h2 {
    font-size: 1.5rem !important;
    margin-bottom: 0.75rem !important;
}

h3 {
    font-size: 1.25rem !important;
    margin-bottom: 0.5rem !important;
}

/* Основной текст */
p, .stMarkdown, .stText {
    color: var(--text-primary) !important;
    font-size: 1rem !important;
    line-height: 1.6 !important;
    margin-bottom: 1rem !important;
}

/* Поля ввода - чистые и простые */
textarea, input[type="text"], .stTextArea textarea, .stTextInput input,
.stTextArea > div > div > textarea, textarea[disabled],
div[data-baseweb="textarea"] textarea {
    color: var(--text-primary) !important;
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    padding: 0.625rem 0.875rem !important;
    font-size: 0.9375rem !important;
    line-height: 1.5 !important;
    font-weight: 400 !important;
    opacity: 1 !important;
    -webkit-text-fill-color: var(--text-primary) !important;
}

textarea:focus, input[type="text"]:focus {
    border-color: var(--primary) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(74, 85, 104, 0.1) !important;
}

textarea[disabled], textarea:disabled {
    background-color: #f7fafc !important;
    color: var(--text-primary) !important;
    border-color: var(--border-light) !important;
    opacity: 1 !important;
    -webkit-text-fill-color: var(--text-primary) !important;
    cursor: text !important;
}

/* Карточки - минималистичные */
.generated-text, .transformed-text, .analysis-block, .story-node-output {
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    padding: 1.5rem !important;
    border-radius: 8px !important;
    border: 1px solid var(--border) !important;
    box-shadow: var(--shadow-sm) !important;
    margin: 1rem 0 !important;
}

/* Кнопки - спокойные и элегантные */
.stButton > button {
    background-color: var(--primary) !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.625rem 1.25rem !important;
    font-weight: 500 !important;
    font-size: 0.9375rem !important;
    transition: background-color 0.2s ease !important;
    box-shadow: none !important;
}

.stButton > button:hover {
    background-color: var(--accent) !important;
    transform: none !important;
}

.stButton > button[kind="secondary"] {
    background-color: transparent !important;
    color: var(--primary) !important;
    border: 1px solid var(--border) !important;
}

.stButton > button[kind="secondary"]:hover {
    background-color: var(--bg-main) !important;
    border-color: var(--primary) !important;
}

/* Метрики */
[data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.875rem !important;
    color: var(--text-secondary) !important;
    font-weight: 400 !important;
}

[data-testid="stMetricContainer"] {
    background-color: var(--bg-card) !important;
    padding: 1rem !important;
    border-radius: 6px !important;
    border: 1px solid var(--border) !important;
}

/* Progress bars */
.stProgress > div > div > div {
    background-color: var(--primary) !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: var(--bg-card) !important;
    border-right: 1px solid var(--border) !important;
}

/* Tabs - простые и чистые */
[data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
}

[data-baseweb="tab"] {
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    padding: 0.75rem 1rem !important;
    transition: color 0.2s ease !important;
}

[data-baseweb="tab"][aria-selected="true"] {
    color: var(--text-primary) !important;
    border-bottom: 2px solid var(--primary) !important;
    font-weight: 600 !important;
}

/* Info boxes - все типы Streamlit */
div[data-baseweb="notification"] {
    border-radius: 6px !important;
    padding: 1rem !important;
    border: 1px solid !important;
}

/* Info (синий) - стандартный стиль Streamlit */
div[data-baseweb="notification"][data-kind="info"] {
    background-color: #ebf8ff !important;
    border-color: #3182ce !important;
    color: #2c5282 !important;
}

div[data-baseweb="notification"][data-kind="info"] p,
div[data-baseweb="notification"][data-kind="info"] div,
div[data-baseweb="notification"][data-kind="info"] span {
    color: #2c5282 !important;
    opacity: 1 !important;
}

/* Success (зеленый) */
div[data-baseweb="notification"][data-kind="success"] {
    background-color: #f0fff4 !important;
    border-color: #38a169 !important;
    color: #22543d !important;
}

div[data-baseweb="notification"][data-kind="success"] p,
div[data-baseweb="notification"][data-kind="success"] div,
div[data-baseweb="notification"][data-kind="success"] span {
    color: #22543d !important;
    opacity: 1 !important;
}

/* Warning (желтый) */
div[data-baseweb="notification"][data-kind="warning"] {
    background-color: #fffaf0 !important;
    border-color: #d69e2e !important;
    color: #744210 !important;
}

div[data-baseweb="notification"][data-kind="warning"] p,
div[data-baseweb="notification"][data-kind="warning"] div,
div[data-baseweb="notification"][data-kind="warning"] span {
    color: #744210 !important;
    opacity: 1 !important;
}

/* Error (красный) */
div[data-baseweb="notification"][data-kind="error"] {
    background-color: #fff5f5 !important;
    border-color: #e53e3e !important;
    color: #742a2a !important;
}

div[data-baseweb="notification"][data-kind="error"] p,
div[data-baseweb="notification"][data-kind="error"] div,
div[data-baseweb="notification"][data-kind="error"] span {
    color: #742a2a !important;
    opacity: 1 !important;
}

/* Альтернативные селекторы для уведомлений */
.stAlert, .stInfo, .stSuccess, .stWarning, .stError {
    border-radius: 6px !important;
    padding: 1rem !important;
}

.stInfo {
    background-color: #ebf8ff !important;
    border-left: 3px solid #3182ce !important;
    color: #2c5282 !important;
}

.stSuccess {
    background-color: #f0fff4 !important;
    border-left: 3px solid #38a169 !important;
    color: #22543d !important;
}

.stWarning {
    background-color: #fffaf0 !important;
    border-left: 3px solid #d69e2e !important;
    color: #744210 !important;
}

.stError {
    background-color: #fff5f5 !important;
    border-left: 3px solid #e53e3e !important;
    color: #742a2a !important;
}

/* Улучшаем читаемость текста в уведомлениях */
.stAlert p, .stAlert div, .stAlert span,
.stInfo p, .stInfo div, .stInfo span,
.stSuccess p, .stSuccess div, .stSuccess span,
.stWarning p, .stWarning div, .stWarning span,
.stError p, .stError div, .stError span {
    color: inherit !important;
    opacity: 1 !important;
}

/* Selectbox */
[data-baseweb="select"] {
    border-radius: 6px !important;
    border: 1px solid var(--border) !important;
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
}

[data-baseweb="select"]:focus {
    border-color: var(--primary) !important;
}

/* Slider */
.stSlider > div > div {
    background-color: var(--primary) !important;
}

/* Checkbox */
.stCheckbox label {
    color: var(--text-primary) !important;
}

/* File uploader */
.stFileUploader {
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    background-color: var(--bg-card) !important;
}

/* Expander */
[data-baseweb="accordion"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
}

[data-baseweb="accordion"] [data-baseweb="accordion-title"] {
    color: var(--text-primary) !important;
}

[data-baseweb="accordion"] [data-baseweb="accordion-content"] {
    color: var(--text-primary) !important;
}

/* Улучшаем читаемость в expander */
.stExpander {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
}

.stExpander label {
    color: var(--text-primary) !important;
}

.stExpander p, .stExpander div, .stExpander span {
    color: var(--text-primary) !important;
    opacity: 1 !important;
}

/* Spinner */
.stSpinner > div {
    border-color: var(--primary) !important;
    border-top-color: transparent !important;
}

/* Убираем наложения текста */
div[data-testid="stMarkdown"] p,
div[data-testid="stMarkdown"] p *,
.stMarkdown p,
.stMarkdown p * {
    opacity: 1 !important;
    color: var(--text-primary) !important;
    line-height: 1.6 !important;
    margin-bottom: 0.75rem !important;
}

/* Улучшаем читаемость всех текстовых элементов */
div[data-testid="stMarkdown"] strong,
.stMarkdown strong {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
}

div[data-testid="stMarkdown"] code,
.stMarkdown code {
    background-color: #f7fafc !important;
    color: var(--text-primary) !important;
    padding: 0.125rem 0.375rem !important;
    border-radius: 3px !important;
    font-size: 0.875rem !important;
}

/* Улучшаем списки */
div[data-testid="stMarkdown"] ul,
div[data-testid="stMarkdown"] ol,
.stMarkdown ul,
.stMarkdown ol {
    color: var(--text-primary) !important;
    margin-bottom: 0.75rem !important;
}

div[data-testid="stMarkdown"] li,
.stMarkdown li {
    color: var(--text-primary) !important;
    line-height: 1.6 !important;
    margin-bottom: 0.25rem !important;
}

/* Hero секция - минималистичная */
.hero-section {
    background-color: var(--bg-card) !important;
    padding: 2rem !important;
    border-radius: 8px !important;
    border: 1px solid var(--border) !important;
    margin-bottom: 2rem !important;
    text-align: center !important;
    box-shadow: var(--shadow-sm) !important;
}

.hero-section h1 {
    color: var(--text-primary) !important;
    -webkit-text-fill-color: var(--text-primary) !important;
    margin-bottom: 0.5rem !important;
    font-size: 2rem !important;
}

.hero-section p {
    color: var(--text-secondary) !important;
    font-size: 1rem !important;
    margin: 0 !important;
    opacity: 1 !important;
}

/* Дополнительные улучшения для читаемости */
.stText {
    color: var(--text-primary) !important;
}

.stMarkdownContainer {
    color: var(--text-primary) !important;
}

/* Улучшаем таблицы */
.stDataFrame {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
}

/* Улучшаем code blocks */
.stCodeBlock {
    background-color: #f7fafc !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text-primary) !important;
}

/* Улучшаем цитаты */
blockquote {
    border-left: 3px solid var(--primary) !important;
    padding-left: 1rem !important;
    margin-left: 0 !important;
    color: var(--text-secondary) !important;
    font-style: italic !important;
}

/* Адаптация под мобильные */
@media (max-width: 600px) {
    body {
        font-size: 0.9375rem !important;
    }

    h1 {
        font-size: 1.75rem !important;
    }

    h2 {
        font-size: 1.375rem !important;
    }

    .generated-text, .transformed-text, .analysis-block {
        padding: 1.25rem !important;
    }
    
    .hero-section {
        padding: 1.5rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

# Настройка страницы
st.set_page_config(
    page_title="NARRALAB - Платформа интерактивного сторителлинга",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hero секция
st.markdown("""
<div class="hero-section">
    <h1>✨ NARRALAB</h1>
    <p style="font-size: 1.1rem; margin-bottom: 0.5rem; color: #4a5568;">Платформа интерактивного сторителлинга с использованием ИИ</p>
    <p style="font-size: 0.9375rem; color: #718096; margin: 0;">Создавайте, анализируйте и экспериментируйте с историями нового поколения</p>
</div>
""", unsafe_allow_html=True)

# Описание платформы
st.markdown("""
<div style="text-align: center; margin: 1.5rem 0; padding: 1.25rem; background: #ffffff; border-radius: 6px; border: 1px solid #e2e8f0;">
    <p style="font-size: 0.9375rem; color: #4a5568; margin: 0; line-height: 1.6;">
        <strong style="color: #2d3748;">NARRALAB</strong> — это профессиональная платформа для создания интерактивных историй, 
        анализа литературных жанров и экспериментов с трансмедиальным сторителлингом. 
        Используйте возможности искусственного интеллекта для генерации, анализа и трансформации текстов.
    </p>
</div>
""", unsafe_allow_html=True)

# Проверка наличия API ключа
env_path = Path(".env")
api_key = os.getenv("GROK_API_KEY")

if not api_key:
    st.warning("⚠️ **API ключ не найден!**")
    with st.expander("📋 Как настроить API ключ", expanded=True):
        st.markdown("""
        Для работы приложения необходим API ключ от Grok.
        
        **Быстрая настройка:**
        
        1. **Создайте файл `.env`** в корне проекта (там же, где находится `app.py`)
        
        2. **Добавьте в файл `.env`** следующую строку:
           ```
           GROK_API_KEY=your_actual_grok_api_key_here
           ```
        
        3. **Получите API ключ:**
           - Зарегистрируйтесь на [console.x.ai](https://console.x.ai)
           - Перейдите в раздел **API Keys**
           - Создайте новый ключ
           - Скопируйте ключ и вставьте в файл `.env` вместо `your_actual_grok_api_key_here`
        
        4. **Перезапустите приложение** после создания/изменения `.env` файла
        
        ⚠️ **Важно:** 
        - Файл `.env` должен быть в той же директории, что и `app.py`
        - Не добавляйте пробелы вокруг знака `=`
        - Не коммитьте файл `.env` в git (он уже в .gitignore)
        """)
    
    if not env_path.exists():
        st.info(f"💡 Файл `.env` не найден в директории: `{Path.cwd()}`")
    else:
        st.info("💡 Файл `.env` найден, но `GROK_API_KEY` не загружен. Проверьте формат файла.")
    
    st.markdown("---")

st.markdown("---")

# Инициализация session state
if "selected_genre_id" not in st.session_state:
    st.session_state.selected_genre_id = None
if "generated_text" not in st.session_state:
    st.session_state.generated_text = ""
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "broken_text" not in st.session_state:
    st.session_state.broken_text = ""
if "user_text_analysis" not in st.session_state:
    st.session_state.user_text_analysis = None
if "user_text_input" not in st.session_state:
    st.session_state.user_text_input = ""
if "plot_structure" not in st.session_state:
    st.session_state.plot_structure = None
if "branching_history" not in st.session_state:
    st.session_state.branching_history = []
if "branching_scene" not in st.session_state:
    st.session_state.branching_scene = ""
if "transformation_result" not in st.session_state:
    st.session_state.transformation_result = None

# Получаем список жанров
all_genres = get_all_genres()

# ==================== ВКЛАДКИ ====================
tab1, tab2, tab3 = st.tabs(["🎨 Генератор историй", "📊 Анализ текста", "🌳 Narrative Playground"])

# ==================== САЙДБАР ====================
with st.sidebar:
    st.header("⚙️ Настройки")
    
    # Выбор жанра
    genre_options = {genre.name: genre.id for genre in all_genres}
    selected_genre_name = st.selectbox(
        "🎨 Выберите жанр:",
        options=list(genre_options.keys()),
        index=0 if not st.session_state.selected_genre_id else 
              next((i for i, g in enumerate(all_genres) if g.id == st.session_state.selected_genre_id), 0)
    )
    selected_genre_id = genre_options[selected_genre_name]
    st.session_state.selected_genre_id = selected_genre_id
    
    selected_genre = get_genre_by_id(selected_genre_id)
    
    st.markdown("---")
    
    # Параметры генерации
    st.subheader("Параметры текста")
    
    tonality = st.selectbox(
        "Тональность:",
        options=["ироничная", "серьёзная", "трагическая", "философская", "сатирическая"],
        index=1
    )
    
    focus = st.selectbox(
        "Фокус повествования:",
        options=["герой", "мир", "событие", "мысль"],
        index=0
    )
    
    descriptiveness = st.slider(
        "Уровень описательности:",
        min_value=0,
        max_value=100,
        value=50,
        step=5
    )
    
    characters_count = st.slider(
        "Количество персонажей:",
        min_value=1,
        max_value=5,
        value=2,
        step=1
    )
    
    has_moral = st.checkbox(
        "Наличие моральной развязки",
        value=True
    )
    
    setting = st.selectbox(
        "Сеттинг / эпоха:",
        options=[
            "современность",
            "XIX век",
            "неопределённое сказочное время",
            "будущее",
            "тоталитарное государство",
            "другое (укажите в тексте)"
        ],
        index=0
    )
    
    target_length = st.slider(
        "Примерный объём текста (слов):",
        min_value=100,
        max_value=400,
        value=200,
        step=50
    )
    
    # Сохраняем параметры в session state
    st.session_state.params = AnalysisParams(
        tonality=tonality,
        focus=focus,
        descriptiveness=descriptiveness,
        characters_count=characters_count,
        has_moral=has_moral,
        setting=setting,
        target_length=target_length
    )

# ==================== ВКЛАДКА 1: ЛАБОРАТОРИЯ ЖАНРОВ ====================
with tab1:
    # ==================== ОСНОВНАЯ ОБЛАСТЬ ====================
    
    if not selected_genre:
        st.error("Ошибка: жанр не найден.")
        st.stop()
    
    # Блок 1: Описание жанра
    st.header(f"📖 {selected_genre.name}")
    st.markdown(f"""
    <div style='background: #ffffff; padding: 1.5rem; border-radius: 6px; border: 1px solid #e2e8f0; margin-bottom: 1.5rem;'>
        <p style='font-size: 0.9375rem; color: #4a5568; margin: 0; line-height: 1.6;'>{selected_genre.description}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Типичные признаки:**")
        for feature in selected_genre.typical_features:
            st.markdown(f"• {feature}")
    
    with col2:
        st.markdown("**Структурная схема:**")
        for i, step in enumerate(selected_genre.structural_schema, 1):
            st.markdown(f"{i}. {step}")
    
    st.markdown("---")
    
    # Блок 2: Профиль жанра (радар)
    st.header("📊 Профиль жанра")
    st.markdown("""
    Радарная диаграмма показывает характерные особенности жанра по следующим осям:
    - **Сюжетность**: насколько развит сюжет
    - **Описательность**: уровень детализации
    - **Конфликтность**: выраженность конфликта
    - **Лиричность**: эмоциональность и лирические отступления
    - **Условность**: степень условности/фантастичности
    - **Нравственная окраска**: выраженность моральной позиции
    - **Социальность**: социальный контекст
    """)
    
    radar_fig = build_radar_chart(selected_genre.radar_profile)
    st.plotly_chart(radar_fig, use_container_width=True)

    st.markdown("---")

    # Блок 3: Генерация текста
    st.header("✍️ Генерация текста")
    st.info("💡 Текст генерируется в завершённом виде. Если модель попытается обрезать текст — система автоматически завершит его до логического окончания.")
    
    if st.button("🔄 Сгенерировать текст", type="primary", use_container_width=True):
        with st.spinner("Генерирую текст..."):
            try:
                # Загружаем промпт для генерации
                prompt_path = Path("prompts/generate_prompt.txt")
                if prompt_path.exists():
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        system_prompt = f.read()
                else:
                    system_prompt = "Ты — опытный литературный автор. Создай текст в заданном жанре с учётом всех параметров."
                
                # Формируем user_prompt
                moral_text = "да" if st.session_state.params.has_moral else "нет"
                descriptiveness_desc = {
                    0: "минимальная",
                    25: "низкая",
                    50: "средняя",
                    75: "высокая",
                    100: "максимальная"
                }
                desc_level = min(descriptiveness_desc.keys(), key=lambda x: abs(x - st.session_state.params.descriptiveness))
                
                user_prompt = f"""Создай текст в жанре "{selected_genre.name}".

ОПИСАНИЕ ЖАНРА:
{selected_genre.description}

ТИПИЧНЫЕ ПРИЗНАКИ:
{', '.join(selected_genre.typical_features)}

СТРУКТУРНАЯ СХЕМА:
{' → '.join(selected_genre.structural_schema)}

ИНСТРУКЦИИ ПО ГЕНЕРАЦИИ:
{selected_genre.generation_instructions}

ПАРАМЕТРЫ:
- Тональность: {st.session_state.params.tonality}
- Фокус повествования: {st.session_state.params.focus}
- Уровень описательности: {descriptiveness_desc[desc_level]} ({st.session_state.params.descriptiveness}/100)
- Количество персонажей: {st.session_state.params.characters_count}
- Наличие моральной развязки: {moral_text}
- Сеттинг/эпоха: {st.session_state.params.setting}
- Объём: примерно {st.session_state.params.target_length} слов

Создай текст, строго следуя всем указанным требованиям."""
                
                # Вызываем API
                generated = call_grok_chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.8,
                    max_tokens=st.session_state.params.target_length * 2  # Примерная оценка токенов
                )
                
                # Проверяем и догенерируем завершение, если текст оборван
                generated = refine_generation_if_needed(generated)
                
                st.session_state.generated_text = generated
                st.session_state.analysis_result = None  # Сбрасываем анализ
                st.session_state.broken_text = ""  # Сбрасываем сломанный текст
                st.success("Текст успешно сгенерирован!")
                
            except ValueError as e:
                # Ошибка отсутствия API ключа
                st.error("❌ Проблема с API ключом")
                st.error(str(e))
                with st.expander("📋 Инструкция по настройке API ключа"):
                    st.markdown("""
                    **Шаг 1:** Создайте файл `.env` в корне проекта (если его нет)
                    
                    **Шаг 2:** Добавьте в файл `.env` следующую строку:
                    ```
                    GROK_API_KEY=your_actual_grok_api_key_here
                    ```
                    
                    **Шаг 3:** Получите API ключ:
                    1. Зарегистрируйтесь на [console.x.ai](https://console.x.ai)
                    2. Перейдите в раздел API Keys
                    3. Создайте новый ключ
                    4. Скопируйте ключ и вставьте в файл `.env`
                    
                    **Шаг 4:** Перезапустите приложение:
                    ```bash
                    # Остановите приложение (Ctrl+C)
                    # Затем запустите снова:
                    streamlit run app.py
                    ```
                    
                    ⚠️ **Важно:** Файл `.env` должен находиться в той же директории, что и `app.py`
                    """)
            except RuntimeError as e:
                # Ошибка API (включая 401)
                error_str = str(e)
                if "401" in error_str or "авторизации" in error_str.lower():
                    st.error(error_str)
                    with st.expander("🔧 Как исправить"):
                        st.markdown("""
                        **Проверьте:**
                        1. Файл `.env` существует в корне проекта
                        2. В `.env` есть строка `GROK_API_KEY=...` (без пробелов вокруг `=`)
                        3. API ключ скопирован полностью, без лишних символов
                        4. API ключ активен на [console.x.ai](https://console.x.ai)
                        
                        **После исправления перезапустите приложение!**
                        """)
                else:
                    st.error(f"Ошибка при генерации текста: {error_str}")
            except Exception as e:
                st.error(f"Неожиданная ошибка: {str(e)}")
                st.info("Проверьте логи для деталей.")
    
    # Отображение сгенерированного текста
    if st.session_state.generated_text:
        st.subheader("Сгенерированный текст:")
        
        # Обёртка для улучшения читаемости
        st.markdown('<div class="generated-text">', unsafe_allow_html=True)
        
        # Позволяем редактировать текст
        edited_text = st.text_area(
            "Вы можете отредактировать текст перед анализом:",
            value=st.session_state.generated_text,
            height=300,
            key="text_editor"
        )
        
        # Обновляем session state, если текст изменён
        if edited_text != st.session_state.generated_text:
            st.session_state.generated_text = edited_text
            st.session_state.analysis_result = None  # Сбрасываем анализ при изменении текста
        
        # Закрываем обёртку
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Блок 4: Анализ соответствия жанру
        st.header("🔍 Анализ соответствия жанру")
        
        if st.button("📊 Проанализировать текст", type="primary", use_container_width=True):
            with st.spinner("Анализирую текст..."):
                try:
                    analysis = analyze_text_with_llm(
                        genre=selected_genre,
                        params=st.session_state.params,
                        text=st.session_state.generated_text
                    )
                    st.session_state.analysis_result = analysis
                    st.success("Анализ завершён!")
                except ValueError as e:
                    st.error("❌ Проблема с API ключом")
                    st.error(str(e))
                    with st.expander("📋 Инструкция по настройке API ключа"):
                        st.markdown("""
                        **Шаг 1:** Создайте файл `.env` в корне проекта (если его нет)
                        
                        **Шаг 2:** Добавьте в файл `.env` следующую строку:
                        ```
                        GROK_API_KEY=your_actual_grok_api_key_here
                        ```
                        
                        **Шаг 3:** Получите API ключ на [console.x.ai](https://console.x.ai)
                        
                        **Шаг 4:** Перезапустите приложение после изменения `.env`
                        """)
                except RuntimeError as e:
                    error_str = str(e)
                    if "401" in error_str or "авторизации" in error_str.lower():
                        st.error(error_str)
                        with st.expander("🔧 Как исправить"):
                            st.markdown("""
                            **Проверьте:**
                            1. Файл `.env` существует и содержит `GROK_API_KEY=...`
                            2. API ключ скопирован полностью, без лишних символов
                            3. API ключ активен на [console.x.ai](https://console.x.ai)
                            
                            **После исправления перезапустите приложение!**
                            """)
                    else:
                        st.error(f"Ошибка при анализе текста: {error_str}")
                except Exception as e:
                    st.error(f"Неожиданная ошибка при анализе: {str(e)}")
                    st.info("Проверьте логи для деталей.")
        
        # Отображение результатов анализа
        if st.session_state.analysis_result:
            analysis = st.session_state.analysis_result
            
            # Обёртка для блока анализа
            st.markdown('<div class="analysis-block">', unsafe_allow_html=True)
            
            # Общая оценка
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                        "Соответствие жанру",
                        f"{analysis['scores']['genre_fit']}%",
                        delta=None
                )
            
            with col2:
                st.metric(
                    "Соответствие тональности",
                    f"{analysis['scores']['tonality_fit']}%",
                    delta=None
                )
            
            with col3:
                st.metric(
                    "Соответствие структуре",
                    f"{analysis['scores']['structure_fit']}%",
                    delta=None
                )
            
            with col4:
                st.metric(
                    "Соответствие стилю",
                    f"{analysis['scores']['style_fit']}%",
                    delta=None
                )
        
            # Визуализация оценок
            st.subheader("Детальные оценки:")
            st.progress(analysis['scores']['genre_fit'] / 100, text=f"Жанр: {analysis['scores']['genre_fit']}%")
            st.progress(analysis['scores']['tonality_fit'] / 100, text=f"Тональность: {analysis['scores']['tonality_fit']}%")
            st.progress(analysis['scores']['structure_fit'] / 100, text=f"Структура: {analysis['scores']['structure_fit']}%")
            st.progress(analysis['scores']['style_fit'] / 100, text=f"Стиль: {analysis['scores']['style_fit']}%")
            
            # Комментарий
            st.subheader("Комментарий:")
            st.markdown(f"**Общая оценка:** {analysis['commentary']['overall']}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if analysis['commentary']['strengths']:
                    st.markdown("**Сильные стороны:**")
                    for strength in analysis['commentary']['strengths']:
                        st.markdown(f"✅ {strength}")
                
                if analysis['commentary']['weaknesses']:
                    st.markdown("**Слабые места:**")
                    for weakness in analysis['commentary']['weaknesses']:
                        st.markdown(f"⚠️ {weakness}")
            
            with col2:
                if analysis['commentary']['recommendations']:
                    st.markdown("**Рекомендации:**")
                    for rec in analysis['commentary']['recommendations']:
                        st.markdown(f"💡 {rec}")
            
            # Радар с наложением
            st.subheader("Сравнение профилей:")
            st.markdown("Сравнение идеального профиля жанра (синий) и профиля текста (оранжевый):")
            
            if 'radar' in analysis and analysis['radar']:
                comparison_radar = build_radar_chart(
                    base_profile=selected_genre.radar_profile,
                    text_profile=analysis['radar']
                )
                st.plotly_chart(comparison_radar, use_container_width=True)
            
            # Закрываем обёртку блока анализа
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Блок 5: Режим "Сломать жанр"
            st.header("🔨 Режим «Сломать жанр»")
            st.markdown("""
            Этот режим создаёт модифицированную версию текста, которая **осознанно нарушает** 
            жанровые нормы, но сохраняет узнаваемые элементы жанра. Это помогает понять границы жанра 
            через их нарушение.
            """)
            
            if st.button("🔨 Сломать жанр", type="secondary", use_container_width=True):
                with st.spinner("Создаю модифицированную версию..."):
                    try:
                        broken = break_genre_with_llm(
                            genre=selected_genre,
                            params=st.session_state.params,
                            text=st.session_state.generated_text
                        )
                        st.session_state.broken_text = broken
                        st.success("Модифицированный текст создан!")
                    except ValueError as e:
                        st.error("❌ Проблема с API ключом")
                        st.error(str(e))
                    except RuntimeError as e:
                        error_str = str(e)
                        if "401" in error_str or "авторизации" in error_str.lower():
                            st.error(error_str)
                            with st.expander("🔧 Как исправить"):
                                st.markdown("""
                                **Проверьте:**
                                1. Файл `.env` существует и содержит `GROK_API_KEY=...`
                                2. API ключ скопирован полностью, без лишних символов
                                3. API ключ активен на [console.x.ai](https://console.x.ai)
                                
                                **После исправления перезапустите приложение!**
                                """)
                        else:
                            st.error(f"Ошибка при создании модифицированного текста: {error_str}")
                    except Exception as e:
                        st.error(f"Неожиданная ошибка: {str(e)}")
            
            if st.session_state.broken_text:
                st.subheader("Модифицированный текст (нарушающий жанровые нормы):")
                # Обёртка для модифицированного текста
                st.markdown('<div class="generated-text">', unsafe_allow_html=True)
                st.text_area(
                    "Модифицированный текст",
                    value=st.session_state.broken_text,
                    height=300,
                    key="broken_text_display",
                    disabled=True,
                    label_visibility="hidden"
                )
                st.markdown('</div>', unsafe_allow_html=True)
                st.info("💡 Этот текст намеренно нарушает жанровые конвенции, но сохраняет связь с исходным жанром.")
    else:
        st.info("👆 Нажмите кнопку «Сгенерировать текст», чтобы создать текст в выбранном жанре.")

# ==================== ВКЛАДКА 2: АНАЛИЗ МОЕГО ТЕКСТА ====================
with tab2:
    # ==================== ВКЛАДКА "АНАЛИЗ МОЕГО ТЕКСТА" ====================
    st.header("📝 Анализ моего текста")
    st.markdown("""
    Загрузите или вставьте свой текст для полного литературоведческого анализа:
    жанровая принадлежность, структура, нарратив, фокализация, стиль.
    """)
    
    # Загрузка файла
    uploaded_file = st.file_uploader(
        "Загрузите текстовый файл (.txt)",
        type=["txt"],
        help="Выберите файл с текстом для анализа"
    )
    
    # Текстовое поле для ввода
    user_text = st.text_area(
        "Или введите текст вручную:",
        value=st.session_state.user_text_input,
        height=300,
        help="Вставьте текст для анализа"
    )
    
    # Обновляем session state
    if user_text != st.session_state.user_text_input:
        st.session_state.user_text_input = user_text
        st.session_state.user_text_analysis = None  # Сбрасываем анализ при изменении текста
    
    # Обработка загруженного файла
    if uploaded_file is not None:
        try:
            file_content = uploaded_file.read().decode("utf-8")
            st.session_state.user_text_input = file_content
            user_text = file_content
            st.success("Файл успешно загружен!")
        except Exception as e:
            st.error(f"Ошибка при чтении файла: {str(e)}")
    
    # Кнопка анализа
    if st.button("🔍 Анализировать текст", type="primary", use_container_width=True):
        if not user_text or len(user_text.strip()) < 50:
            st.warning("⚠️ Текст слишком короткий. Введите или загрузите текст длиной не менее 50 символов.")
        else:
            with st.spinner("Анализирую текст..."):
                try:
                    analysis = analyze_user_text(user_text, all_genres)
                    st.session_state.user_text_analysis = analysis
                    st.success("Анализ завершён!")
                except ValueError as e:
                    st.error("❌ Проблема с API ключом")
                    st.error(str(e))
                except RuntimeError as e:
                    error_str = str(e)
                    if "401" in error_str or "авторизации" in error_str.lower():
                        st.error(error_str)
                    else:
                        st.error(f"Ошибка при анализе текста: {error_str}")
                except Exception as e:
                    st.error(f"Неожиданная ошибка: {str(e)}")
    
    # Отображение результатов анализа
    if st.session_state.user_text_analysis:
        analysis = st.session_state.user_text_analysis
        
        st.markdown("---")
        
        # Обёртка для блока анализа пользовательского текста
        st.markdown('<div class="analysis-block">', unsafe_allow_html=True)
        
        # Жанровая принадлежность
        st.subheader("🎭 Жанровая принадлежность")
        
        genre_pred = analysis.get("genre_prediction", {})
        main_genre = genre_pred.get("main_genre", "Не определен")
        probabilities = genre_pred.get("probabilities", {})
        elements = genre_pred.get("elements_of_genres", {})
        explanation = genre_pred.get("explanation", "")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.metric("Основной жанр", main_genre)
            
            if probabilities:
                st.markdown("**Вероятности жанров:**")
                for genre_name, prob in sorted(probabilities.items(), key=lambda x: x[1], reverse=True):
                    if prob > 0:
                        st.progress(prob / 100, text=f"{genre_name}: {prob}%")
        
        with col2:
            st.markdown("**Объяснение:**")
            st.info(explanation)
            
            if elements:
                st.markdown("**Элементы других жанров:**")
                for genre_name, features in elements.items():
                    if features:
                        st.markdown(f"**{genre_name}:** {', '.join(features)}")
        
        st.markdown("---")
        
        # Структурный анализ
        st.subheader("📐 Структурный анализ")
        
        structure = analysis.get("structure", {})
        struct_type = structure.get("type", "не определена")
        phases = structure.get("phases", {})
        struct_comment = structure.get("comment", "")
        
        st.markdown(f"**Тип структуры:** {struct_type}")
        
        if phases:
            col1, col2 = st.columns(2)
            
            with col1:
                if phases.get("exposition"):
                    st.markdown("**Экспозиция:**")
                    st.text(phases.get("exposition", ""))
                
                if phases.get("conflict"):
                    st.markdown("**Завязка/Конфликт:**")
                    st.text(phases.get("conflict", ""))
                
                if phases.get("development"):
                    st.markdown("**Развитие:**")
                    st.text(phases.get("development", ""))
            
            with col2:
                if phases.get("climax"):
                    st.markdown("**Кульминация:**")
                    st.text(phases.get("climax", ""))
                
                if phases.get("resolution"):
                    st.markdown("**Развязка:**")
                    st.text(phases.get("resolution", ""))
        
        if struct_comment:
            st.markdown("**Комментарий:**")
            st.info(struct_comment)
        
        st.markdown("---")
        
        # Нарратив и фокализация
        st.subheader("👁️ Нарратив и фокализация")
        
        narrative = analysis.get("narrative", {})
        narrator_type = narrative.get("narrator_type", "не определен")
        focalization = narrative.get("focalization", "не определена")
        focal_explanation = narrative.get("focalization_explanation", "")
        temporal_flow = narrative.get("temporal_flow", "не определен")
        temporal_comment = narrative.get("temporal_comment", "")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Тип повествователя:** {narrator_type}")
            st.markdown(f"**Фокализация:** {focalization}")
            if focal_explanation:
                st.markdown("**Объяснение фокализации:**")
                st.text(focal_explanation)
        
        with col2:
            st.markdown(f"**Временной поток:** {temporal_flow}")
            if temporal_comment:
                st.markdown("**Комментарий о времени:**")
                st.text(temporal_comment)
        
        st.markdown("---")
        
        # Стилистический анализ
        st.subheader("✍️ Стилистический анализ")
        
        style = analysis.get("style", {})
        register = style.get("register", "не определен")
        lexical = style.get("lexical_features", [])
        syntactic = style.get("syntactic_features", [])
        rhetorical = style.get("rhetorical_devices", [])
        style_comment = style.get("overall_comment", "")
        
        st.markdown(f"**Регистр:** {register}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if lexical:
                st.markdown("**Лексические особенности:**")
                for feature in lexical:
                    st.markdown(f"• {feature}")
            
            if syntactic:
                st.markdown("**Синтаксические особенности:**")
                for feature in syntactic:
                    st.markdown(f"• {feature}")
        
        with col2:
            if rhetorical:
                st.markdown("**Риторические приёмы:**")
                for device in rhetorical:
                    st.markdown(f"• {device}")
        
        if style_comment:
            st.markdown("**Общая характеристика стиля:**")
            st.info(style_comment)
        
        st.markdown("---")
        
        # Цитаты-доказательства
        st.subheader("📎 Цитаты-доказательства")
        
        evidence = analysis.get("evidence", [])
        if evidence:
            for item in evidence:
                aspect = item.get("aspect", "")
                quote = item.get("quote", "")
                explanation = item.get("explanation", "")
                
                if quote and explanation:
                    with st.expander(f"🔖 {aspect.capitalize()}"):
                        st.markdown(f"**Цитата:**")
                        st.markdown(f"> {quote}")
                        st.markdown(f"**Объяснение:** {explanation}")
        else:
            st.info("Цитаты-доказательства не предоставлены.")
        
        # Закрываем обёртку блока анализа пользовательского текста
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== ВКЛАДКА 3: NARRATIVE PLAYGROUND ====================
with tab3:
    st.header("🎭 Narrative Playground")
    st.markdown("""
    **Narrative Playground** — экспериментальная площадка для изучения трансмедиальности,
    нелинейного сторителлинга, ветвящихся нарративов и сюжетных структур.
    
    Исследуйте различные нарративные формы, создавайте ветвящиеся истории и экспериментируйте 
    с трансформацией текста между различными медиаформатами.
    """)
    
    st.markdown("---")
    
    # Режим аудитории (QR-код для ngrok)
    with st.expander("📱 Режим аудитории (QR-код для доступа через ngrok)", expanded=False):
        st.markdown("""
        **Для работы в аудитории:**
        1. Запустите приложение с ngrok: `ngrok http 8501`
        2. Установите переменную окружения NGROK_URL с URL от ngrok
        3. Студенты сканируют QR-код и получают доступ к приложению на своих устройствах
        """)
        display_qr_code()
    
    st.markdown("---")
    
    # Секция 1: Конструктор сюжета (Plot Builder)
    st.subheader("🏗️ Конструктор сюжета (Plot Builder)")
    st.markdown("""
    Создайте структурированную сюжетную схему с узлами и связями. 
    Выберите тип структуры, количество узлов и параметры жанра.
    """)
    
    plot_col1, plot_col2 = st.columns(2)
    
    with plot_col1:
        structure_type = st.selectbox(
            "Тип структуры:",
            ["linear", "branching", "circular", "mosaic", "Rashomon", "split-perspective", "epistolary"],
            help="Выберите тип сюжетной структуры"
        )
        
        num_nodes = st.slider(
            "Количество узлов:",
            min_value=3,
            max_value=15,
            value=5,
            help="Количество узлов в сюжетной структуре"
        )
        
        genre_name_plot = st.selectbox(
            "Жанр:",
            [genre.name for genre in all_genres],
            key="plot_genre",
            help="Выберите жанр для сюжета"
        )
    
    with plot_col2:
        style_plot = st.selectbox(
            "Стилистика:",
            ["реалистическая", "романтическая", "модернистская", "постмодернистская", "экспериментальная"],
            help="Стилистика повествования"
        )
        
        era_plot = st.text_input(
            "Эпоха:",
            value="современность",
            help="Эпоха, в которой происходит действие"
        )
    
    if st.button("🔄 Сгенерировать сюжетную структуру", type="primary", use_container_width=True):
        with st.spinner("Генерирую сюжетную структуру..."):
            try:
                selected_genre_plot = next((g for g in all_genres if g.name == genre_name_plot), all_genres[0])
                
                plot_structure = request_with_delay(
                    generate_plot_structure,
                    structure_type=structure_type,
                    num_nodes=num_nodes,
                    genre=selected_genre_plot.name,
                    style=style_plot,
                    era=era_plot
                )
                
                st.session_state.plot_structure = plot_structure
                st.success("Сюжетная структура успешно сгенерирована!")
                
            except ValueError as e:
                st.error("❌ Проблема с API ключом")
                st.error(str(e))
            except RuntimeError as e:
                error_str = str(e)
                if "401" in error_str or "авторизации" in error_str.lower():
                    st.error(error_str)
                else:
                    st.error(f"Ошибка при генерации структуры: {error_str}")
            except Exception as e:
                st.error(f"Неожиданная ошибка: {str(e)}")
    
    if st.session_state.plot_structure:
        plot_structure = st.session_state.plot_structure
        
        st.markdown("---")
        
        # Визуализация графа
        st.subheader("📊 Визуализация сюжетного графа")
        
        try:
            graph_fig = build_story_graph(plot_structure)
            st.plotly_chart(graph_fig, use_container_width=True)
            
            # Статистика графа
            stats = get_graph_statistics(plot_structure)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Узлов", stats["total_nodes"])
            with col2:
                st.metric("Связей", stats["total_edges"])
            with col3:
                st.metric("Средняя степень", f"{stats['average_degree']:.1f}")
            with col4:
                st.metric("Циклы", "Да" if stats["has_cycles"] else "Нет")
            
        except Exception as e:
            st.error(f"Ошибка при визуализации графа: {str(e)}")
        
        st.markdown("---")
        
        # Генерация текста для узлов
        st.subheader("📝 Генерация текста для узлов")
        
        nodes = plot_structure.get("nodes", [])
        selected_node_id = st.selectbox(
            "Выберите узел для генерации текста:",
            [node["node_id"] for node in nodes],
            format_func=lambda x: f"Узел {x}: {next((n['title'] for n in nodes if n['node_id'] == x), '')}"
        )
        
        if st.button("📝 Сгенерировать текст узла", type="secondary"):
            selected_node = next((n for n in nodes if n["node_id"] == selected_node_id), None)
            if selected_node:
                with st.spinner("Генерирую текст узла..."):
                    try:
                        # Получаем выбранный жанр заново из UI
                        selected_genre_plot = next((g for g in all_genres if g.name == genre_name_plot), all_genres[0])
                        
                        node_text = request_with_delay(
                            generate_node_text,
                            node_id=selected_node_id,
                            node_title=selected_node["title"],
                            node_description=selected_node["description"],
                            genre=selected_genre_plot.name,
                            style=style_plot,
                            era=era_plot
                        )
                        
                        st.markdown("### Текст узла:")
                        # Обёртка для текста узла
                        st.markdown('<div class="story-node-output">', unsafe_allow_html=True)
                        st.text_area(
                            "Текст узла",
                            value=node_text,
                            height=300,
                            key=f"node_text_{selected_node_id}",
                            disabled=True,
                            label_visibility="hidden"
                        )
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                    except ValueError as e:
                        st.error("❌ Проблема с API ключом")
                        st.error(str(e))
                    except RuntimeError as e:
                        error_str = str(e)
                        st.error(f"Ошибка при генерации текста узла: {error_str}")
                    except Exception as e:
                        st.error(f"Неожиданная ошибка: {str(e)}")
    
    st.markdown("---")
    
    # Секция 2: Ветвящиеся истории (Branching Narrative Lab)
    st.subheader("🌳 Ветвящиеся истории (Branching Narrative Lab)")
    st.markdown("""
    Создавайте интерактивные истории с ветвлениями. Каждый выбор ведёт к альтернативному развитию сюжета.
    """)
    
    initial_scene = st.text_area(
        "Начальная сцена:",
        value=st.session_state.branching_scene,
        height=150,
        help="Опишите начальную сцену или текущее состояние истории"
    )
    
    if initial_scene != st.session_state.branching_scene:
        st.session_state.branching_scene = initial_scene
        st.session_state.branching_history = []  # Сбрасываем историю при изменении сцены
    
    choice = st.text_input(
        "Вариант выбора:",
        placeholder="Например: Герой решает пойти налево",
        help="Опишите выбор, который приведёт к ветвлению истории"
    )
    
    if st.button("✨ Создать ветвление", type="primary", use_container_width=True):
        if not initial_scene or len(initial_scene.strip()) < 20:
            st.warning("⚠️ Начальная сцена должна содержать не менее 20 символов.")
        elif not choice or len(choice.strip()) < 5:
            st.warning("⚠️ Вариант выбора должен содержать не менее 5 символов.")
        else:
            with st.spinner("Генерирую ветвление..."):
                try:
                    branch = request_with_delay(
                        generate_branch,
                        initial_scene=initial_scene,
                        choice=choice,
                        previous_branches=st.session_state.branching_history
                    )
                    
                    # Добавляем выбор в ветвление для истории
                    branch["choice"] = choice
                    branch["initial_scene"] = initial_scene
                    
                    st.session_state.branching_history.append(branch)
                    st.session_state.branching_scene = branch.get("branch_text", initial_scene)
                    
                    st.success("Ветвление успешно создано!")
                    
                except ValueError as e:
                    st.error("❌ Проблема с API ключом")
                    st.error(str(e))
                except RuntimeError as e:
                    error_str = str(e)
                    if "401" in error_str or "авторизации" in error_str.lower():
                        st.error(error_str)
                    else:
                        st.error(f"Ошибка при генерации ветвления: {error_str}")
                except Exception as e:
                    st.error(f"Неожиданная ошибка: {str(e)}")
    
    if st.session_state.branching_history:
        st.markdown("---")
        st.subheader("📚 История ветвлений")
        
        for i, branch in enumerate(st.session_state.branching_history, 1):
            with st.expander(f"🌿 Ветвление {i}: {branch.get('choice', 'Выбор')}"):
                st.markdown(f"**Продолжение:**")
                # Обёртка для текста ветвления
                st.markdown('<div class="generated-text">', unsafe_allow_html=True)
                st.text_area(
                    "Текст ветвления",
                    value=branch.get("branch_text", ""),
                    height=200,
                    key=f"branch_text_{i}",
                    disabled=True,
                    label_visibility="hidden"
                )
                st.markdown('</div>', unsafe_allow_html=True)
                
                analysis = branch.get("analysis", {})
                if analysis:
                    col1, col2 = st.columns(2)
                    with col1:
                        if analysis.get("genre_shift"):
                            st.markdown(f"**Жанровый сдвиг:** {analysis['genre_shift']}")
                        if analysis.get("focalization_change"):
                            st.markdown(f"**Изменение фокализации:** {analysis['focalization_change']}")
                    with col2:
                        if analysis.get("style_change"):
                            st.markdown(f"**Изменение стиля:** {analysis['style_change']}")
                        if analysis.get("tension_change"):
                            st.markdown(f"**Изменение напряжения:** {analysis['tension_change']}")
        
        # Сравнительный анализ
        if len(st.session_state.branching_history) > 1:
            st.markdown("---")
            st.subheader("📊 Сравнительный анализ ветвлений")
            
            try:
                comparison = compare_branches(st.session_state.branching_history)
                
                if "error" not in comparison:
                    st.markdown(f"**Всего ветвлений:** {comparison['total_branches']}")
                    
                    # Отображаем сравнения
                    for branch_num, genre_shift in enumerate(comparison.get("genre_shifts", []), 1):
                        if genre_shift.get("shift") != "Не указано":
                            st.markdown(f"**Ветвление {branch_num}** — Жанровый сдвиг: {genre_shift['shift']}")
                    
            except Exception as e:
                st.error(f"Ошибка при сравнении ветвлений: {str(e)}")
        
        if st.button("🔄 Начать заново", type="secondary"):
            st.session_state.branching_history = []
            st.session_state.branching_scene = ""
            st.rerun()
    
    st.markdown("---")
    
    # Секция 3: Трансформация медиума (Form Shifter)
    st.subheader("🎭 Трансформация медиума (Form Shifter)")
    st.markdown("""
    Преобразуйте текст в различные медиаформаты: пьеса, сценарий, подкаст, комикс, визуальный роман,
    игровая сцена, дневниковая запись, соцсетевой пост или поэтическая версия.
    """)
    
    transform_text_input = st.text_area(
        "Введите текст для трансформации:",
        height=200,
        help=f"Максимальная длина: {MAX_CHARS} символов"
    )
    
    # Отображение информации о длине текста
    if transform_text_input:
        char_count = len(transform_text_input)
        if char_count > MAX_CHARS:
            st.warning(f"⚠️ Текст слишком длинный ({char_count} символов). Максимальная длина: {MAX_CHARS} символов.")
        else:
            st.info(f"📝 Длина текста: {char_count} / {MAX_CHARS} символов")
    
    target_format = st.selectbox(
        "Целевой формат:",
        ["пьеса", "сценарий", "подкаст", "комикс", "визуальный роман", 
         "игровая сцена", "дневниковая запись", "соцсетевой пост", "поэтическая версия"],
        help="Выберите формат для трансформации текста"
    )
    
    if st.button("🔄 Преобразовать текст", type="primary", use_container_width=True):
        if not transform_text_input or len(transform_text_input.strip()) < 20:
            st.warning("⚠️ Текст должен содержать не менее 20 символов.")
        else:
            is_valid, error_msg = validate_text_length(transform_text_input)
            if not is_valid:
                st.error(error_msg)
            else:
                with st.spinner("Преобразую текст..."):
                    try:
                        transformation = request_with_delay(
                            transform_text,
                            text=transform_text_input,
                            target_format=target_format
                        )
                        
                        st.session_state.transformation_result = transformation
                        st.success("Текст успешно преобразован!")
                        
                    except ValueError as e:
                        st.error(str(e))
                    except RuntimeError as e:
                        error_str = str(e)
                        if "401" in error_str or "авторизации" in error_str.lower():
                            st.error(error_str)
                        else:
                            st.error(f"Ошибка при трансформации: {error_str}")
                    except Exception as e:
                        st.error(f"Неожиданная ошибка: {str(e)}")
    
    if st.session_state.transformation_result:
        transformation = st.session_state.transformation_result
        
        st.markdown("---")
        st.subheader("✨ Результат трансформации")
        
        result_text = transformation.get("result_text", "")
        if result_text:
            st.markdown("### Преобразованный текст:")
            # Обёртка для преобразованного текста
            st.markdown('<div class="transformed-text">', unsafe_allow_html=True)
            st.text_area(
                "Преобразованный текст",
                value=result_text,
                height=400,
                key="transformation_result_text",
                disabled=True,
                label_visibility="hidden"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        explanation = transformation.get("explanation", {})
        if explanation:
            st.markdown("### Анализ трансформации:")
            # Обёртка для блока анализа трансформации
            st.markdown('<div class="analysis-block">', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if explanation.get("changed_structure"):
                    st.markdown("**Изменение структуры:**")
                    st.info(explanation["changed_structure"])
                
                if explanation.get("changed_focalization"):
                    st.markdown("**Изменение фокализации:**")
                    st.info(explanation["changed_focalization"])
            
            with col2:
                if explanation.get("changed_style"):
                    st.markdown("**Изменение стиля:**")
                    st.info(explanation["changed_style"])
                
                if explanation.get("new_effect"):
                    st.markdown("**Новый эффект формата:**")
                    st.info(explanation["new_effect"])
            
            st.markdown('</div>', unsafe_allow_html=True)

# Футер
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #718096; padding: 2rem; margin-top: 2rem;'>
    <p style='font-size: 1rem; font-weight: 600; color: #2d3748; margin-bottom: 0.5rem;'><strong>✨ NARRALAB</strong></p>
    <p style='font-size: 0.875rem; color: #718096; margin: 0;'>Платформа интерактивного сторителлинга с использованием ИИ</p>
    <p style='font-size: 0.75rem; color: #a0aec0; margin-top: 0.75rem;'>© 2026 NARRALAB. Все права защищены.</p>
    </div>
    """,
    unsafe_allow_html=True
)

