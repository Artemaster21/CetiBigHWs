"""
Читает solve_log.txt и делает HTML-отчёт с вкладками.
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
      {"num": 1, "html": "...", "action": "..."},
      ...
    ]
    """
    blocks = []
    parts = re.split(r"--- Итерация (\d+) ---", text)
    for i in range(1, len(parts), 2):
        num = int(parts[i])
        body = parts[i + 1] if i + 1 < len(parts) else ""

        html_match = re.search(r"=== HTML ===\s*(.*?)\s*=== END ===", body, re.S)
        html = html_match.group(1) if html_match else ""

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


def build_report(blocks, meta):
    parts = []
    parts.append("""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Отчёт по ДЗ-1 (вкладки)</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif;
         margin: 0; padding: 0; background: #f5f7fa; color: #222; }

  /* --- Шапка с мета-информацией --- */
  .header { background: #1a3d6b; color: #fff; padding: 16px 24px; }
  .header h1 { margin: 0 0 8px 0; font-size: 20px; }
  .header .meta { font-size: 13px; opacity: 0.9; }
  .header .meta code { background: rgba(255,255,255,0.15); padding: 2px 6px;
                       border-radius: 3px; font-family: monospace; }
  .header .secret { background: #28a745; color: #fff; padding: 8px 12px;
                    border-radius: 6px; margin-top: 8px; display: inline-block;
                    font-family: monospace; font-weight: bold; }

  /* --- Раскладка: слева табы, справа содержимое --- */
  .layout { display: flex; height: calc(100vh - 80px); }

  /* --- Левая панель с табами --- */
  .tabs {
    width: 320px;
    background: #fff;
    border-right: 1px solid #ddd;
    overflow-y: auto;
    flex-shrink: 0;
  }
  .tab {
    padding: 10px 16px;
    border-bottom: 1px solid #eee;
    cursor: pointer;
    font-size: 13px;
    transition: background 0.15s;
  }
  .tab:hover { background: #f0f4ff; }
  .tab.active { background: #e8f0fe; border-left: 4px solid #1a3d6b;
                font-weight: bold; color: #1a3d6b; }
  .tab .num { display: inline-block; min-width: 50px; color: #1a3d6b; }
  .tab .action { font-family: monospace; font-size: 11px; color: #666;
                 display: block; margin-top: 2px; word-break: break-all; }

  /* --- Правая панель с HTML --- */
  .content { flex: 1; padding: 16px; overflow-y: auto; }
  .panel { display: none; }
  .panel.active { display: block; }
  .panel h2 { margin: 0 0 12px 0; font-size: 16px; color: #1a3d6b; }
  .panel .action { display: inline-block; background: #e8f0fe; color: #174ea6;
                   padding: 4px 10px; border-radius: 4px; font-family: monospace;
                   font-size: 12px; margin-bottom: 12px; word-break: break-all; }

  /* --- Рендер HTML как есть, но в рамке --- */
  .html-render {
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 12px;
    overflow-x: auto;
    font-size: 14px;
  }
  .html-render table { border-collapse: collapse; margin: 8px 0; }
  .html-render td, .html-render th { border: 1px solid #ccc; padding: 4px 8px; }
  .html-render code { background: #f0f0f0; padding: 1px 4px; border-radius: 3px;
                      font-family: monospace; font-size: 12px; }

  /* --- Кнопки навигации --- */
  .nav { margin-bottom: 12px; }
  .nav button {
    background: #1a3d6b; color: #fff; border: none; border-radius: 4px;
    padding: 6px 12px; margin-right: 8px; cursor: pointer; font-size: 13px;
  }
  .nav button:disabled { background: #ccc; cursor: not-allowed; }
  .nav button:hover:not(:disabled) { background: #2a5a9b; }

  /* --- Скроллбар --- */
  .tabs::-webkit-scrollbar, .content::-webkit-scrollbar { width: 8px; }
  .tabs::-webkit-scrollbar-thumb, .content::-webkit-scrollbar-thumb {
    background: #bbb; border-radius: 4px;
  }
</style>
</head>
<body>
""")

    # Шапка
    parts.append('<div class="header">')
    parts.append('<h1>Отчёт по ДЗ-1</h1>')
    parts.append('<div class="meta">')
    parts.append(f"<b>Токен пользователя:</b> <code>{html_lib.escape(meta['user_token'])}</code><br>")
    parts.append(f"<b>Всего шагов:</b> {len(blocks)}")
    parts.append('</div>')
    if meta.get("secret"):
        parts.append(f'<div class="secret">SECRET TOKEN: {html_lib.escape(meta["secret"])}</div>')
    parts.append('</div>')

    # Левая панель с табами
    parts.append('<div class="layout">')
    parts.append('<div class="tabs" id="tabs">')
    for b in blocks:
        action_esc = html_lib.escape(b["action"]) if b["action"] else ""
        parts.append(
            f'<div class="tab" data-step="{b["num"]}" onclick="showStep({b["num"]})">'
            f'<span class="num">Шаг {b["num"]}</span>'
            f'<span class="action">{action_esc}</span>'
            f'</div>'
        )
    parts.append('</div>')

    # Правая панель с содержимым
    parts.append('<div class="content" id="content">')

    # Навигация
    parts.append('<div class="nav">')
    parts.append('<button id="prevBtn" onclick="prevStep()">← Назад</button>')
    parts.append('<button id="nextBtn" onclick="nextStep()">Вперёд →</button>')
    parts.append('</div>')

    # Все панели (скрытые)
    for b in blocks:
        action_esc = html_lib.escape(b["action"]) if b["action"] else ""
        parts.append(f'<div class="panel" id="panel-{b["num"]}">')
        parts.append(f'<h2>Шаг {b["num"]}</h2>')
        if b["action"]:
            parts.append(f'<div class="action">{action_esc}</div>')
        # Рендерим HTML как есть
        parts.append(f'<div class="html-render">{b["html"]}</div>')
        parts.append('</div>')

    parts.append('</div>')  # content
    parts.append('</div>')  # layout

    # JS для управления вкладками
    parts.append("""
<script>
  let currentStep = 1;
  const totalSteps = %d;

  function showStep(num) {
    // Скрываем все панели
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    // Убираем active у всех табов
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));

    // Показываем нужную панель
    const panel = document.getElementById('panel-' + num);
    if (panel) panel.classList.add('active');

    // Подсвечиваем таб
    const tab = document.querySelector('.tab[data-step="' + num + '"]');
    if (tab) {
      tab.classList.add('active');
      // Прокручиваем таб в видимую область
      tab.scrollIntoView({block: 'nearest', behavior: 'smooth'});
    }

    currentStep = num;

    // Обновляем состояние кнопок
    document.getElementById('prevBtn').disabled = (num <= 1);
    document.getElementById('nextBtn').disabled = (num >= totalSteps);

    // Сбрасываем скролл правой панели наверх
    document.getElementById('content').scrollTop = 0;
  }

  function prevStep() {
    if (currentStep > 1) showStep(currentStep - 1);
  }

  function nextStep() {
    if (currentStep < totalSteps) showStep(currentStep + 1);
  }

  // Горячие клавиши: ← и → для навигации
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') prevStep();
    if (e.key === 'ArrowRight') nextStep();
  });

  // Открываем первый шаг при загрузке
  window.addEventListener('DOMContentLoaded', () => showStep(1));
</script>
""" % len(blocks))

    parts.append("</body></html>")
    return "\n".join(parts)


def main():
    if not LOG_PATH.exists():
        print(f"Файл {LOG_PATH} не найден.")
        return

    text = LOG_PATH.read_text(encoding="utf-8")

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
