import socket
import struct

def detect_http(ip, port, timeout=1.0):
    try:
        with socket.create_connection((ip, port), timeout=timeout) as s:
            s.sendall(b'HEAD / HTTP/1.0\r\n\r\n')
            data = s.recv(1024)
            return b'HTTP/' in data
    except Exception:
        return False

def detect_echo(ip, port, timeout=1.0):
    try:
        with socket.create_connection((ip, port), timeout=timeout) as s:
            test = b'PORTSCAN_ECHO_TEST'
            s.sendall(test)
            data = s.recv(1024)
            return data == test
    except Exception:
        return False

def detect_dns(ip, port=53, timeout=1.0):
    # Вручную собираем DNS-запрос A-записи для example.com
    txid = b'\xab\xcd'
    flags = b'\x01\x00'
    counts = b'\x00\x01\x00\x00\x00\x00\x00\x00'
    qname = b'\x07example\x03com\x00'
    qtype_qclass = b'\x00\x01\x00\x01'
    query = txid + flags + counts + qname + qtype_qclass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(timeout)
            s.sendto(query, (ip, port))
            data, _ = s.recvfrom(1024)
            return len(data) > 12 and data[:2] == txid
    except Exception:
        return False
