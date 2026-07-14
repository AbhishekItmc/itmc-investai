"""Number/currency formatting helpers (Indian conventions)."""
from __future__ import annotations

import math


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not (isinstance(x, float) and math.isnan(x))


def inr(value, decimals: int = 2, symbol: str = "₹") -> str:
    """Format with Indian digit grouping: 12,34,567.89."""
    if not _is_num(value):
        return "—"
    neg = value < 0
    value = abs(value)
    whole, frac = divmod(round(value, decimals), 1)
    s = f"{int(whole)}"
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    if decimals:
        s += f"{frac:.{decimals}f}"[1:]
    return f"{'-' if neg else ''}{symbol}{s}"


def compact_inr(value) -> str:
    """1.5 Cr / 23.4 L / 12 K style."""
    if not _is_num(value):
        return "—"
    a = abs(value)
    sign = "-" if value < 0 else ""
    if a >= 1e7:
        return f"{sign}₹{a / 1e7:,.2f} Cr"
    if a >= 1e5:
        return f"{sign}₹{a / 1e5:,.2f} L"
    if a >= 1e3:
        return f"{sign}₹{a / 1e3:,.1f} K"
    return f"{sign}₹{a:,.2f}"


def pct(value, decimals: int = 2) -> str:
    if not _is_num(value):
        return "—"
    return f"{value:+.{decimals}f}%"


def num(value, decimals: int = 2) -> str:
    if not _is_num(value):
        return "—"
    return f"{value:,.{decimals}f}"
