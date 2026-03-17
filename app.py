"""NARRALAB: Платформа интерактивного сторителлинга с использованием ИИ."""

import streamlit as st
import os
import logging
from pathlib import Path
from genres.schema import get_all_genres, get_genre_by_id
from genres.rules import AnalysisParams, analyze_text_with_llm, break_genre_with_llm
from services.grok_client import (
    get_active_provider,
    get_api_key_hints
)
from components.radar import build_radar_chart
from research.user_text_analysis import analyze_user_text
from narrative.builder import generate_plot_structure, generate_node_text
from narrative.graph import build_story_graph, get_graph_statistics
from narrative.branching import generate_branch, compare_branches
from narrative.transformations import transform_text
from narrative.load_balance import validate_text_length, request_with_delay, MAX_CHARS
from utils import init_session_state, load_prompt, trim_list_state
from ai_engine import generate_text, stream_text
from ui_components import (
    render_hero,
    render_api_setup_help,
    render_api_key_error_block,
)

logging.basicConfig(level=logging.INFO)

# Настройка страницы должна быть первой streamlit-командой. Сайдбар скрыт на «Как пользоваться» и «Нарративная песочница».
_current_tab = st.session_state.get("current_tab", "help")
_sidebar_hidden_tabs = ("help", "playground")
st.set_page_config(
    page_title="NARRALAB - Платформа интерактивного сторителлинга",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed" if _current_tab in _sidebar_hidden_tabs else "expanded"
)

# Проброс секретов из Streamlit Cloud в окружение (чтобы grok_client видел DEEPSEEK_API_KEY)
try:
    for key in ("DEEPSEEK_API_KEY", "AI_API_KEY", "GROK_API_KEY", "APP_LOGIN", "APP_PASSWORD"):
        if hasattr(st, "secrets") and key in st.secrets and not os.environ.get(key):
            os.environ[key] = str(st.secrets.get(key) or "")
except Exception:
    pass

# Учётные данные для входа (Streamlit Cloud: Secrets; локально: .env или переменные окружения)
def _get_secret(key: str, default: str = "") -> str:
    try:
        return (st.secrets.get(key) or os.getenv(key, default)) or default
    except Exception:
        return os.getenv(key, default)

APP_LOGIN = _get_secret("APP_LOGIN", "").strip()
APP_PASSWORD = _get_secret("APP_PASSWORD", "").strip()
AUTH_REQUIRED = bool(APP_PASSWORD)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Выход по ссылке ?logout=1 (кнопка «Выйти» рендерится как ссылка для надёжных стилей в тёмной теме)
if AUTH_REQUIRED and st.session_state.authenticated and st.query_params.get("logout") == "1":
    st.session_state.authenticated = False
    st.query_params.clear()
    st.rerun()

# Экран входа: показываем только форму логина, пока пользователь не введёт верные данные
if AUTH_REQUIRED and not st.session_state.authenticated:
    st.markdown("<div style='max-width: 420px; margin: 4rem auto; padding: 2rem;'>", unsafe_allow_html=True)
    st.header("🔐 Вход в NARRALAB")
    st.markdown("Введите логин и пароль, полученные от преподавателя.")
    with st.form("login_form"):
        login = st.text_input("Логин", placeholder="логин" if APP_LOGIN else "не требуется")
        password = st.text_input("Пароль", type="password", placeholder="пароль")
        submitted = st.form_submit_button("Войти")
    if submitted:
        login_ok = (login.strip() == APP_LOGIN) if APP_LOGIN else True
        if login_ok and password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Неверный логин или пароль.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# Элегантный минималистичный дизайн
st.markdown("""
<style>
/* Спокойная светлая палитра */
:root {
    --primary: #2563eb;          /* насыщенный синий для акцентов */
    --primary-light: #60a5fa;    /* более светлый синий */
    --accent: #1d4ed8;           /* тёмный синий для hover */
    --bg-main: #f9fafb;          /* очень светлый серый фон */
    --bg-card: #ffffff;          /* карточки на белом фоне */
    --text-primary: #111827;     /* почти чёрный текст */
    --text-secondary: #4b5563;   /* тёмно-серый вторичный текст */
    --text-muted: #6b7280;       /* приглушённый текст */
    --border: #e2e8f0;
    --border-light: #edf2f7;
    --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

/* Тёмная тема — переопределение переменных и захардкоженных цветов */
body:has(#theme-dark) {
    --primary: #60a5fa;
    --primary-light: #93c5fd;
    --accent: #3b82f6;
    --bg-main: #111827;
    --bg-card: #1f2937;
    --text-primary: #f9fafb;
    --text-secondary: #d1d5db;
    --text-muted: #9ca3af;
    --border: #374151;
    --border-light: #4b5563;
    --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.3);
    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
}
body:has(#theme-dark) textarea[disabled],
body:has(#theme-dark) textarea:disabled {
    background-color: #374151 !important;
    border-color: var(--border) !important;
}
body:has(#theme-dark) .stButton > button {
    background-color: #1e3a5f !important;
    color: #93c5fd !important;
    border-color: #3b82f6 !important;
}
body:has(#theme-dark) .stButton > button:hover {
    background-color: #1e40af !important;
}
body:has(#theme-dark) .stButton > button[kind="secondary"] {
    background-color: #374151 !important;
    color: #e0f2fe !important;
    border-color: #4b5563 !important;
}
body:has(#theme-dark) .stButton > button[kind="secondary"]:hover {
    background-color: #4b5563 !important;
    border-color: #60a5fa !important;
}
body:has(#theme-dark) [data-testid="stSidebar"],
body:has(#theme-dark) [data-testid="stSidebar"] > div {
    background-color: #1f2937 !important;
}
body:has(#theme-dark) .stCodeBlock {
    background-color: #374151 !important;
}
/* Уведомления в тёмной теме */
body:has(#theme-dark) div[data-baseweb="notification"][data-kind="info"],
body:has(#theme-dark) .stInfo {
    background-color: #1e3a5f !important;
    border-color: #3b82f6 !important;
    color: #93c5fd !important;
}
body:has(#theme-dark) div[data-baseweb="notification"][data-kind="success"],
body:has(#theme-dark) .stSuccess {
    background-color: #14532d !important;
    border-color: #22c55e !important;
    color: #86efac !important;
}
body:has(#theme-dark) div[data-baseweb="notification"][data-kind="warning"],
body:has(#theme-dark) .stWarning {
    background-color: #422006 !important;
    border-color: #eab308 !important;
    color: #fde047 !important;
}
body:has(#theme-dark) div[data-baseweb="notification"][data-kind="error"],
body:has(#theme-dark) .stError {
    background-color: #450a0a !important;
    border-color: #ef4444 !important;
    color: #fca5a5 !important;
}
body:has(#theme-dark) [data-testid="stAppViewContainer"],
body:has(#theme-dark) [data-testid="stHeader"],
body:has(#theme-dark) section[data-testid="stSidebar"] {
    background-color: #111827 !important;
}
/* Все блоки контента (в т.ч. Нарративная песочница) — без белого фона, чтобы кнопки и текст читались */
body:has(#theme-dark) [data-testid="stVerticalBlock"],
body:has(#theme-dark) [data-testid="stHorizontalBlock"],
body:has(#theme-dark) [data-testid="column"],
body:has(#theme-dark) [data-testid="stVerticalBlockBorderWrapper"],
body:has(#theme-dark) section[data-testid="stSidebar"] [data-testid="stVerticalBlock"],
body:has(#theme-dark) section[data-testid="stSidebar"] [data-testid="column"] {
    background-color: transparent !important;
}
/* Верхняя панель — тёмный фон */
body:has(#theme-dark) [data-testid="stVerticalBlock"] > div:first-child [data-testid="stHorizontalBlock"],
body:has(#theme-dark) [data-testid="stHorizontalBlock"]:first-of-type,
body:has(#theme-dark) [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"] {
    background-color: #111827 !important;
}
/* Обёртка кнопки — без белого фона */
body:has(#theme-dark) .stButton {
    background-color: transparent !important;
}
body:has(#theme-dark) [data-baseweb="select"] > div,
body:has(#theme-dark) .stTextInput input,
body:has(#theme-dark) div[data-baseweb="textarea"] textarea {
    background-color: #1f2937 !important;
    color: #f9fafb !important;
    border-color: #374151 !important;
}
body:has(#theme-dark) [data-baseweb="select"] *,
body:has(#theme-dark) [data-baseweb="select"] + * {
    color: #f9fafb !important;
    -webkit-text-fill-color: #f9fafb !important;
}
body:has(#theme-dark) .stTextInput input::placeholder,
body:has(#theme-dark) div[data-baseweb="textarea"] textarea::placeholder {
    color: #9ca3af !important;
}
/* Все кнопки в тёмной теме — светлый читаемый текст (в т.ч. «Выйти») */
body:has(#theme-dark) .stButton > button,
body:has(#theme-dark) .stButton > button *,
body:has(#theme-dark) .stButton > button span {
    color: #e0f2fe !important;
    -webkit-text-fill-color: #e0f2fe !important;
}
/* Подписи, лейблы, заголовки полей — везде светлый текст */
body:has(#theme-dark) label,
body:has(#theme-dark) [data-testid="stSidebar"] label,
body:has(#theme-dark) .stSlider label,
body:has(#theme-dark) .stSlider [data-testid="stCaption"],
body:has(#theme-dark) .stCheckbox label,
body:has(#theme-dark) .stRadio label,
body:has(#theme-dark) [data-testid="stCaption"],
body:has(#theme-dark) .stCaption {
    color: #e5e7eb !important;
    -webkit-text-fill-color: #e5e7eb !important;
}
body:has(#theme-dark) .stExpander label,
body:has(#theme-dark) .stExpander p,
body:has(#theme-dark) .stExpander div,
body:has(#theme-dark) .stExpander span,
body:has(#theme-dark) [data-baseweb="accordion"] * {
    color: #e5e7eb !important;
}
body:has(#theme-dark) div[data-testid="stMarkdown"] p,
body:has(#theme-dark) div[data-testid="stMarkdown"] p *,
body:has(#theme-dark) .stMarkdown p,
body:has(#theme-dark) .stMarkdown p *,
body:has(#theme-dark) div[data-testid="stMarkdown"] li,
body:has(#theme-dark) .stMarkdown li,
body:has(#theme-dark) div[data-testid="stMarkdown"] strong,
body:has(#theme-dark) .stMarkdown strong,
body:has(#theme-dark) div[data-testid="stMarkdown"] code,
body:has(#theme-dark) .stMarkdown code {
    color: #e5e7eb !important;
    -webkit-text-fill-color: #e5e7eb !important;
}
body:has(#theme-dark) .stMarkdown code {
    background-color: #374151 !important;
    color: #e5e7eb !important;
}
body:has(#theme-dark) .stText,
body:has(#theme-dark) .stMarkdownContainer {
    color: #e5e7eb !important;
}
body:has(#theme-dark) [data-testid="stMetricValue"],
body:has(#theme-dark) [data-testid="stMetricLabel"] {
    color: #f9fafb !important;
}
body:has(#theme-dark) .stDataFrame,
body:has(#theme-dark) .stDataFrame * {
    background-color: #1f2937 !important;
    color: #e5e7eb !important;
    border-color: #4b5563 !important;
}
body:has(#theme-dark) .stProgress > div > div > div {
    background-color: #60a5fa !important;
}
body:has(#theme-dark) .hero-section,
body:has(#theme-dark) .hero-section * {
    background-color: #1f2937 !important;
    color: #e5e7eb !important;
    border-color: #374151 !important;
}
/* Уведомления: текст внутри тоже светлый */
body:has(#theme-dark) div[data-baseweb="notification"] p,
body:has(#theme-dark) div[data-baseweb="notification"] div,
body:has(#theme-dark) div[data-baseweb="notification"] span,
body:has(#theme-dark) .stAlert p, body:has(#theme-dark) .stAlert div, body:has(#theme-dark) .stAlert span,
body:has(#theme-dark) .stInfo p, body:has(#theme-dark) .stInfo div, body:has(#theme-dark) .stInfo span,
body:has(#theme-dark) .stSuccess p, body:has(#theme-dark) .stSuccess div, body:has(#theme-dark) .stSuccess span,
body:has(#theme-dark) .stWarning p, body:has(#theme-dark) .stWarning div, body:has(#theme-dark) .stWarning span,
body:has(#theme-dark) .stError p, body:has(#theme-dark) .stError div, body:has(#theme-dark) .stError span {
    color: inherit !important;
    opacity: 1 !important;
}
body:has(#theme-dark) .section-nav-title {
    color: #e5e7eb !important;
}
body:has(#theme-dark) blockquote {
    color: #d1d5db !important;
    border-left-color: #60a5fa !important;
}
body:has(#theme-dark) .generated-text,
body:has(#theme-dark) .transformed-text,
body:has(#theme-dark) .analysis-block,
body:has(#theme-dark) .story-node-output,
body:has(#theme-dark) .generated-text textarea,
body:has(#theme-dark) .transformed-text textarea,
body:has(#theme-dark) .analysis-block textarea,
body:has(#theme-dark) .story-node-output textarea {
    color: #e5e7eb !important;
    -webkit-text-fill-color: #e5e7eb !important;
}
/* Блоки с инлайн-стилями в контенте */
body:has(#theme-dark) .genre-description-block,
body:has(#theme-dark) .genre-description-block p {
    background-color: #1f2937 !important;
    color: #e5e7eb !important;
    border-color: #374151 !important;
}
body:has(#theme-dark) .generation-card,
body:has(#theme-dark) .generation-card h2,
body:has(#theme-dark) .generation-card p,
body:has(#theme-dark) .generation-card summary,
body:has(#theme-dark) .generation-card details * {
    background-color: #1f2937 !important;
    color: #e5e7eb !important;
    border-color: #374151 !important;
}
body:has(#theme-dark) .app-footer,
body:has(#theme-dark) .app-footer p,
body:has(#theme-dark) .app-footer * {
    color: #9ca3af !important;
}

/* ========== Аудит тёмной темы: всё контентное пространство тёмное, все кнопки и текст читаемы ========== */
body:has(#theme-dark) main,
body:has(#theme-dark) [data-testid="stAppViewContainer"] > div,
body:has(#theme-dark) [data-testid="stAppViewContainer"] section,
body:has(#theme-dark) [data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #111827 !important;
}
body:has(#theme-dark) div[data-testid="stVerticalBlock"],
body:has(#theme-dark) div[data-testid="stHorizontalBlock"],
body:has(#theme-dark) div[data-testid="column"] {
    background-color: transparent !important;
}
/* Формы и кнопки отправки (Создать ветвление, и др.) */
body:has(#theme-dark) [data-testid="stForm"],
body:has(#theme-dark) form,
body:has(#theme-dark) .stForm {
    background-color: transparent !important;
}
body:has(#theme-dark) [data-testid="stForm"] button,
body:has(#theme-dark) form button,
body:has(#theme-dark) .stForm button,
body:has(#theme-dark) button[type="submit"],
body:has(#theme-dark) .stButton > button[kind="primary"],
body:has(#theme-dark) .stButton > button[kind="secondary"],
body:has(#theme-dark) .stButton > button {
    background-color: #1e3a5f !important;
    color: #e0f2fe !important;
    border-color: #3b82f6 !important;
    -webkit-text-fill-color: #e0f2fe !important;
}
body:has(#theme-dark) .stButton > button[kind="secondary"],
body:has(#theme-dark) form button[type="submit"]:not([kind="primary"]) {
    background-color: #374151 !important;
    border-color: #4b5563 !important;
}
body:has(#theme-dark) [data-testid="stForm"] button *,
body:has(#theme-dark) form button *,
body:has(#theme-dark) .stButton > button *,
body:has(#theme-dark) .stButton > button span {
    color: #e0f2fe !important;
    -webkit-text-fill-color: #e0f2fe !important;
}
/* Подсказки (caption), подписи под полями — всегда светлый текст */
body:has(#theme-dark) [data-testid="stCaption"] *,
body:has(#theme-dark) .stCaption *,
body:has(#theme-dark) small,
body:has(#theme-dark) [class*="caption"] {
    color: #b0b8c0 !important;
    -webkit-text-fill-color: #b0b8c0 !important;
}
/* Tooltip (help=...) — тёмный фон, светлый текст */
body:has(#theme-dark) [data-baseweb="tooltip"],
body:has(#theme-dark) [role="tooltip"],
body:has(#theme-dark) [data-state="open"][data-baseweb="popover"] {
    background-color: #1f2937 !important;
    color: #e5e7eb !important;
    border: 1px solid #4b5563 !important;
}
body:has(#theme-dark) [data-baseweb="tooltip"] *,
body:has(#theme-dark) [role="tooltip"] * {
    color: #e5e7eb !important;
}
/* Заголовки и подзаголовки на всех страницах */
body:has(#theme-dark) h1, body:has(#theme-dark) h2, body:has(#theme-dark) h3,
body:has(#theme-dark) h4, body:has(#theme-dark) h5, body:has(#theme-dark) h6,
body:has(#theme-dark) .stSubheader,
body:has(#theme-dark) [data-testid="stMarkdown"] h1,
body:has(#theme-dark) [data-testid="stMarkdown"] h2,
body:has(#theme-dark) [data-testid="stMarkdown"] h3 {
    color: #f3f4f6 !important;
    -webkit-text-fill-color: #f3f4f6 !important;
}
/* Любой параграф и span в основной области */
body:has(#theme-dark) main p,
body:has(#theme-dark) main span,
body:has(#theme-dark) main div[data-testid="stMarkdown"],
body:has(#theme-dark) [data-testid="stMarkdown"] {
    color: #e5e7eb !important;
}
body:has(#theme-dark) [data-testid="stMarkdown"] * {
    color: inherit !important;
}
body:has(#theme-dark) [data-testid="stMarkdown"] p,
body:has(#theme-dark) [data-testid="stMarkdown"] li,
body:has(#theme-dark) [data-testid="stMarkdown"] span {
    color: #e5e7eb !important;
}
/* Row widgets (кнопки, поля) — обёртка без белого фона */
body:has(#theme-dark) [class*="row-widget"],
body:has(#theme-dark) [class*="stButton"],
body:has(#theme-dark) [class*="stTextInput"],
body:has(#theme-dark) [class*="stTextArea"] {
    background-color: transparent !important;
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

/* Основной текст — чуть крупнее для удобства чтения */
p, .stMarkdown, .stText {
    color: var(--text-primary) !important;
    font-size: 1.0625rem !important;
    line-height: 1.6 !important;
    margin-bottom: 1rem !important;
}

/* Сайдбар — подписи полей крупнее и контрастнее */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown {
    font-size: 1rem !important;
    color: var(--text-primary) !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] .stSlider label {
    font-size: 1rem !important;
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

/* Карточки и блоки для чтения — минималистичные, крупнее шрифт */
.generated-text, .transformed-text, .analysis-block, .story-node-output {
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    padding: 1.5rem !important;
    border-radius: 8px !important;
    border: 1px solid var(--border) !important;
    box-shadow: var(--shadow-sm) !important;
    margin: 1rem 0 !important;
    font-size: 1.125rem !important;
    line-height: 1.75 !important;
}
/* Текст внутри полей результата (textarea) — крупнее для удобства */
.generated-text textarea, .transformed-text textarea, .analysis-block textarea, .story-node-output textarea {
    font-size: 1.0625rem !important;
    line-height: 1.7 !important;
}

/* Кнопки - светлые, с акцентами */
.stButton > button {
    background-color: #eff6ff !important; /* очень светлый синий фон */
    color: var(--primary) !important;
    border: 1px solid var(--primary-light) !important;
    border-radius: 6px !important;
    padding: 0.625rem 1.25rem !important;
    font-weight: 500 !important;
    font-size: 0.9375rem !important;
    transition: background-color 0.2s ease !important;
    box-shadow: none !important;
}

.stButton > button:hover {
    background-color: #dbeafe !important;
    transform: none !important;
}

.stButton > button[kind="secondary"] {
    background-color: transparent !important;
    color: var(--primary) !important;
    border: 1px solid var(--primary-light) !important;
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
    font-size: 0.9375rem !important;
    color: var(--text-primary) !important;
    font-weight: 500 !important;
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

/* Sidebar — слегка серый фон; скрываем полностью на вкладке «Нарративная песочница» */
[data-testid="stSidebar"] {
    background-color: #f3f4f6 !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div {
    background-color: #f3f4f6 !important;
}
/* Скрываем сайдбар на вкладках «Как пользоваться» и «Нарративная песочница» (set_page_config не всегда срабатывает при смене вкладки) */
body:has(#playground-tab-active) [data-testid="stSidebar"],
body:has(#help-tab-active) [data-testid="stSidebar"] {
    display: none !important;
}

/* Верхняя панель: тема и выход справа */
.top-bar-spacer {
    margin-bottom: 0.5rem !important;
}
/* Кнопка «Выйти» — ссылка с полным контролем стилей (читаема в любой теме) */
.exit-btn {
    display: block !important;
    padding: 0.5rem 1rem !important;
    font-size: 0.9375rem !important;
    font-weight: 500 !important;
    text-decoration: none !important;
    border-radius: 6px !important;
    border: 1px solid #3b82f6 !important;
    background-color: #eff6ff !important;
    color: #1d4ed8 !important;
    text-align: center !important;
    width: 100% !important;
    box-sizing: border-box !important;
}
.exit-btn:hover {
    background-color: #dbeafe !important;
    color: #1e40af !important;
}
body:has(#theme-dark) .exit-btn {
    background-color: #374151 !important;
    border-color: #4b5563 !important;
    color: #e0f2fe !important;
}
body:has(#theme-dark) .exit-btn:hover {
    background-color: #4b5563 !important;
    color: #f0f9ff !important;
    border-color: #60a5fa !important;
}

/* Блок навигации по разделам — заголовок и кнопки заметны */
.section-nav-title {
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    margin-bottom: 0.6rem !important;
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

/* Slider – только заполненная часть трека синяя, фон остаётся светлым */
.stSlider [data-baseweb="slider"] > div > div:nth-child(2) {
    background-color: var(--primary-light) !important;
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

/* Скрываем иконки, которые Streamlit показывает как текст (arrow_right, keyboard_double_a и т.д.) */
.stExpander [data-testid="expanderExpandIcon"],
[aria-label="arrow_down (right)"],
[aria-label="arrow_down"],
[aria-label="arrow_right"],
[aria-label="_arrow_right"],
[title="arrow_down (right)"],
[title="arrow_down"],
[title="arrow_right"],
[title="_arrow_right"] {
    display: none !important;
}
/* По атрибуту (содержит) — на случай других имён на Streamlit Cloud: скрываем arrow-иконки полностью */
[aria-label*="arrow"], [aria-label*="Arrow"], [title*="arrow"], [title*="Arrow"] {
    display: none !important;
}
/* keyboard — только убираем видимый текст, кнопка сайдбара остаётся кликабельной */
[aria-label*="keyboard"], [title*="keyboard"] {
    font-size: 0 !important;
    line-height: 0 !important;
    overflow: hidden !important;
    color: transparent !important;
}
[aria-label*="keyboard"] *, [title*="keyboard"] * {
    font-size: 0 !important;
    color: transparent !important;
}
/* Текст кнопки сворачивания сайдбара (keyboard_double, keyboard_double_a и т.д.) — скрываем надпись */
[aria-label="keyboard_double_a"], [title="keyboard_double_a"],
[aria-label="keyboard_double"], [title="keyboard_double"],
[data-testid="stSidebar"] button[aria-label="keyboard_double_a"],
[data-testid="stSidebar"] [title="keyboard_double_a"],
[data-testid="stSidebar"] button[aria-label="keyboard_double"],
[data-testid="stSidebar"] [title="keyboard_double"] {
    font-size: 0 !important;
    line-height: 0 !important;
    overflow: hidden !important;
    color: transparent !important;
}
[aria-label="keyboard_double_a"] *, [title="keyboard_double_a"] *,
[aria-label="keyboard_double"] *, [title="keyboard_double"] * {
    font-size: 0 !important;
    color: transparent !important;
}
/* Скрываем первый блок сайдбара (надпись keyboard_double у кнопки сворачивания). Кнопка «Выйти» перенесена в основную область справа вверху. */
[data-testid="stSidebar"] > div:first-child > button,
[data-testid="stSidebar"] > div:first-child > button *,
[data-testid="stSidebar"] > div:first-child > *:first-child,
[data-testid="stSidebar"] > div:first-child > *:first-child * {
    font-size: 0 !important;
    line-height: 0 !important;
    color: transparent !important;
}
/* Блок иконки в заголовке expander — скрываем, чтобы не показывался текст _arrow_right */
[data-baseweb="accordion-header"] > div:last-of-type,
[data-baseweb="accordion-header"] > div:last-child,
.stExpander > div:first-child > div:last-child {
    font-size: 0 !important;
    line-height: 0 !important;
    visibility: hidden !important;
    width: 0 !important;
    min-width: 0 !important;
    overflow: hidden !important;
    padding: 0 !important;
    margin: 0 !important;
}
/* Скрываем любой элемент с текстом expand/collapse в expander (запасной вариант для Cloud) */
.stExpander [data-testid="stExpanderExpandIcon"] {
    display: none !important;
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

# Инициализация session state (нужна до верхней панели и hero)
init_session_state(
    {
        "current_tab": "help",
        "prev_tab": "help",
        "theme": "light",  # "light" | "dark"
        "selected_genre_id": None,
        "generated_text": "",
        "analysis_result": None,
        "broken_text": "",
        "user_text_analysis": None,
        "user_text_input": "",
        "plot_structure": None,
        "branching_history": [],
        "branching_scene": "",
        "transformation_result": None,
    }
)
trim_list_state("branching_history", max_items=20)

# Верхняя панель: справа — тема (луна/солнце) и кнопка «Выйти»
_top_bar_cols = st.columns([1, 0.12, 0.08])
with _top_bar_cols[1]:
    _theme = st.session_state.get("theme", "light")
    _is_dark = _theme == "dark"
    _icon = "☀️" if _is_dark else "🌙"
    _tooltip = "Включить светлую тему" if _is_dark else "Включить тёмную тему"
    if st.button(_icon, key="theme_toggle", help=_tooltip, use_container_width=True):
        st.session_state.theme = "dark" if not _is_dark else "light"
        st.rerun()
with _top_bar_cols[2]:
    if AUTH_REQUIRED:
        st.markdown(
            '<a href="?logout=1" class="exit-btn" title="Завершить сессию">Выйти</a>',
            unsafe_allow_html=True,
        )
st.markdown('<div class="top-bar-spacer" aria-hidden="true"></div>', unsafe_allow_html=True)

# Hero — один блок с названием, описанием и лозунгом
render_hero()

# Проверка наличия API ключа
env_path = Path(".env")
api_key = (
    os.getenv("DEEPSEEK_API_KEY")
    or os.getenv("AI_API_KEY")
    or os.getenv("GROK_API_KEY")
)
active_provider = get_active_provider().capitalize()

if not api_key:
    render_api_setup_help(active_provider=active_provider, api_key_hints=get_api_key_hints())
    
    if not env_path.exists():
        st.info(f"💡 Файл `.env` не найден в директории: `{Path.cwd()}`")
    else:
        st.info(f"💡 Файл `.env` найден, но ключ для `{active_provider}` не загружен. Проверьте формат файла.")
    
    st.markdown("---")

st.markdown("---")

# Получаем список жанров
all_genres = get_all_genres()

# ==================== РАЗДЕЛЫ САЙТА (навигация — явные кнопки, чтобы было понятно, куда идти) ====================
_tab_labels = {
    "help": "📖 Как пользоваться",
    "generator": "🎨 Генератор историй",
    "analysis": "📊 Анализ текста",
    "playground": "🌳 Нарративная песочница",
}
_current_tab = st.session_state.get("current_tab", "help")

st.markdown("")
st.markdown('<p class="section-nav-title">📍 Разделы</p>', unsafe_allow_html=True)
nav_cols = st.columns(4)
for idx, (tab_key, label) in enumerate(_tab_labels.items()):
    with nav_cols[idx]:
        is_selected = (_current_tab == tab_key)
        if st.button(
            label,
            key=f"nav_{tab_key}",
            type="primary" if is_selected else "secondary",
            use_container_width=True,
        ) and not is_selected:
            st.session_state.current_tab = tab_key
            st.session_state.prev_tab = tab_key
            st.rerun()
st.markdown("---")

# Маркеры для CSS: скрывать сайдбар на «Как пользоваться» и «Нарративная песочница»; тёмная тема
if st.session_state.current_tab == "playground":
    st.markdown('<div id="playground-tab-active" style="display:none" aria-hidden="true"></div>', unsafe_allow_html=True)
if st.session_state.current_tab == "help":
    st.markdown('<div id="help-tab-active" style="display:none" aria-hidden="true"></div>', unsafe_allow_html=True)
if st.session_state.get("theme") == "dark":
    st.markdown('<div id="theme-dark" style="display:none" aria-hidden="true"></div>', unsafe_allow_html=True)

# ==================== САЙДБАР ====================
with st.sidebar:
    st.header("⚙️ Настройки")
    
    # Выбор жанра (стабильный порядок опций и key — чтобы выбор сохранялся для всех жанров)
    genre_names = [g.name for g in all_genres]
    genre_id_by_name = {g.name: g.id for g in all_genres}
    default_genre_index = 0
    if st.session_state.selected_genre_id:
        for i, g in enumerate(all_genres):
            if g.id == st.session_state.selected_genre_id:
                default_genre_index = i
                break
    selected_genre_name = st.selectbox(
        "🎨 Выберите жанр:",
        options=genre_names,
        index=default_genre_index,
        key="sidebar_genre",
    )
    selected_genre_id = genre_id_by_name.get(selected_genre_name) or all_genres[0].id
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

# Кнопка «Выйти» перенесена в верхнюю панель справа

# ==================== ВКЛАДКА: КАК ПОЛЬЗОВАТЬСЯ ====================
if st.session_state.current_tab == "help":
    st.header("📖 Инструкция по использованию NARRALAB")
    st.markdown("""
    Ниже описаны **все возможности платформы** по разделам. Рекомендуем начать с настройки API-ключа, затем перейти в «Генератор историй» или «Анализ текста».
    """)
    st.markdown("---")

    # 0. Настройка — открытый по умолчанию блок на HTML, без expander (нет иконок Streamlit)
    st.markdown("""
    <details open style="margin-bottom:1rem;">
        <summary style="cursor:pointer; font-weight:600; font-size:1.05rem;">🔑 Настройка перед началом работы</summary>
        <div style="margin-top:0.75rem; padding-left:0.5rem;">
            <p><strong>1. Вход.</strong> Если приложение защищено (настроен логин/пароль), сначала введите данные, полученные от преподавателя. Кнопка <strong>«Выйти»</strong> справа вверху страницы завершает сессию.</p>
            <p><strong>2. API-ключ.</strong> Если вы запускаете приложение <strong>локально</strong>, создайте в корне проекта файл <code>.env</code> и добавьте <code>DEEPSEEK_API_KEY=ваш_ключ</code>. Ключ: <a href="https://platform.deepseek.com/api_keys" target="_blank">platform.deepseek.com</a>. Если приложение размещено на <strong>Streamlit Cloud</strong> и ключ задан в настройках (Secrets), вводить ключ не нужно.</p>
            <p><strong>3. Запуск (локально).</strong> В терминале из папки проекта: <code>streamlit run app.py</code>. Откроется браузер.</p>
            <p><strong>4. Вкладки.</strong> Сверху: Как пользоваться, Генератор историй, Анализ текста, Нарративная песочница.</p>
        </div>
    </details>
    """, unsafe_allow_html=True)

    # 1. Генератор историй
    st.subheader("🎨 Генератор историй")
    st.markdown("**Назначение:** создание текста в выбранном жанре с заданными параметрами, проверка соответствия жанру и эксперимент «Сломать жанр».")
    st.markdown("""
    <details style="margin-bottom:1rem;">
        <summary style="cursor:pointer; font-weight:600;">Подробно: Генератор историй</summary>
        <ul style="margin-top:0.5rem; padding-left:1.5rem;">
            <li><strong>Слева (сайдбар)</strong> задаются жанр и параметры: тональность, фокус повествования, уровень описательности, количество персонажей, моральная развязка, сеттинг, объём в словах.</li>
            <li><strong>Описание и профиль жанра.</strong> В начале страницы — описание жанра, типичные признаки, структурная схема и радарная диаграмма. Раздел «Что означают оси радара» можно раскрыть по желанию.</li>
            <li><strong>Генерация.</strong> Кнопка «Сгенерировать текст» отправляет запрос в ИИ. Появится черновик; его можно править в поле ниже.</li>
            <li><strong>Анализ соответствия жанру.</strong> После правок нажмите «Проанализировать текст». Отобразятся оценки, комментарий, сильные стороны, слабые места, рекомендации и сравнение профиля с идеальным профилем жанра на радаре.</li>
            <li><strong>Режим «Сломать жанр».</strong> Появляется после анализа. Создаётся вариант текста, намеренно нарушающий жанровые нормы — полезно для учёбы и экспериментов.</li>
        </ul>
    </details>
    """, unsafe_allow_html=True)

    # 2. Анализ текста
    st.subheader("📊 Анализ текста")
    st.markdown("**Назначение:** полный литературоведческий разбор вашего текста (жанр, структура, нарратив, фокализация, стиль) с цитатами.")
    st.markdown("""
    <details style="margin-bottom:1rem;">
        <summary style="cursor:pointer; font-weight:600;">Подробно: Анализ текста</summary>
        <ul style="margin-top:0.5rem; padding-left:1.5rem;">
            <li><strong>Ввод текста.</strong> Можно загрузить файл .txt или вставить отрывок в поле «Или введите текст вручную». Минимум около 50 символов. Нажмите «Анализировать текст».</li>
            <li><strong>Результаты.</strong> Появятся блоки: жанровая принадлежность, структурный анализ, нарратив и фокализация, стилистический анализ, цитаты-доказательства.</li>
        </ul>
    </details>
    """, unsafe_allow_html=True)

    # 3. Нарративная песочница — три блока на details/summary
    st.subheader("🌳 Нарративная песочница")
    st.markdown("**Назначение:** три инструмента в одном разделе: конструктор сюжета, ветвящиеся истории, трансформация медиума. Жанр и параметры задаются в формах каждого инструмента; панель слева здесь не используется.")
    st.markdown("""
    <details style="margin-bottom:1rem;">
        <summary style="cursor:pointer; font-weight:600;">Подробно: Конструктор сюжета (Plot Builder)</summary>
        <ul style="margin-top:0.5rem; padding-left:1.5rem;">
            <li>Заполните форму: тип структуры (linear, branching, circular, mosaic и др.), количество узлов (3–15), жанр, стилистика, эпоха. Нажмите «Сгенерировать сюжетную структуру».</li>
            <li>Появится граф сюжета и статистика. Ниже можно выбрать узел и нажать «Сгенерировать текст узла» — ИИ напишет текст для этой точки сюжета.</li>
        </ul>
    </details>
    <details style="margin-bottom:1rem;">
        <summary style="cursor:pointer; font-weight:600;">Подробно: Ветвящиеся истории (Branching Narrative Lab)</summary>
        <ul style="margin-top:0.5rem; padding-left:1.5rem;">
            <li>Раскройте блок «Как использовать в кабинете писателя» — там подсказки для сценаристов.</li>
            <li>В форме укажите начальную сцену и вариант выбора героя. «Создать ветвление» — ИИ сгенерирует альтернативное продолжение и анализ.</li>
            <li>Все ветвления сохраняются в «История ветвлений» с метками (Сцена 1, 2, …). При двух и более ветвлениях доступен сравнительный анализ. Кнопка «Начать заново» очищает историю.</li>
        </ul>
    </details>
    <details style="margin-bottom:1rem;">
        <summary style="cursor:pointer; font-weight:600;">Подробно: Трансформация медиума (Form Shifter)</summary>
        <ul style="margin-top:0.5rem; padding-left:1.5rem;">
            <li>Введите исходный текст (от 50 символов, максимум 2500) и выберите целевой формат: пьеса, сценарий, подкаст, комикс, визуальный роман, игровая сцена, дневниковая запись, соцсетевой пост, поэтическая версия.</li>
            <li>«Преобразовать текст» — получите вариант в выбранном формате и краткое объяснение изменений.</li>
        </ul>
    </details>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("При ошибках API (ключ не найден, 401) откройте блок «Инструкция по настройке API ключа» в сообщении об ошибке или настройте файл `.env` и перезапустите приложение.")

# ==================== ВКЛАДКА 1: ЛАБОРАТОРИЯ ЖАНРОВ ====================
elif st.session_state.current_tab == "generator":
    # ==================== ОСНОВНАЯ ОБЛАСТЬ ====================
    
    if not selected_genre:
        st.error("Ошибка: жанр не найден.")
        st.stop()
    
    # Блок 1: Описание жанра
    st.header(f"📖 {selected_genre.name}")
    st.markdown(f"""
    <div class="genre-description-block" style='background: #ffffff; padding: 1.5rem; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 1.5rem;'>
        <p style='font-size: 1.0625rem; color: #374151; margin: 0; line-height: 1.7;'>{selected_genre.description}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Сворачиваемые блоки (как везде — details/summary)
    def _esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    features_li = "".join(f"<li>{_esc(f)}</li>" for f in selected_genre.typical_features)
    schema_li = "".join(f"<li>{_esc(step)}</li>" for step in selected_genre.structural_schema)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <details style="margin-bottom:1rem;">
            <summary style="cursor:pointer; font-weight:600;">Типичные признаки</summary>
            <ul style="margin-top:0.5rem; padding-left:1.5rem;">{features_li}</ul>
        </details>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <details style="margin-bottom:1rem;">
            <summary style="cursor:pointer; font-weight:600;">Структурная схема</summary>
            <ol style="margin-top:0.5rem; padding-left:1.5rem;">{schema_li}</ol>
        </details>
        """, unsafe_allow_html=True)
    st.markdown("---")
    
    # Блок 2: Профиль жанра (радар)
    st.header("📊 Профиль жанра")
    st.markdown("""
    <details style="margin-bottom:1rem;">
        <summary style="cursor:pointer; font-weight:600;">Что означают оси радара</summary>
        <ul style="margin-top:0.5rem; padding-left:1.5rem;">
            <li><strong>Сюжетность</strong> — насколько развит сюжет</li>
            <li><strong>Описательность</strong> — уровень детализации</li>
            <li><strong>Конфликтность</strong> — выраженность конфликта</li>
            <li><strong>Лиричность</strong> — эмоциональность и отступления</li>
            <li><strong>Условность</strong> — степень условности/фантастичности</li>
            <li><strong>Нравственная окраска</strong> — моральная позиция</li>
            <li><strong>Социальность</strong> — социальный контекст</li>
        </ul>
    </details>
    """, unsafe_allow_html=True)
    
    radar_fig = build_radar_chart(selected_genre.radar_profile)
    st.plotly_chart(radar_fig, use_container_width=True)

    st.markdown("---")

    # Блок 3: Генерация текста — карточка и одна кнопка
    st.markdown("""
    <div class="generation-card" style="background:#fff; border-radius:12px; padding:1.5rem; margin-bottom:1.25rem; border:1px solid #e5e7eb; box-shadow:0 1px 3px rgba(0,0,0,0.06);">
        <h2 style="margin:0 0 0.5rem 0; font-size:1.35rem; color:#111827;">✍️ Генерация текста</h2>
        <p style="margin:0 0 1rem 0; font-size:0.9375rem; color:#6b7280; line-height:1.5;">Сгенерируйте черновик в выбранном жанре — затем его можно отредактировать, проанализировать и при желании «сломать» жанр.</p>
        <details style="margin-top:0.5rem;">
            <summary style="cursor:pointer; font-size:0.875rem; color:#6b7280;">Подсказка: шаги работы</summary>
            <p style="margin:0.5rem 0 0 0; font-size:0.875rem; color:#4b5563;">Шаг 1 — сгенерировать текст. Шаг 2 — проанализировать соответствие жанру. Шаг 3 — при желании использовать режим «Сломать жанр».</p>
        </details>
    </div>
    """, unsafe_allow_html=True)
    if st.button("🔄 Сгенерировать текст", type="primary", use_container_width=True):
        with st.status("Генерация текста...", expanded=True) as status:
            try:
                status.write("Подготавливаю промпт...")
                system_prompt = load_prompt(
                    "prompts/generate_prompt.txt",
                    fallback="Ты — опытный литературный автор. Создай текст в заданном жанре с учётом всех параметров."
                )
                
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
                
                status.write("Отправляю запрос в LLM...")
                generated = generate_text(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.8,
                    max_tokens=st.session_state.params.target_length * 2,
                    ensure_complete=True
                )

                st.session_state.generated_text = generated
                st.session_state.analysis_result = None  # Сбрасываем анализ
                st.session_state.broken_text = ""  # Сбрасываем сломанный текст
                status.update(label="Готово", state="complete")
                st.success("Текст успешно сгенерирован!")
                
            except ValueError as e:
                # Ошибка отсутствия API ключа
                status.update(label="Ошибка", state="error")
                st.error("❌ Проблема с API ключом")
                st.error(str(e))
                render_api_key_error_block()
            except RuntimeError as e:
                # Ошибка API (включая 401)
                status.update(label="Ошибка", state="error")
                error_str = str(e)
                if "401" in error_str or "авторизации" in error_str.lower():
                    st.error(error_str)
                    st.markdown("""
                    <details open style="margin-bottom:1rem;">
                        <summary style="cursor:pointer; font-weight:600;">🔧 Как исправить</summary>
                        <p style="margin-top:0.5rem;"><strong>Проверьте:</strong></p>
                        <ol style="margin:0.25rem 0 0 1.25rem; padding:0;">
                            <li>Файл <code>.env</code> существует в корне проекта</li>
                            <li>В <code>.env</code> есть строка <code>DEEPSEEK_API_KEY=...</code> (или <code>GROK_API_KEY=...</code>)</li>
                            <li>API ключ скопирован полностью, без лишних символов</li>
                            <li>Ключ активен у выбранного провайдера</li>
                        </ol>
                        <p style="margin-top:0.5rem;"><strong>После исправления перезапустите приложение!</strong></p>
                    </details>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"Ошибка при генерации текста: {error_str}")
            except Exception as e:
                status.update(label="Ошибка", state="error")
                st.error(f"Неожиданная ошибка: {str(e)}")
                st.info("Проверьте логи для деталей.")
    
    # Отображение сгенерированного текста
    if st.session_state.generated_text:
        st.subheader("Сгенерированный текст:")
        
        # Обёртка для улучшения читаемости
        st.markdown('<div class="generated-text">', unsafe_allow_html=True)
        
        st.markdown("**Предпросмотр (потоковый вывод):**")
        st.write_stream(stream_text(st.session_state.generated_text))
        st.markdown("---")

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
                    if analysis.get("error"):
                        st.warning("Анализ завершён с предупреждением: модель вернула некорректный формат, показан безопасный результат.")
                    else:
                        st.success("Анализ завершён!")
                except ValueError as e:
                    st.error("❌ Проблема с API ключом")
                    st.error(str(e))
                    render_api_key_error_block()
                except RuntimeError as e:
                    error_str = str(e)
                    if "401" in error_str or "авторизации" in error_str.lower():
                        st.error(error_str)
                        st.markdown("""
                        <details open style="margin-bottom:1rem;">
                            <summary style="cursor:pointer; font-weight:600;">🔧 Как исправить</summary>
                            <p style="margin-top:0.5rem;"><strong>Проверьте:</strong></p>
                            <ol style="margin:0.25rem 0 0 1.25rem; padding:0;">
                                <li>Файл <code>.env</code> существует и содержит <code>DEEPSEEK_API_KEY=...</code> (или <code>GROK_API_KEY=...</code>)</li>
                                <li>API ключ скопирован полностью, без лишних символов</li>
                                <li>API ключ активен у выбранного провайдера</li>
                            </ol>
                            <p style="margin-top:0.5rem;"><strong>После исправления перезапустите приложение!</strong></p>
                        </details>
                        """, unsafe_allow_html=True)
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
                        render_api_key_error_block()
                    except RuntimeError as e:
                        error_str = str(e)
                        if "401" in error_str or "авторизации" in error_str.lower():
                            st.error(error_str)
                            render_api_key_error_block()
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
        st.caption("👆 Нажмите «Сгенерировать текст» выше — появится черновик в выбранном жанре.")

# ==================== ВКЛАДКА 2: АНАЛИЗ МОЕГО ТЕКСТА ====================
elif st.session_state.current_tab == "analysis":
    # ==================== ВКЛАДКА "АНАЛИЗ МОЕГО ТЕКСТА" ====================
    st.header("📝 Анализ моего текста")
    st.markdown("""
    Загрузите файл **.txt** или вставьте отрывок — получите разбор: жанр, структура, тип повествователя, фокализация и стиль с цитатами из текста.
    """)
    st.caption("💡 Жанр, выбранный в панели настроек слева, используется как контекст: в объяснении будет учтено соответствие текста этому жанру.")
    
    with st.form("user_text_form"):
        uploaded_file = st.file_uploader(
            "Загрузите текстовый файл (.txt)",
            type=["txt"],
            help="Выберите файл с текстом для анализа"
        )
        
        user_text = st.text_area(
            "Или введите текст вручную:",
            value=st.session_state.user_text_input,
            height=300,
            help="Вставьте текст для анализа"
        )
        submitted = st.form_submit_button("🔍 Анализировать текст")
    
    # Обновляем session state
    if user_text != st.session_state.user_text_input:
        st.session_state.user_text_input = user_text
        st.session_state.user_text_analysis = None  # Сбрасываем анализ при изменении текста
    
    # Обработка загруженного файла (даёт приоритет содержимому файла)
    if uploaded_file is not None:
        try:
            file_content = uploaded_file.read().decode("utf-8")
            st.session_state.user_text_input = file_content
            user_text = file_content
            st.success("Файл успешно загружен!")
        except Exception as e:
            st.error(f"Ошибка при чтении файла: {str(e)}")
    
    # Кнопка анализа
    if submitted:
        if not user_text or len(user_text.strip()) < 50:
            st.warning("⚠️ Текст слишком короткий. Введите или загрузите текст длиной не менее 50 символов.")
        else:
            with st.spinner("Анализирую текст..."):
                try:
                    # Учитываем выбранный в настройках жанр как контекст для анализа
                    _expected_genre = get_genre_by_id(st.session_state.selected_genre_id) if st.session_state.get("selected_genre_id") else None
                    analysis = analyze_user_text(user_text, all_genres, expected_genre_name=_expected_genre.name if _expected_genre else None)
                    st.session_state.user_text_analysis = analysis
                    st.success("Анализ завершён!")
                except ValueError as e:
                    st.error("❌ Проблема с API ключом")
                    st.error(str(e))
                    render_api_key_error_block()
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
            parts = []
            for item in evidence:
                aspect = item.get("aspect", "")
                quote = item.get("quote", "")
                explanation = item.get("explanation", "")
                if quote and explanation:
                    q_esc = quote.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                    ex_esc = explanation.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                    parts.append(f"""
                    <details style="margin-bottom:0.75rem;">
                        <summary style="cursor:pointer; font-weight:600;">🔖 {aspect.capitalize()}</summary>
                        <p style="margin-top:0.5rem;"><strong>Цитата:</strong></p>
                        <blockquote style="margin:0.25rem 0; padding-left:1rem; border-left:3px solid #e2e8f0;">{q_esc}</blockquote>
                        <p style="margin-top:0.5rem;"><strong>Объяснение:</strong> {ex_esc}</p>
                    </details>
                    """)
            if parts:
                st.markdown("<div>" + "".join(parts) + "</div>", unsafe_allow_html=True)
        else:
            st.info("Цитаты-доказательства не предоставлены.")
        
        # Закрываем обёртку блока анализа пользовательского текста
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== ВКЛАДКА 3: НАРРАТИВНАЯ ПЕСОЧНИЦА ====================
elif st.session_state.current_tab == "playground":
    st.header("🎭 Нарративная песочница")
    st.markdown("""
    **Нарративная песочница** — экспериментальная площадка для изучения трансмедиальности,
    нелинейного сторителлинга, ветвящихся нарративов и сюжетных структур.
    
    Исследуйте различные нарративные формы, создавайте ветвящиеся истории и экспериментируйте 
    с трансформацией текста между различными медиаформатами.
    """)
    st.caption("💡 Настройки в панели слева относятся к разделу «Генератор историй» и «Анализ текста». Здесь у каждого инструмента свои параметры — задавайте жанр и контекст прямо в формах ниже.")
    st.markdown("---")
    
    # Секция 1: Конструктор сюжета (Plot Builder)
    st.subheader("🏗️ Конструктор сюжета (Plot Builder)")
    st.info("💡 **Для сценаристов:** Узлы — это сцены или ключевые точки. Выберите тип структуры под задачу; пояснения — в раскрывающемся списке ниже.")
    st.markdown("""
    Создайте структурированную сюжетную схему с узлами и связями. 
    Выберите тип структуры, количество узлов и параметры жанра.
    """)
    
    # Типы структуры: русские названия для UI, английские — для API
    STRUCTURE_OPTIONS = [
        ("linear", "Линейная", "События в хронологическом порядке, классическая драматургия (завязка — развитие — развязка)."),
        ("branching", "Ветвящаяся", "Несколько путей развития, точки выбора героя; подходит для интерактива и игровых сценариев."),
        ("circular", "Кольцевая", "Сюжет возвращается к началу, цикл; конец перекликается с началом."),
        ("mosaic", "Мозаичная", "Фрагменты и сцены в нелинейном порядке; общая картина складывается из кусочков."),
        ("Rashomon", "Рашомон", "Одно и то же событие показано с разных точек зрения персонажей; различающиеся версии."),
        ("split-perspective", "Раздельная перспектива", "Параллельные сюжетные линии или переключение между героями/временами."),
        ("epistolary", "Эпистолярная", "Структура из писем, дневников, документов; повествование через «документы»."),
    ]
    structure_labels = [opt[1] for opt in STRUCTURE_OPTIONS]
    structure_value_by_label = {opt[1]: opt[0] for opt in STRUCTURE_OPTIONS}
    
    # Свои настройки песочницы — нейтральные по умолчанию (не из сайдбара)
    with st.form("plot_builder_form"):
        plot_col1, plot_col2 = st.columns(2)
        
        with plot_col1:
            structure_label = st.selectbox(
                "Тип структуры:",
                options=structure_labels,
                help="Выберите тип сюжетной структуры"
            )
            structure_type = structure_value_by_label[structure_label]
            
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
        
        plot_submitted = st.form_submit_button("🔄 Сгенерировать сюжетную структуру")
    
    # Пояснения к типам структуры (открывающийся список)
    structure_details_items = "".join(
        f'<li><strong>{opt[1]}</strong> — {opt[2]}</li>' for opt in STRUCTURE_OPTIONS
    )
    st.markdown(f"""
    <details style="margin-top:0.75rem; margin-bottom:1rem;">
        <summary style="cursor:pointer; font-weight:600;">Что означают типы структуры?</summary>
        <ul style="margin-top:0.5rem; padding-left:1.5rem;">{structure_details_items}</ul>
    </details>
    """, unsafe_allow_html=True)
    
    if plot_submitted:
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
                render_api_key_error_block()
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
    <details open style="margin-bottom:1rem;">
        <summary style="cursor:pointer; font-weight:600;">📖 Как использовать в кабинете писателя</summary>
        <p style="margin-top:0.5rem;"><strong>Ветвления полезны, когда нужно:</strong></p>
        <ul style="margin:0.25rem 0 0 1.25rem; padding:0;">
            <li>Продумать <strong>точки выбора</strong> героя (моральная дилемма, поворот сюжета, точка невозврата).</li>
            <li>Сравнить <strong>альтернативные развития</strong> одной сцены и увидеть, как меняются жанр, тон и напряжение.</li>
            <li>Подготовить <strong>интерактивный сценарий</strong> или черновик для игр/выборных историй.</li>
        </ul>
        <p style="margin-top:0.5rem;"><strong>Совет:</strong> Задавайте начальную сцену чётко (место, персонажи, конфликт). Вариант выбора формулируйте как действие или решение героя — так модель лучше строит продолжение.</p>
    </details>
    """, unsafe_allow_html=True)
    
    st.caption("Опишите сцену и выбор героя — система сгенерирует альтернативное продолжение и покажет, как меняются жанр, фокализация, стиль и напряжение.")
    
    with st.form("branching_form"):
        initial_scene = st.text_area(
            "Начальная сцена:",
            value=st.session_state.branching_scene,
            height=150,
            help="Опишите начальную сцену или текущее состояние истории"
        )
        
        choice = st.text_input(
            "Вариант выбора:",
            placeholder="Например: Герой решает пойти налево",
            help="Опишите выбор, который приведёт к ветвлению истории"
        )
        
        branching_submitted = st.form_submit_button("✨ Создать ветвление")
    
    if initial_scene != st.session_state.branching_scene:
        st.session_state.branching_scene = initial_scene
        st.session_state.branching_history = []  # Сбрасываем историю при изменении сцены
    
    if branching_submitted:
        if not initial_scene or len(initial_scene.strip()) < 20:
            st.warning("⚠️ Начальная сцена должна содержать не менее 20 символов.")
        elif not choice or len(choice.strip()) < 5:
            st.warning("⚠️ Вариант выбора должен содержать не менее 5 символов.")
        else:
            with st.spinner("Генерирую ветвление..."):
                try:
                    # Песочница не использует сайдбар — контекст задаётся текстом сцены и выбора
                    branch = request_with_delay(
                        generate_branch,
                        initial_scene=initial_scene,
                        choice=choice,
                        previous_branches=st.session_state.branching_history,
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
                    render_api_key_error_block()
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
        st.caption("Каждое ветвление — альтернативная сцена. Метки помогают сравнивать тон, жанр и напряжение между вариантами.")
        
        for i, branch in enumerate(st.session_state.branching_history, 1):
            choice_label = (branch.get("choice") or "Выбор")[:50] + ("…" if len((branch.get("choice") or "")) > 50 else "")
            with st.expander(f"**Сцена {i}** · {choice_label}", expanded=(i == len(st.session_state.branching_history))):
                st.markdown("**Выбор героя:**")
                st.caption(branch.get("choice", "—"))
                st.markdown("**Продолжение:**")
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
                    st.markdown("**Метки для сценария:**")
                    tags = []
                    if analysis.get("genre_shift"):
                        tags.append(f"Жанр: {analysis['genre_shift']}")
                    if analysis.get("tension_change"):
                        tags.append(f"Напряжение: {analysis['tension_change']}")
                    if analysis.get("focalization_change"):
                        tags.append(f"Фокализация: {analysis['focalization_change']}")
                    if analysis.get("style_change"):
                        tags.append(f"Стиль: {analysis['style_change']}")
                    if tags:
                        st.caption(" · ".join(tags))
                    else:
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
    st.info("💡 **Для сценаристов и писателей:** Один и тот же эпизод можно переложить в пьесу, сценарий, подкаст или игровую сцену — удобно для питчей, адаптаций и проверки «звучания» в другом формате.")
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
                        # Песочница не использует сайдбар — трансформация по тексту и формату
                        transformation = request_with_delay(
                            transform_text,
                            text=transform_text_input,
                            target_format=target_format,
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
    <div class="app-footer" style='text-align: center; color: #718096; padding: 2rem; margin-top: 2rem;'>
    <p style='font-size: 1rem; font-weight: 600; color: #2d3748; margin-bottom: 0.5rem;'><strong>✨ NARRALAB</strong></p>
    <p style='font-size: 0.875rem; color: #718096; margin: 0;'>Платформа интерактивного сторителлинга с использованием ИИ</p>
    <p style='font-size: 0.75rem; color: #a0aec0; margin-top: 0.75rem;'>© 2026 NARRALAB. Все права защищены.</p>
    </div>
    """,
    unsafe_allow_html=True
)

