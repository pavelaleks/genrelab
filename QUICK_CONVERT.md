# Быстрая конвертация TECHNICAL.md в Word

## Способ 1: Через скрипт (рекомендуется)

### Шаг 1: Установите библиотеку

```bash
# Если используете виртуальное окружение:
source venv/bin/activate
pip install python-docx

# Или глобально:
pip install python-docx
```

### Шаг 2: Запустите скрипт

```bash
python convert_to_word.py
```

Файл `TECHNICAL.docx` будет создан в корне проекта.

---

## Способ 2: Через pandoc (если установлен)

```bash
pandoc TECHNICAL.md -o TECHNICAL.docx
```

---

## Способ 3: Вручную через Word/Google Docs

1. Откройте файл `TECHNICAL.md` в любом текстовом редакторе
2. Скопируйте весь текст
3. Откройте Microsoft Word или Google Docs
4. Вставьте текст
5. Word автоматически распознает markdown форматирование
6. Сохраните как `.docx`

---

## Способ 4: Онлайн конвертер

Используйте онлайн-сервисы для конвертации markdown в Word:
- https://www.markdowntoword.com/
- https://cloudconvert.com/md-to-docx
- https://convertio.co/ru/md-docx/

Загрузите файл `TECHNICAL.md` и скачайте результат.

---

**Текущий статус:** Файл `TECHNICAL.docx` еще не создан. Используйте один из способов выше для его создания.
