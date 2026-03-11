# Инструкция по конвертации TECHNICAL.md в Word

## Установка необходимых библиотек

Для конвертации markdown в Word требуется библиотека `python-docx`.

### Установка через pip:

```bash
pip install python-docx
```

Или если используете виртуальное окружение:

```bash
source venv/bin/activate  # macOS/Linux
# или
venv\Scripts\activate     # Windows

pip install python-docx
```

## Запуск конвертации

После установки библиотеки выполните:

```bash
python convert_to_word.py
```

Или:

```bash
python3 convert_to_word.py
```

## Результат

После успешного выполнения скрипта будет создан файл `TECHNICAL.docx` в корне проекта.

## Альтернативный способ (через pandoc)

Если у вас установлен pandoc, вы можете использовать его напрямую:

```bash
pandoc TECHNICAL.md -o TECHNICAL.docx
```

Установка pandoc:
- macOS: `brew install pandoc`
- Linux: `sudo apt-get install pandoc` (Ubuntu/Debian)
- Windows: скачайте с https://pandoc.org/installing.html
