import argparse

def parse_port_spec(spec):
    ports = set()
    for part in spec.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            ports.update(range(int(a), int(b) + 1))
        else:
            ports.add(int(part))
    return sorted(ports)

def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--timeout', type=float, default=2.0)
    p.add_argument('-j', '--num-threads', type=int, default=1)
    p.add_argument('-v', '--verbose', action='store_true')
    p.add_argument('-g', '--guess', action='store_true')
    p.add_argument('target')
    p.add_argument('specs', nargs='+')

    args = p.parse_args(argv)

    scan_specs = []
    for spec in args.specs:
        proto, _, port_part = spec.partition('/')
        proto = proto.lower()
        if proto not in ('tcp', 'udp'):
            p.error(f'неизвестный протокол: {proto}')
        ports = parse_port_spec(port_part) if port_part else list(range(1, 65536))
        scan_specs.append((proto, ports))

    args.scan_specs = scan_specs
    return args
