"""
Читает solve_log.txt и делает красивый HTML-отчёт.
Запуск: python log_to_html.py
Результат: solve_report.html
"""

import re
import html as html_lib
from pathlib import Path

LOG_PATH = Path("solve_log.txt")
OUT_PATH = Path("solve_report.html")


def parse_log(text):
    """
    Парсит лог на отдельные блоки:
    [
      {"type": "step", "num": 1, "html": "...", "action": "...", "url": "..."},
      ...
    ]
    """
    blocks = []
    # Разбиваем по "--- Итерация N ---"
    parts = re.split(r"--- Итерация (\d+) ---", text)
    # parts[0] — преамбула [START]
    # далее чередуются: номер и тело
    for i in range(1, len(parts), 2):
        num = int(parts[i])
        body = parts[i + 1] if i + 1 < len(parts) else ""

        # HTML между "=== HTML ===" и "=== END ==="
        html_match = re.search(r"=== HTML ===\s*(.*?)\s*=== END ===", body, re.S)
        html = html_match.group(1) if html_match else ""

        # Действие (строки в квадратных скобках)
        action_match = re.search(r"\[([A-Za-z+]+)\]\s*(http\S+)\s*→\s*(\d+)", body)
        action = ""
        if action_match:
            action = f"{action_match.group(1)} {action_match.group(2)} → {action_match.group(3)}"

        blocks.append({
            "num": num,
            "html": html,
            "action": action,
        })
    return blocks


def clean_html(raw_html):
    """Минимальная визуализация: оставляем как есть, но экранируем опасные теги."""
    # Ничего не убираем — просто возвращаем как есть, браузер сам отрисует
    return raw_html


def build_report(blocks, meta):
    parts = []
    parts.append("""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Отчёт по ДЗ-1</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif;
         max-width: 1100px; margin: 0 auto; padding: 20px; background: #f5f7fa; color: #222; }
  h1 { color: #1a3d6b; }
  .meta { background: #fff; padding: 16px; border-radius: 8px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 24px; }
  .meta code { background: #eef; padding: 2px 6px; border-radius: 4px; }
  .step { background: #fff; border-radius: 8px; padding: 16px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 16px; }
  .step h2 { margin: 0 0 8px 0; font-size: 18px; color: #1a3d6b; }
  .action { display: inline-block; background: #e8f0fe; color: #174ea6;
            padding: 4px 10px; border-radius: 4px; font-family: monospace;
            font-size: 13px; margin-bottom: 12px; }
  .html-preview { background: #fafafa; border: 1px solid #ddd; border-radius: 6px;
                  padding: 12px; overflow-x: auto; font-family: monospace;
                  font-size: 12px; white-space: pre-wrap; word-break: break-word;
                  max-height: 400px; overflow-y: auto; }
  .secret { background: #d4edda; border: 2px solid #28a745; color: #155724;
            padding: 16px; border-radius: 8px; font-size: 18px;
            font-weight: bold; margin-top: 24px; text-align: center; }
  .summary { background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px;
             border-radius: 4px; margin-bottom: 24px; }
</style>
</head>
<body>
""")
    parts.append(f"<h1>Отчёт по ДЗ-1</h1>")

    # Мета-блок
    parts.append('<div class="meta">')
    parts.append(f"<p><b>Токен пользователя:</b> <code>{meta['user_token']}</code></p>")
    parts.append(f"<p><b>Всего шагов в логе:</b> {len(blocks)}</p>")
    if meta.get("secret"):
        parts.append(f"<p><b>Секретный токен:</b> <code>{meta['secret']}</code></p>")
    parts.append('</div>')

    if meta.get("secret"):
        parts.append(f'<div class="secret">SECRET TOKEN: {meta["secret"]}</div>')

    # Шаги
    for b in blocks:
        parts.append('<div class="step">')
        parts.append(f'<h2>Шаг {b["num"]}</h2>')
        if b["action"]:
            parts.append(f'<div class="action">{html_lib.escape(b["action"])}</div>')
        # Рендерим HTML как есть (браузер покажет таблицу)
        parts.append('<details><summary>HTML запроса</summary>')
        parts.append(f'<div class="html-preview">{b["html"]}</div>')
        parts.append('</details>')
        parts.append('</div>')

    parts.append("</body></html>")
    return "\n".join(parts)


def main():
    if not LOG_PATH.exists():
        print(f"Файл {LOG_PATH} не найден.")
        return

    text = LOG_PATH.read_text(encoding="utf-8")

    # Извлекаем мета-данные
    user_token_match = re.search(r"user=([a-f0-9]{32})", text)
    secret_match = re.search(r"SECRET TOKEN:\s*([a-f0-9]+)", text)

    meta = {
        "user_token": user_token_match.group(1) if user_token_match else "?",
        "secret": secret_match.group(1) if secret_match else None,
    }

    blocks = parse_log(text)
    report = build_report(blocks, meta)
    OUT_PATH.write_text(report, encoding="utf-8")

    print(f"Готово: {OUT_PATH}")
    print(f"Шагов: {len(blocks)}")
    if meta["secret"]:
        print(f"Секретный токен: {meta['secret']}")


if __name__ == "__main__":
    main()
