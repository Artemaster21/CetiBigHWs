import requests
import re
import sys

BASE = "http://hw1.alexbers.com"
USER_TOKEN = "91e7c7839a479f5895216100cb651a6a"

LOG_FILE = open("solve_log.txt", "w", encoding="utf-8")

def log(*args, **kwargs):
    print(*args, **kwargs)
    print(*args, **kwargs, file=LOG_FILE, flush=True)


s = requests.Session()
s.cookies.set("user", USER_TOKEN)


def parse_all_tables(html):
    """
    Возвращает список таблиц.
    Каждая таблица — список пар (key, value).
    """
    tables = []
    # Находим все таблицы
    for table_html in re.findall(r"<table[^>]*>(.*?)</table>", html, re.S):
        # Внутри таблицы ищем все пары <td><code>...</code></td>
        cells = re.findall(
            r"<td><code>([^<]+)</code></td>",
            table_html,
            re.S,
        )
        # Группируем по 2: (key, value)
        pairs = [(cells[i], cells[i + 1]) for i in range(0, len(cells) - 1, 2)]
        if pairs:
            tables.append(pairs)
    return tables


def parse_action_url(html):
    m = re.search(r"<code>(/[^<]+)</code>", html)
    return m.group(1) if m else None


def parse_link(html):
    m = re.search(r"""<a\s+href=["']([^"']+)["']""", html)
    return m.group(1) if m else None


def step(html):
    log("\n=== HTML ===")
    log(html[:800])
    log("=== END ===\n")

    # --- Тип 1: GET (Перейдите по ссылке) ---
    if "Перейдите по" in html:
        link = parse_link(html)
        if link is None:
            log("!!! Не найдена ссылка!")
            return None

        sections = extract_tables_by_section(html)
        r = s.get(
            BASE + link,
            cookies=sections["cookie"],
            headers=sections["headers"],
            params=sections["params"],
        )
        log(f"[GET] {r.url} → {r.status_code}")
        return r.text

    # --- Тип 2: GET по <code> ---
    if "Отправьте GET-запрос" in html:
        path = parse_action_url(html)
        sections = extract_tables_by_section(html)
        r = s.get(
            BASE + path,
            cookies=sections["cookie"],
            headers=sections["headers"],
            params=sections["params"],
        )
        log(f"[GET] {r.url} → {r.status_code}")
        return r.text

    # --- Тип 3: POST ---
    if "Отправьте POST-запрос" in html:
        path = parse_action_url(html)
        sections = extract_tables_by_section(html)
        r = s.post(
            BASE + path,
            cookies=sections["cookie"],
            headers=sections["headers"],
            params=sections["params"],
            data=sections["data"],
        )
        log(f"[POST] {r.url} → {r.status_code}")
        return r.text

    # --- Тип 4: Загрузка файлов ---
    if "Загрузите файлы" in html:
        path = parse_action_url(html)
        sections = extract_tables_by_section(html)
        # Для загрузки файлов таблица "Имя файла / Содержимое" — это sections["data"] или первая таблица
        files = {}
        # Перебираем все таблицы, чтобы найти правильную (Имя файла / Содержимое)
        for m in re.finditer(r"<table[^>]*>(.*?)</table>", html, re.S):
            table_html = m.group(1)
            cells = re.findall(r"<td><code>([^<]+)</code></td>", table_html, re.S)
            pairs = [(cells[i], cells[i + 1]) for i in range(0, len(cells) - 1, 2)]
            # Проверяем, что это таблица файлов: имена файлов содержат точку
            if pairs and "." in pairs[0][0]:
                for filename, content in pairs:
                    files[filename] = (filename, content.encode("utf-8"), "application/octet-stream")
                break
        r = s.post(BASE + path, files=files)
        log(f"[UPLOAD] {r.url} → {r.status_code}")
        return r.text

    return None

def extract_tables_by_section(html):
    """
    Разбивает HTML на секции по фразам и извлекает из каждой таблицу.
    Возвращает dict: {"cookie": {...}, "headers": {...}, "params": {...}, "data": {...}}
    """
    result = {"cookie": {}, "headers": {}, "params": {}, "data": {}}

    # Все фразы-маркеры с их "типом"
    markers = [
        (r"должны быть выставлены cookie", "cookie"),
        (r"должен иметь следующие заголовки", "headers"),
        (r"параметры запроса", "params"),
        (r"данные формы", "data"),
    ]

    # Находим все таблицы с их позициями
    tables_with_pos = []
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", html, re.S):
        table_html = m.group(1)
        cells = re.findall(r"<td><code>([^<]+)</code></td>", table_html, re.S)
        pairs = [(cells[i], cells[i + 1]) for i in range(0, len(cells) - 1, 2)]
        if pairs:
            tables_with_pos.append((m.start(), pairs))

    # Сортируем таблицы по позиции
    tables_with_pos.sort(key=lambda x: x[0])

    # Идём по HTML слева направо, ищем фразы и присваиваем следующую таблицу
    table_idx = 0
    for m in re.finditer(
        r"(должны быть выставлены cookie|должен иметь следующие заголовки|параметры запроса|данные формы)",
        html,
    ):
        phrase = m.group(1)
        phrase_pos = m.start()

        # Определяем тип
        if "cookie" in phrase:
            section = "cookie"
        elif "заголовки" in phrase:
            section = "headers"
        elif "параметры" in phrase:
            section = "params"
        else:
            section = "data"

        # Ищем таблицу, которая идёт ПОСЛЕ этой фразы, и берём первую ещё не использованную
        while table_idx < len(tables_with_pos):
            t_start, pairs = tables_with_pos[table_idx]
            if t_start > phrase_pos:
                result[section].update(dict(pairs))
                table_idx += 1
                break
            table_idx += 1

    return result

# --- Главный цикл ---
html = s.get(BASE + "/").text
log("[START]")

SECRET = None
for i in range(530):
    try:
        m = re.search(r"\b[a-f0-9]{32}\b", html)
        if m and "Шаг" not in html:
            SECRET = m.group(0)
            log("\n=== SECRET TOKEN:", SECRET, "===")
            break

        log(f"\n--- Итерация {i + 1} ---")
        new_html = step(html)
        if new_html is None:
            log("Неизвестный шаг. HTML:")
            log(html)
            break
        html = new_html
    except Exception as e:
        log(f"\n!!! Ошибка на итерации {i + 1}: {e}")
        log(f"Последний HTML:\n{html}")
        break

log(f"\nВсего итераций: {i + 1}")
log(f"Секретный токен: {SECRET}")
LOG_FILE.close()
