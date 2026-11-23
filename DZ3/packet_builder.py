import struct
import socket

def checksum(data):
    if len(data) % 2:
        data += b'\x00'
    s = 0
    for i in range(0, len(data), 2):
        s += (data[i] << 8) + data[i + 1]
    s = (s >> 16) + (s & 0xffff)
    s += (s >> 16)
    return (~s) & 0xffff

def build_tcp_syn(src_ip, dst_ip, src_port, dst_port, seq=1000):
    offset_flags = (5 << 12) | 0x02  # SYN
    tcp = struct.pack('!HHLLHHHH', src_port, dst_port, seq, 0,
                      offset_flags, 5840, 0, 0)
    pseudo = struct.pack('!4s4sBBH',
                         socket.inet_aton(src_ip),
                         socket.inet_aton(dst_ip),
                         0, socket.IPPROTO_TCP, len(tcp))
    chk = checksum(pseudo + tcp)
    tcp = tcp[:16] + struct.pack('!H', chk) + tcp[18:]
    return tcp

def build_tcp_rst(src_ip, dst_ip, src_port, dst_port, seq, ack):
    offset_flags = (5 << 12) | 0x04  # RST
    tcp = struct.pack('!HHLLHHHH', src_port, dst_port, seq, ack,
                      offset_flags, 0, 0, 0)
    pseudo = struct.pack('!4s4sBBH',
                         socket.inet_aton(src_ip),
                         socket.inet_aton(dst_ip),
                         0, socket.IPPROTO_TCP, len(tcp))
    chk = checksum(pseudo + tcp)
    tcp = tcp[:16] + struct.pack('!H', chk) + tcp[18:]
    return tcp
