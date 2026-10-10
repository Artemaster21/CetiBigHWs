#!/bin/bash
# Решение ДЗ-1 (вариант на 10 баллов, curl/wget)
# Проходит всю цепочку заданий и печатает финальный токен.

set -e

BASE="http://hw1.alexbers.com"
USER_TOKEN="91e7c7839a479f5895216100cb651a6a"
COOKIE="user=$USER_TOKEN"
LOG="curl_log.txt"
: > "$LOG"

# --- Утилиты ---

# Извлекает URL из <code>/...</code> после "адресу"
parse_action_url() {
    echo "$1" | grep -oP '(?<=адресу <code>)/[^<]+' | head -1
}

# Извлекает ссылку из <a href="..."> или <a href='...'>
parse_link() {
    echo "$1" | grep -oP "(?<=<a href=[\"'])/[^\"']+" | head -1
}

# Извлекает пары (key, value) из ВСЕХ таблиц в порядке появления.
# Печатает: "key<TAB>value" — по одной паре на строку.
parse_table_pairs() {
    echo "$1" | grep -oP '<td><code>[^<]+</code></td>' \
        | sed -E 's|</?td>||g; s|<code>||g; s|</code>||g'
}

# Получить N-й заголовок из HTML-блока headers
# (используем позиционный счётчик)
extract_section_pairs() {
    # $1 = html
    # $2 = тип: cookie | headers | params | data
    # $3 = номер таблицы этого типа (0 по умолчанию)
    local html="$1" type="$2" idx="${3:-0}"
    python3 - "$html" "$type" "$idx" <<'EOF'
import sys, re
html, typ, idx = sys.argv[1], sys.argv[2], int(sys.argv[3])
markers = {
    "cookie": r"должны быть выставлены cookie",
    "headers": r"должен иметь следующие заголовки",
    "params": r"параметры запроса",
    "data": r"данные формы",
}
# Находим все таблицы и их позиции
tables = []
for m in re.finditer(r"<table[^>]*>(.*?)</table>", html, re.S):
    cells = re.findall(r"<td><code>([^<]+)</code></td>", m.group(1), re.S)
    pairs = [(cells[i], cells[i+1]) for i in range(0, len(cells)-1, 2)]
    if pairs:
        tables.append((m.start(), pairs))
tables.sort(key=lambda x: x[0])

# Идём по HTML и назначаем таблицы фразам
table_idx = 0
assigned = {k: [] for k in markers}
for m in re.finditer("|".join(markers.values()), html):
    phrase = m.group(0)
    section = next(k for k, v in markers.items() if v == re.escape(phrase) or v == phrase)
    while table_idx < len(tables):
        t_start, pairs = tables[table_idx]
        if t_start > m.start():
            assigned[section].append(pairs)
            table_idx += 1
            break
        table_idx += 1

if idx < len(assigned[typ]):
    for k, v in assigned[typ][idx]:
        print(f"{k}\t{v}")
EOF
}

# Формирует строку cookie из пар (key=value; key2=value2)
build_cookie_string() {
    echo "$1" | awk -F'\t' '{printf "%s=%s;", $1, $2}' | sed 's/;$//'
}

# Формирует -H "k: v" аргументы
build_header_args() {
    while IFS=$'\t' read -r k v; do
        printf -- "-H\n%s: %s\n" "$k" "$v"
    done
}

# Формирует --data-urlencode "k=v" аргументы
build_data_args() {
    while IFS=$'\t' read -r k v; do
        printf -- "--data-urlencode\n%s=%s\n" "$k" "$v"
    done
}

# --- Обработка шага ---

current_path="/"
i=0
SECRET=""

while true; do
    i=$((i + 1))
    echo "--- Итерация $i ---" | tee -a "$LOG"

    # GET текущий URL
    URL="$BASE$current_path"
    HTML=$(curl -s -b "$COOKIE" "$URL")
    echo "$HTML" >> "$LOG"

    # Проверка на финальный токен
    if ! echo "$HTML" | grep -q "Шаг"; then
        SECRET=$(echo "$HTML" | grep -oP '\b[a-f0-9]{32}\b' | head -1)
        if [ -n "$SECRET" ]; then
            echo "=== SECRET TOKEN: $SECRET ===" | tee -a "$LOG"
            break
        fi
    fi

    # Определяем тип шага
    if echo "$HTML" | grep -q "Перейдите по"; then
        # --- Тип 1: GET по ссылке (query или cookie) ---
        LINK=$(parse_link "$HTML")
        if echo "$HTML" | grep -q "должны быть выставлены cookie"; then
            COOKIES=$(extract_section_pairs "$HTML" cookie)
            CS=$(build_cookie_string "$COOKIES")
            HTML=$(curl -s -b "$COOKIE; $CS" "$BASE$LINK")
        else
            PARAMS=$(extract_section_pairs "$HTML" params)
            PARAMS_ENC=$(echo "$PARAMS" | awk -F'\t' '{printf "%s=%s&", $1, $2}' | sed 's/&$//')
            HTML=$(curl -s -b "$COOKIE" "$BASE$LINK?$PARAMS_ENC")
        fi

    elif echo "$HTML" | grep -q "Отправьте GET-запрос"; then
        # --- Тип 2: GET по <code> ---
        PATH_=$(parse_action_url "$HTML")
        COOKIES=$(extract_section_pairs "$HTML" cookie)
        CS=$(build_cookie_string "$COOKIES")
        HEADERS=$(extract_section_pairs "$HTML" headers)
        PARAMS=$(extract_section_pairs "$HTML" params)
        HDR_ARGS=$(echo "$HEADERS" | build_header_args)
        PARAMS_ENC=$(echo "$PARAMS" | awk -F'\t' '{printf "%s=%s&", $1, $2}' | sed 's/&$//')

        # shellcheck disable=SC2086
        HTML=$(curl -s -b "$COOKIE; $CS" $HDR_ARGS "$BASE$PATH_?$PARAMS_ENC")

    elif echo "$HTML" | grep -q "Отправьте POST-запрос"; then
        # --- Тип 3: POST ---
        PATH_=$(parse_action_url "$HTML")
        COOKIES=$(extract_section_pairs "$HTML" cookie)
        CS=$(build_cookie_string "$COOKIES")
        HEADERS=$(extract_section_pairs "$HTML" headers)
        PARAMS=$(extract_section_pairs "$HTML" params)
        DATA=$(extract_section_pairs "$HTML" data)
        HDR_ARGS=$(echo "$HEADERS" | build_header_args)
        DATA_ARGS=$(echo "$DATA" | build_data_args)
        PARAMS_ENC=$(echo "$PARAMS" | awk -F'\t' '{printf "%s=%s&", $1, $2}' | sed 's/&$//')

        # shellcheck disable=SC2086
        HTML=$(curl -s -b "$COOKIE; $CS" $HDR_ARGS $DATA_ARGS "$BASE$PATH_?$PARAMS_ENC")

    elif echo "$HTML" | grep -q "Загрузите файлы"; then
        # --- Тип 4: Загрузка файлов (multipart) ---
        PATH_=$(parse_action_url "$HTML")
        # Извлекаем Имя/Содержимое — они во ВСЕХ таблицах (только одна таблица тут)
        PAIRS=$(parse_table_pairs "$HTML")

        # Формируем -F "name=value;filename=..." для каждого файла
        FILES_ARGS=""
        while IFS= read -r line; do
            [ -z "$line" ] && continue
            # разбиваем на key (имя файла) и value (содержимое)
            FILENAME=$(echo "$line" | sed -n '1p')
            # содержимое — следующая строка
            :
        done < /dev/null

        # Проще: вытаскиваем пары через Python, формируем файлы во временной папке
        python3 - "$HTML" <<'EOF' > /tmp/upload_files.txt
import sys, re
html = sys.argv[1]
for m in re.finditer(r"<table[^>]*>(.*?)</table>", html, re.S):
    cells = re.findall(r"<td><code>([^<]+)</code></td>", m.group(1), re.S)
    pairs = [(cells[i], cells[i+1]) for i in range(0, len(cells)-1, 2)]
    for filename, content in pairs:
        if "." in filename:
            # сохраняем содержимое во временный файл
            with open(f"/tmp/{filename}", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"{filename}")
EOF

        # Формируем -F для curl
        F_ARGS=""
        while IFS= read -r fname; do
            [ -z "$fname" ] && continue
            F_ARGS="$F_ARGS -F file=@/tmp/$fname;filename=$fname"
        done < /tmp/upload_files.txt

        # shellcheck disable=SC2086
        HTML=$(curl -s -b "$COOKIE" $F_ARGS "$BASE$PATH_")

    else
        echo "Неизвестный тип шага:"
        echo "$HTML"
        break
    fi

    # Перезаписываем текущий URL: HTML обрабатывается на следующей итерации
    # (в этой версии логика "state-less" — каждый раз парсим HTML)
    # Поэтому нужно сохранить HTML в переменную и обработать её в начале следующей итерации
    # Для простоты делаем это через временный файл
    echo "$HTML" > /tmp/current_html.txt
    current_path="__HTML_ALREADY_FETCHED__"
done

echo "Итераций: $i"
echo "Токен: $SECRET"