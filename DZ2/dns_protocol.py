import struct

# Константы типов
QTYPE_A = 1
QTYPE_NS = 2
QTYPE_CNAME = 5
QTYPE_MX = 15
QTYPE_AAAA = 28

QCLASS_IN = 1


def parse_name(data: bytes, offset: int):
    """
    Читает доменное имя начиная с offset.
    Поддерживает сжатие (name compression).
    Возвращает (name_str, new_offset).
    """
    labels = []
    original_offset = offset
    jumped = False
    new_offset = offset

    while True:
        if offset >= len(data):
            return "", original_offset + 1
        length = data[offset]

        if length == 0:
            if not jumped:
                new_offset = offset + 1
            break

        if (length & 0xC0) == 0xC0:
            if offset + 1 >= len(data):
                return "", original_offset + 1
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if not jumped:
                new_offset = offset + 2
                jumped = True
            offset = pointer
            continue

        label = data[offset + 1: offset + 1 + length].decode('ascii', errors='replace')
        labels.append(label)
        offset += 1 + length

    return ".".join(labels), new_offset


def encode_name(name: str) -> bytes:
    """Превращает строку 'example.com' в байты DNS-имени."""
    parts = name.rstrip('.').split('.')
    result = b""
    for part in parts:
        if part:
            result += struct.pack("!B", len(part)) + part.encode('ascii')
    result += b"\x00"
    return result


def parse_message(data: bytes):
    """Парсит весь DNS-пакет. Возвращает dict."""
    if len(data) < 12:
        return None

    tx_id, flags, qdcount, ancount, nscount, arcount = struct.unpack("!HHHHHH", data[:12])

    msg = {
        "id": tx_id,
        "flags": flags,
        "qdcount": qdcount,
        "ancount": ancount,
        "nscount": nscount,
        "arcount": arcount,
        "questions": [],
        "answers": [],
        "authority": [],
        "additional": []
    }

    offset = 12
    # Вопросы
    for _ in range(qdcount):
        qname, offset = parse_name(data, offset)
        if offset + 4 > len(data):
            break
        qtype, qclass = struct.unpack("!HH", data[offset:offset + 4])
        offset += 4
        msg["questions"].append({"qname": qname, "qtype": qtype, "qclass": qclass})

    # Функция разбора RR (Resource Record)
    def parse_rr(offset):
        name, offset = parse_name(data, offset)
        if offset + 10 > len(data):
            return None, offset
        rtype, rclass, ttl, rdlength = struct.unpack("!HHIH", data[offset:offset + 10])
        offset += 10
        rdata_start = offset
        rdata = data[rdata_start:rdata_start + rdlength]
        offset += rdlength

        parsed_data = rdata
        if rtype == QTYPE_A and rdlength == 4:
            parsed_data = ".".join(str(b) for b in rdata)
        elif rtype == QTYPE_AAAA and rdlength == 16:
            import socket
            parsed_data = socket.inet_ntop(socket.AF_INET6, rdata)
        elif rtype in (QTYPE_NS, QTYPE_CNAME):
            parsed_data, _ = parse_name(data, rdata_start)
        elif rtype == QTYPE_MX and rdlength > 2:
            pref = struct.unpack("!H", rdata[:2])[0]
            exch, _ = parse_name(data, rdata_start + 2)
            parsed_data = (pref, exch)

        return {
            "name": name,
            "type": rtype,
            "class": rclass,
            "ttl": ttl,
            "rdata": parsed_data
        }, offset

    # Ответы
    for _ in range(ancount):
        rr, offset = parse_rr(offset)
        if rr: msg["answers"].append(rr)
    # Авторитетные
    for _ in range(nscount):
        rr, offset = parse_rr(offset)
        if rr: msg["authority"].append(rr)
    # Дополнительные
    for _ in range(arcount):
        rr, offset = parse_rr(offset)
        if rr: msg["additional"].append(rr)

    return msg


def build_query(tx_id: int, qname: str, qtype: int):
    """Собирает DNS-запрос для отправки корневому серверу."""
    header = struct.pack("!HHHHHH", tx_id, 0x0100, 1, 0, 0, 0)  # RD=1
    qname_bytes = encode_name(qname)
    question = qname_bytes + struct.pack("!HH", qtype, QCLASS_IN)
    return header + question


def build_response(tx_id: int, questions: list, answers: list, rcode=0):
    """
    Собирает ответ для клиента.
    answers - список dict: {"qtype": int, "ip": str} или {"qtype": int, "name": str}
    """
    flags = 0x8180 | rcode  # QR=1, RD=1, RA=1
    qdcount = len(questions)
    ancount = len(answers)

    header = struct.pack("!HHHHHH", tx_id, flags, qdcount, ancount, 0, 0)

    q_bytes = b""
    for q in questions:
        q_bytes += encode_name(q['qname'])
        q_bytes += struct.pack("!HH", q['qtype'], QCLASS_IN)

    a_bytes = b""
    for ans in answers:
        a_bytes += struct.pack("!H", 0xC00C)  # Указатель на имя в вопросе
        rtype = ans['qtype']
        rclass = QCLASS_IN
        ttl = 60

        if rtype == QTYPE_A:
            import socket
            rdata = socket.inet_aton(ans['ip'])
        elif rtype == QTYPE_AAAA:
            import socket
            rdata = socket.inet_pton(socket.AF_INET6, ans['ip'])
        else:
            rdata = b""

        a_bytes += struct.pack("!HHIH", rtype, rclass, ttl, len(rdata))
        a_bytes += rdata

    return header + q_bytes + a_bytes
