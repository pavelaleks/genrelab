"""Рендерер для гипертекстовых узлов."""

import streamlit as st


def render_hypertext_node(story_nodes: dict, node_id: str):
    """
    Рендерит гипертекстовый узел с текстом и выбором дальнейшего развития.
    
    Args:
        story_nodes: Словарь всех узлов истории {node_id: {text, choices}}
        node_id: ID текущего узла для отображения
    """
    if node_id not in story_nodes:
        st.error("❌ Узел не найден.")
        if st.button("🔁 Вернуться к началу"):
            st.query_params.clear()
            st.rerun()
        return
    
    node = story_nodes[node_id]
    
    st.markdown(f"### 📖 Узел: {node_id}")
    
    # Отображаем текст узла в стилизованном блоке
    node_text = node.get('text', 'Текст узла отсутствует.')
    st.markdown(
        f"""
        <div class="hypertext-node">
            {node_text}
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    choices = node.get("choices", [])
    
    if not choices:
        st.info("🏁 Конец ветки. Выборов нет.")
        if st.button("🔁 Вернуться к началу", use_container_width=True):
            st.query_params.clear()
            st.rerun()
        return
    
    st.markdown("#### 🎯 Выберите дальнейшее развитие:")
    
    # Отображаем кнопки выбора
    for i, ch in enumerate(choices):
        label = ch.get("label", f"Вариант {i+1}")
        target = ch.get("target")
        
        if target and st.button(label, key=f"choice_{node_id}_{i}", use_container_width=True):
            st.query_params["node"] = target
            st.rerun()
    
    st.markdown("---")
    
    if st.button("🔁 Вернуться к началу", use_container_width=True):
        st.query_params.clear()
        st.rerun()

