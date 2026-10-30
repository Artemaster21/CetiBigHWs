import socket
import struct
import threading
import dns_protocol
import special
import resolver
from cache import DNSCache

HOST = '0.0.0.0'
PORT = 53
cache = DNSCache()


def handle_request(data: bytes, client_addr=None, tcp_conn=None):
    """Универсальная обработка запроса."""
    # Парсим
    msg = dns_protocol.parse_message(data)
    if not msg or not msg["questions"]:
        return b""

    q = msg["questions"][0]
    qname = q["qname"]
    qtype = q["qtype"]
    tx_id = msg["id"]

    print(f"[QUERY] {qname} (type={qtype})")

    answers = []
    rcode = 0

    # 1. Multiply
    ip = special.handle_multiply(qname)
    if ip:
        print(f"  -> MULTIPLY: {ip}")
        answers.append({"qtype": dns_protocol.QTYPE_A, "ip": ip})

    # 2. Cache
    if not answers:
        cached = cache.get(qname, qtype)
        if cached:
            print(f"  -> CACHE HIT: {cached}")
            answers.append({"qtype": qtype, "ip": cached})

    # 3. Resolve
    if not answers:
        print(f"  -> RESOLVING...")
        res_ip, ttl = resolver.resolve(qname, qtype)
        if res_ip:
            cache.set(qname, qtype, res_ip, ttl)
            answers.append({"qtype": qtype, "ip": res_ip})
        else:
            rcode = 3  # NXDOMAIN

    response = dns_protocol.build_response(tx_id, msg["questions"], answers, rcode)
    return response


def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"UDP server started on {HOST}:{PORT}")
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            # Многопоточность для UDP
            threading.Thread(target=lambda: sock.sendto(handle_request(data), addr)).start()
        except ConnectionResetError:
            # Windows бросает эту ошибку, когда клиент закрыл сокет
            # Игнорируем и продолжаем слушать
            pass
        except Exception as e:
            print(f"UDP error: {e}")

def tcp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))
    sock.listen(5)
    print(f"TCP server started on {HOST}:{PORT}")
    while True:
        conn, addr = sock.accept()
        threading.Thread(target=handle_tcp_client, args=(conn,)).start()


def handle_tcp_client(conn):
    try:
        # Читаем 2 байта длины
        length_data = conn.recv(2)
        if not length_data:
            return
        length = struct.unpack("!H", length_data)[0]

        # Читаем сам пакет
        data = b""
        while len(data) < length:
            chunk = conn.recv(length - len(data))
            if not chunk:
                break
            data += chunk

        response = handle_request(data)

        # Отправляем с префиксом длины
        conn.sendall(struct.pack("!H", len(response)) + response)
    except Exception as e:
        print(f"TCP error: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    # Запускаем UDP и TCP в разных потоках
    threading.Thread(target=udp_server, daemon=True).start()
    threading.Thread(target=tcp_server, daemon=True).start()

    print("DNS Server is running. Press Ctrl+F2(Fn + Esc mod) to stop.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        cache.save()  # Сохраняем кэш
        print("\nCache saved. Bye!")
