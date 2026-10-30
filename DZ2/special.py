def handle_multiply(qname: str):
    """2.22.multiply.test.com -> 127.0.0.44"""
    if ".multiply." not in qname.lower():
        return None

    prefix = qname.lower().split(".multiply.")[0]
    try:
        numbers = [int(x) for x in prefix.split(".")]
        product = 1
        for n in numbers:
            product *= n
        return f"127.0.0.{product % 256}"
    except ValueError:
        return None
