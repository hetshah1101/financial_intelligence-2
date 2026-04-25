from datetime import datetime


def fmt_inr(val: float, compact: bool = False) -> str:
    """Format a number as Indian Rupees."""
    if compact:
        sign = "−" if val < 0 else ""
        absval = abs(val)
        if absval >= 1_00_000:
            return f"{sign}₹{absval / 1_00_000:.1f}L"
        elif absval >= 1_000:
            return f"{sign}₹{absval / 1_000:.1f}K"
        return f"{sign}₹{absval:.0f}"
    neg = val < 0
    s = f"{abs(val):.0f}"
    if len(s) > 3:
        last3, rest = s[-3:], s[:-3]
        parts = []
        while len(rest) > 2:
            parts.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.append(rest)
        s = ",".join(reversed(parts)) + "," + last3
    return f"{chr(8722) if neg else ''}₹{s}"


def fmt_delta(val: float) -> tuple:
    """Return (label, color) for a percentage delta."""
    if val > 0:
        return f"▲ +{val:.1f}%", "#e05252"
    elif val < 0:
        return f"▼ {val:.1f}%", "#4caf7d"
    return "─ 0%", "#888780"


def fmt_pct(val: float) -> str:
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.1f}%"


def fmt_month(ym: str) -> str:
    """Convert 'YYYY-MM' -> \"Jan'25\"."""
    try:
        dt = datetime.strptime(ym, "%Y-%m")
        return dt.strftime("%b'%y")
    except Exception:
        return ym


def fmt_month_axis(months: list) -> list:
    """Convert a list of YYYY-MM strings for chart axis labels."""
    return [fmt_month(m) for m in months]
