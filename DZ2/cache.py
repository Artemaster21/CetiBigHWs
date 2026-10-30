import time
import json
import os

class DNSCache:
    def __init__(self, filename="dns_cache.json"):
        self.filename = filename
        self.data = {} # { "qname:qtype": (rdata, expire_time) }
        self.load()

    def get(self, qname: str, qtype: int):
        key = f"{qname.lower()}:{qtype}"
        if key in self.data:
            rdata, expire = self.data[key]
            if time.time() < expire:
                return rdata
            else:
                del self.data[key]
        return None

    def set(self, qname: str, qtype: int, rdata, ttl: int):
        key = f"{qname.lower()}:{qtype}"
        self.data[key] = (rdata, time.time() + ttl)

    def save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f)
        except Exception:
            pass

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}
