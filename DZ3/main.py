import socket
from args_parser import parse_args
from tcp_syn import scan_tcp_syn
from udp_scan import scan_udp
from protocol_detect import detect_http, detect_echo, detect_dns
from output import format_result

def get_src_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '0.0.0.0'

def main():
    args = parse_args()
    src_ip = get_src_ip()
    # '127.0.0.1' , get_src_ip()
    results = []

    for proto, ports in args.scan_specs:
        if proto == 'tcp':
            def on_tcp(port, status, elapsed):
                if status == 'open':
                    results.append(('tcp', port, elapsed, None))
            scan_tcp_syn(args.target, ports, src_ip, args.timeout, on_tcp)
        elif proto == 'udp':
            def on_udp(port, status, elapsed):
                if status == 'open':
                    results.append(('udp', port, None, None))
            scan_udp(args.target, ports, args.timeout, on_udp)

    if args.guess:
        for i, (proto, port, elapsed, _) in enumerate(results):
            detected = None
            if proto == 'tcp':
                if detect_http(args.target, port):
                    detected = 'HTTP'
                elif detect_echo(args.target, port):
                    detected = 'ECHO'
            elif proto == 'udp':
                if detect_dns(args.target, port):
                    detected = 'DNS'
            results[i] = (proto, port, elapsed, detected)

    for proto, port, elapsed, detected in results:
        print(format_result(proto, port, elapsed, args.verbose, detected, args.guess))

if __name__ == '__main__':
    main()
