import socket
import struct
import time
import select
from packet_builder import build_tcp_syn, build_tcp_rst

def scan_tcp_syn(target_ip, ports, src_ip, timeout, on_result):
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
    sock.setblocking(False)

    pending = {}      # src_port -> (dst_port, send_time)
    src_base = 40000

    for i, port in enumerate(ports):
        sp = src_base + (i % 10000)
        pkt = build_tcp_syn(src_ip, target_ip, sp, port)
        try:
            sock.sendto(pkt, (target_ip, 0))
            pending[sp] = (port, time.time())
        except OSError:
            continue

    deadline = time.time() + timeout

    while pending and time.time() < deadline:
        remain = max(0, deadline - time.time())
        rlist, _, _ = select.select([sock], [], [], remain)
        if not rlist:
            break

        try:
            data, _ = sock.recvfrom(4096)
        except BlockingIOError:
            continue

        # В Linux необработанный сокет с IPPROTO_TCP получает IP-заголовок + TCP-заголовок
        ip_hlen = (data[0] & 0x0f) * 4
        tcp = data[ip_hlen:]
        if len(tcp) < 20:
            continue

        r_src, r_dst, r_seq, r_ack = struct.unpack('!HHLL', tcp[:12])
        flags = struct.unpack('!H', tcp[12:14])[0] & 0x3f

        if r_dst not in pending:
            continue

        port, st = pending.pop(r_dst)
        elapsed = (time.time() - st) * 1000

        if flags == 0x12:  # SYN-ACK
            rst = build_tcp_rst(src_ip, target_ip, r_dst, port,
                                seq=r_ack, ack=r_seq + 1)
            try:
                sock.sendto(rst, (target_ip, 0))
            except OSError:
                pass
            on_result(port, 'open', elapsed)
        elif flags == 0x14:  # RST-ACK
            on_result(port, 'closed', elapsed)

    # Таймаут
    for sp, (port, _) in pending.items():
        on_result(port, 'timeout', timeout * 1000)
        # print(f"Sent SYN from {sp} to {port}")

    sock.close()
