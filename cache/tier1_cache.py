import time

# In-memory store
_cache = {}

DEFAULT_TTL = 300  # seconds (5 minutes)


def get_l1(question: str):
    entry = _cache.get(question)

    if not entry:
        return None

    sql, df, expiry = entry

    if time.time() > expiry:
        del _cache[question]
        return None

    return sql, df


def set_l1(question: str, sql: str, df, ttl=DEFAULT_TTL):
    expiry = time.time() + ttl
    _cache[question] = (sql, df, expiry)


def clear_l1():
    _cache.clear()
