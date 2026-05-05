import math


def stats(values):
    clean = sorted(float(v) for v in values if v is not None)
    if not clean:
        return {}
    n = len(clean)
    mean = sum(clean) / n
    median = clean[n // 2] if n % 2 else (clean[n // 2 - 1] + clean[n // 2]) / 2.0
    variance = sum((x - mean) ** 2 for x in clean) / n
    return {
        "count": n,
        "min": clean[0],
        "max": clean[-1],
        "mean": mean,
        "median": median,
        "stddev": math.sqrt(variance),
    }


def format_tr(value):
    if value is None:
        return ""
    text = ("%.2f" % float(value)).rstrip("0").rstrip(".")
    left, _, right = text.partition(".")
    groups = []
    while left:
        groups.insert(0, left[-3:])
        left = left[:-3]
    return ".".join(groups) + ("," + right if right else "")


def manual_breaks(text):
    breaks = []
    for item in str(text or "").replace(";", ",").split(","):
        item = item.strip()
        if item:
            breaks.append(float(item.replace(".", "").replace(",", ".")))
    return sorted(breaks)
