def format_result(proto, port, elapsed_ms=None, verbose=False, protocol=None, guess=False):
    parts = [proto.upper(), str(port)]
    if verbose:
        parts.append(f'[{elapsed_ms:.2f}ms]' if elapsed_ms is not None else '[-]')
    if guess:
        parts.append(protocol if protocol else '-')
    return ' '.join(parts)
