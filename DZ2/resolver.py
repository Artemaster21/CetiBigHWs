import socket
import random
import struct
import dns_protocol

ROOT_SERVERS = ["198.41.0.4", "199.9.14.201", "192.33.4.12", "199.7.91.13"]


def send_udp(server_ip, query):
    """Отправляет UDP-запрос. Возвращает сырые байты ответа или None."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2.0)
        s.sendto(query, (server_ip, 53))
        data, _ = s.recvfrom(4096)
        s.close()
        return data
    except Exception:
        return None


def send_tcp(server_ip, query):
    """Отправляет TCP-запрос. DNS по TCP требует 2-байтовый префикс длины."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((server_ip, 53))
        # Префикс длины (2 байта, big-endian)
        msg = struct.pack("!H", len(query)) + query
        s.sendall(msg)

        # Читаем 2 байта длины ответа
        len_data = b""
        while len(len_data) < 2:
            chunk = s.recv(2 - len(len_data))
            if not chunk:
                s.close()
                return None
            len_data += chunk
        resp_len = struct.unpack("!H", len_data)[0]

        # Читаем сам ответ
        resp_data = b""
        while len(resp_data) < resp_len:
            chunk = s.recv(resp_len - len(resp_data))
            if not chunk:
                break
            resp_data += chunk
        s.close()
        return resp_data
    except Exception:
        return None


def query_server(server_ip, qname, qtype):
    """Делает запрос к серверу. Если UDP обрезан, повторяет по TCP."""
    tx_id = random.randint(0, 65535)
    query = dns_protocol.build_query(tx_id, qname, qtype)

    # 1. Пробуем UDP
    data = send_udp(server_ip, query)
    if data:
        msg = dns_protocol.parse_message(data)
        if msg:
            # Проверяем TC-флаг (бит 9 в Flags)
            if msg["flags"] & 0x0200:
                print(f"  [TC] Пакет обрезан от {server_ip}, перезапрос по TCP...")
                data = send_tcp(server_ip, query)
                if data:
                    return dns_protocol.parse_message(data)
            return msg

    # Если UDP не сработал (таймаут), тоже пробуем TCP
    data = send_tcp(server_ip, query)
    if data:
        return dns_protocol.parse_message(data)

    return None


def resolve(qname: str, qtype: int, depth=0):
    """
    Возвращает (ip_str, ttl) или (None, 0).
    """
    if depth > 20:
        return None, 0

    current_servers = ROOT_SERVERS

    for step in range(15):
        next_servers = []

        for server_ip in current_servers:
            msg = query_server(server_ip, qname, qtype)
            if not msg:
                continue

            # 1. Если в ответе есть нужный тип - возвращаем!
            for ans in msg["answers"]:
                if ans["type"] == qtype:
                    if qtype in (dns_protocol.QTYPE_A, dns_protocol.QTYPE_AAAA):
                        return ans["rdata"], ans["ttl"]

                # Если пришел CNAME, идем по нему
                if ans["type"] == dns_protocol.QTYPE_CNAME:
                    return resolve(ans["rdata"], qtype, depth + 1)

            # 2. Если есть авторитетные NS - берем их IP из Additional
            for auth in msg["authority"]:
                if auth["type"] == dns_protocol.QTYPE_NS:
                    ns_name = auth["rdata"]
                    # Ищем IP этого NS в additional
                    for add in msg["additional"]:
                        if add["name"].lower() == ns_name.lower() and add["type"] in (dns_protocol.QTYPE_A,
                                                                                      dns_protocol.QTYPE_AAAA):
                            next_servers.append(add["rdata"])

            # Если нашли серверы для следующего шага — переходим к ним
            if next_servers:
                break

        if not next_servers:
            # Если не нашли NS в additional, пробуем разрешить NS-сервер отдельно
            # (на случай, если сервер не прислал IP)
            for auth in msg["authority"]:
                if auth["type"] == dns_protocol.QTYPE_NS:
                    ns_ip, _ = resolve(auth["rdata"], dns_protocol.QTYPE_A, depth + 1)
                    if ns_ip:
                        next_servers.append(ns_ip)

        if not next_servers:
            break

        current_servers = next_servers

    return None, 0
