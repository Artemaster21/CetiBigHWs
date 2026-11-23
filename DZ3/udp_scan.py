import socket
import struct
import time

def scan_udp(target_ip, ports, timeout, on_result):
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for port in ports:
        try:
            send_sock.sendto(b'\x00', (target_ip, port))
        except OSError:
            pass
    send_sock.close()

    icmp_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    icmp_sock.setblocking(False)

    closed_ports = set()
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            data, _ = icmp_sock.recvfrom(4096)
        except BlockingIOError:
            time.sleep(0.001)
            continue

        if len(data) < 28:
            continue

        icmp_type = data[0]
        icmp_code = data[1]
        if icmp_type == 3 and icmp_code == 3:
            # Извлекаем исходный UDP-заголовок из полезной нагрузки ICMP (упрощённо: IP-заголовок 20 байт)
            orig_udp = data[28:]
            if len(orig_udp) >= 4:
                dst_port = struct.unpack('!H', orig_udp[2:4])[0]
                closed_ports.add(dst_port)

    icmp_sock.close()

    for port in ports:
        if port in closed_ports:
            on_result(port, 'closed', 0)
        else:
            on_result(port, 'open', 0)
