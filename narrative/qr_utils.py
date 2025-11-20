"""Модуль для генерации QR-кодов для доступа к приложению через ngrok."""

from io import BytesIO
from typing import Optional
import streamlit as st

# Защита импорта для qrcode
try:
    import qrcode
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "Библиотека qrcode не установлена.\n\n"
        "РЕШЕНИЕ:\n"
        "1. Убедитесь, что виртуальное окружение активировано:\n"
        "   source .venv/bin/activate  # macOS/Linux\n"
        "   .venv\\Scripts\\activate     # Windows\n\n"
        "2. Установите библиотеку:\n"
        "   pip install qrcode[pil]\n\n"
        "Или установите все зависимости сразу:\n"
        "   pip install -r requirements.txt"
    )


def create_qr(url: str, size: int = 300) -> BytesIO:
    """
    Создаёт QR-код для указанного URL.
    
    Args:
        url: URL для кодирования в QR-код
        size: Размер QR-кода в пикселях (по умолчанию 300)
        
    Returns:
        BytesIO: Изображение QR-кода в формате PNG
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Изменяем размер изображения
    img = img.resize((size, size))
    
    # Сохраняем в BytesIO
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes


def get_current_url() -> Optional[str]:
    """
    Получает текущий URL приложения Streamlit.
    
    Returns:
        Optional[str]: URL приложения или None, если не удалось определить
    """
    try:
        # Streamlit предоставляет способ получить текущий URL через query_params
        # Но для получения полного URL нужно использовать другие методы
        
        # Альтернативный способ: использовать session_state или query_params
        # В данном случае, пользователь должен ввести ngrok URL вручную
        # или мы можем попробовать получить его из переменных окружения
        
        import os
        ngrok_url = os.getenv("NGROK_URL")
        
        if ngrok_url:
            return ngrok_url
        
        # Если NGROK_URL не установлен, возвращаем None
        # Пользователь должен будет ввести URL вручную
        return None
        
    except Exception:
        return None


def display_qr_code(url: Optional[str] = None) -> None:
    """
    Отображает QR-код в Streamlit интерфейсе.
    
    Args:
        url: URL для кодирования (если None, пытается получить автоматически)
    """
    if url is None:
        url = get_current_url()
    
    if url is None:
        st.warning(
            "⚠️ URL не найден. Для работы через ngrok:\n"
            "1. Установите переменную окружения NGROK_URL\n"
            "2. Или введите URL вручную ниже"
        )
        manual_url = st.text_input(
            "Введите URL приложения (например, https://xxx.ngrok.io):",
            placeholder="https://xxx.ngrok.io"
        )
        if manual_url:
            url = manual_url
    
    if url:
        try:
            qr_img = create_qr(url)
            st.image(qr_img, caption=f"QR-код для доступа к приложению\n{url}", use_container_width=False)
            st.success(f"✅ Студенты могут отсканировать QR-код для доступа к приложению")
        except Exception as e:
            st.error(f"❌ Ошибка при создании QR-кода: {str(e)}")
