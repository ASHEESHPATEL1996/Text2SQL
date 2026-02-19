
_metrics = {
    "l1_hits": 0,
    "l2_hits": 0,
    "misses": 0
}


def record_l1_hit():
    _metrics["l1_hits"] += 1


def record_l2_hit():
    _metrics["l2_hits"] += 1


def record_miss():
    _metrics["misses"] += 1


def get_metrics():
    return _metrics.copy()


def reset_metrics():
    for k in _metrics:
        _metrics[k] = 0


def hit_rate():
    total = sum(_metrics.values())
    if total == 0:
        return 0.0

    hits = _metrics["l1_hits"] + _metrics["l2_hits"]
    return hits / total
