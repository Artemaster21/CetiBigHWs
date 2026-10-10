"""
Решение ДЗ-1 (вариант на 12 баллов, ручное формирование HTTP).
Использует только socket + re, без requests.
"""

import socket
import re
from urllib.parse import urlencode


HOST = "hw1.alexbers.com"
PORT = 80
BASE = f"http://{HOST}"
USER_TOKEN = "91e7c7839a479f5895216100cb651a6a"

LOG_FILE = open("raw_log.txt", "w", encoding="utf-8")


def log(*args, **kwargs):
    print(*args, **kwargs)
    print(*args, **kwargs, file=LOG_FILE, flush=True)


# ---------- HTTP через сокет ----------

def http_request(method, path, headers=None, cookies=None, params=None, data=None):
    """
    Формирует HTTP-запрос вручную и отправляет через сокет.
    Возвращает распарсенный HTML (строку).
    """
    headers = dict(headers) if headers else {}
    cookies = dict(cookies) if cookies else {}

    # Добавляем user-cookie всегда
    cookies["user"] = USER_TOKEN

    # Формируем query string
    if params:
        query = urlencode(params)
        if "?" in path:
            path += "&" + query
        else:
            path += "?" + query

    # Формируем тело
    body = b""
    if data:
        body = urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Content-Length"] = str(len(body))

    # Cookie-строка
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())

    # Собираем запрос
    request_line = f"{method} {path} HTTP/1.1\r\n"
    request_headers = f"Host: {HOST}\r\n"
    request_headers += f"Cookie: {cookie_str}\r\n"
    request_headers += "Connection: close\r\n"
    request_headers += "User-Agent: raw-http-client/1.0\r\n"
    for k, v in headers.items():
        request_headers += f"{k}: {v}\r\n"
    request_headers += "\r\n"

    raw_request = request_line.encode("utf-8") + request_headers.encode("utf-8") + body

    # Отправляем
    s = socket.create_connection((HOST, PORT), timeout=10)
    s.sendall(raw_request)

    # Читаем ответ
    response = b""
    while True:
        chunk = s.recv(8192)
        if not chunk:
            break
        response += chunk
    s.close()

    # Разделяем заголовки и тело
    text = response.decode("utf-8", errors="replace")
    if "\r\n\r\n" in text:
        head, body_text = text.split("\r\n\r\n", 1)
        log(f"    {head.splitlines()[0]}")  # статус-строка
        return body_text
    return text


# ---------- Парсинг HTML ----------

def parse_action_url(html):
    m = re.search(r"<code>(/[^<]+)</code>", html)
    return m.group(1) if m else None


def parse_link(html):
    m = re.search(r"""<a\s+href=["']([^"']+)["']""", html)
    return m.group(1) if m else None


def parse_all_tables(html):
    """Возвращает список таблиц, каждая — список (key, value)."""
    tables = []
    for table_html in re.findall(r"<table[^>]*>(.*?)</table>", html, re.S):
        cells = re.findall(r"<td><code>([^<]+)</code></td>", table_html, re.S)
        pairs = [(cells[i], cells[i + 1]) for i in range(0, len(cells) - 1, 2)]
        if pairs:
            tables.append(pairs)
    return tables


def extract_sections(html):
    """Возвращает dict с cookie / headers / params / data по фразам."""
    result = {"cookie": {}, "headers": {}, "params": {}, "data": {}}

    markers = [
        (r"должны быть выставлены cookie", "cookie"),
        (r"должен иметь следующие заголовки", "headers"),
        (r"параметры запроса", "params"),
        (r"данные формы", "data"),
    ]

    # Все таблицы с позициями
    tables = []
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", html, re.S):
        cells = re.findall(r"<td><code>([^<]+)</code></td>", m.group(1), re.S)
        pairs = [(cells[i], cells[i + 1]) for i in range(0, len(cells) - 1, 2)]
        if pairs:
            tables.append((m.start(), pairs))
    tables.sort(key=lambda x: x[0])

    table_idx = 0
    for m in re.finditer("|".join(p for p, _ in markers), html):
        phrase = m.group(0)
        section = next(s for p, s in markers if p == phrase)
        while table_idx < len(tables):
            t_start, pairs = tables[table_idx]
            if t_start > m.start():
                result[section].update(dict(pairs))
                table_idx += 1
                break
            table_idx += 1

    return result


# ---------- Логика шага ----------

def step(html):
    log("\n=== HTML ===")
    log(html[:600])
    log("=== END ===\n")

    # Тип 1: Перейдите по ссылке
    if "Перейдите по" in html:
        link = parse_link(html)
        sections = extract_sections(html)
        html = http_request(
            "GET", link,
            cookies=sections["cookie"],
            headers=sections["headers"],
            params=sections["params"],
        )
        return html

    # Тип 2: GET
    if "Отправьте GET-запрос" in html:
        path = parse_action_url(html)
        sections = extract_sections(html)
        html = http_request(
            "GET", path,
            cookies=sections["cookie"],
            headers=sections["headers"],
            params=sections["params"],
        )
        return html

    # Тип 3: POST
    if "Отправьте POST-запрос" in html:
        path = parse_action_url(html)
        sections = extract_sections(html)
        html = http_request(
            "POST", path,
            cookies=sections["cookie"],
            headers=sections["headers"],
            params=sections["params"],
            data=sections["data"],
        )
        return html

    # Тип 4: Загрузка файлов
    if "Загрузите файлы" in html:
        path = parse_action_url(html)
        tables = parse_all_tables(html)
        # Для загрузки файлов нужна multipart/form-data — соберём вручную
        boundary = "----RawBoundary7MA4YWxkTrZu0gW"
        body_parts = []
        if tables:
            for filename, content in tables[0]:
                body_parts.append(f"--{boundary}\r\n".encode())
                body_parts.append(
                    f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
                )
                body_parts.append(b"Content-Type: application/octet-stream\r\n\r\n")
                body_parts.append(content.encode("utf-8"))
                body_parts.append(b"\r\n")
        body_parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(body_parts)

        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        }
        # Формируем запрос вручную (не через http_request, т.к. body — bytes)
        cookies = {"user": USER_TOKEN}
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())

        request_line = f"POST {path} HTTP/1.1\r\n"
        request_headers = f"Host: {HOST}\r\n"
        request_headers += f"Cookie: {cookie_str}\r\n"
        request_headers += "Connection: close\r\n"
        for k, v in headers.items():
            request_headers += f"{k}: {v}\r\n"
        request_headers += "\r\n"

        raw = request_line.encode() + request_headers.encode() + body

        s = socket.create_connection((HOST, PORT), timeout=10)
        s.sendall(raw)
        response = b""
        while True:
            chunk = s.recv(8192)
            if not chunk:
                break
            response += chunk
        s.close()

        text = response.decode("utf-8", errors="replace")
        if "\r\n\r\n" in text:
            return text.split("\r\n\r\n", 1)[1]
        return text

    return None


# ---------- Главный цикл ----------

log("[START] raw-socket client")

html = http_request("GET", "/")
SECRET = None

for i in range(530):
    m = re.search(r"\b[a-f0-9]{32}\b", html)
    if m and "Шаг" not in html:
        SECRET = m.group(0)
        log(f"\n=== SECRET TOKEN: {SECRET} ===")
        break

    log(f"\n--- Итерация {i + 1} ---")
    new_html = step(html)
    if new_html is None:
        log("Неизвестный шаг. HTML:")
        log(html)
        break
    html = new_html
else:
    log("Цикл закончился без токена.")
    log(html)

log(f"\nВсего итераций: {i + 1}")
log(f"Секретный токен: {SECRET}")
LOG_FILE.close()
