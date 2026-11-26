"""清洗规则：缺失、重复、非法值。"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Callable

MISSING_TOKENS = {"", "na", "n/a", "null", "none", "nan", "-", "?"}

_REGEX_CACHE: dict[str, re.Pattern] = {}


def is_missing(v: str | None) -> bool:
    return v is None or v.strip().lower() in MISSING_TOKENS


# ---------- 缺失值 ----------
def fill_missing(rows: list[dict], column: str, strategy: str = "drop",
                 value: str | None = None) -> list[dict]:
    if strategy == "drop":
        return [r for r in rows if not is_missing(r.get(column))]

    if strategy == "constant":
        for r in rows:
            if is_missing(r.get(column)):
                r[column] = "" if value is None else value
        return rows

    if strategy == "mean":
        nums: list[float] = []
        for r in rows:
            v = r.get(column)
            if is_missing(v):
                continue
            try:
                nums.append(float(v))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                raise ValueError(
                    f"column '{column}' 含非数值 {v!r}，不能用 mean 填充"
                )
        m = sum(nums) / len(nums) if nums else 0.0
        filled = f"{m:.6g}"
        for r in rows:
            if is_missing(r.get(column)):
                r[column] = filled
        return rows

    raise ValueError(f"unknown fill strategy: {strategy}")


# ---------- 重复值 ----------
def _norm(v):
    return v.strip().lower() if isinstance(v, str) else v


def dedup(rows: list[dict], keys: list[str] | None = None,
          normalize: bool = False) -> list[dict]:
    seen: set = set()
    out: list[dict] = []
    for r in rows:
        if keys:
            if any(k not in r for k in keys):
                raise KeyError(f"dedup key not in row: {keys}")
            k = tuple(r.get(c) for c in keys)
        else:
            k = tuple(sorted(r.items()))
        if normalize:
            k = tuple(_norm(x) for x in k)
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


# ---------- 非法值 ----------
def _checker(rule: dict) -> Callable[[str], bool]:
    t = rule["type"]
    if t == "int":
        return lambda v: bool(re.fullmatch(r"-?\d+", v.strip()))
    if t == "float":
        def _f(v):
            try:
                float(v.strip())
                return True
            except ValueError:
                return False
        return _f
    if t == "date":
        fmt = rule.get("fmt", "%Y-%m-%d")
        def _d(v):
            try:
                datetime.strptime(v.strip(), fmt)
                return True
            except ValueError:
                return False
        return _d
    if t == "regex":
        pat = rule["pattern"]
        if pat not in _REGEX_CACHE:
            _REGEX_CACHE[pat] = re.compile(pat)
        rx = _REGEX_CACHE[pat]
        return lambda v: bool(rx.fullmatch(v))
    if t == "enum":
        allowed = set(rule["allowed"])
        return lambda v: v in allowed
    raise ValueError(f"unknown rule type: {t}")


def validate(rows: list[dict], column: str, rule: dict) -> list[tuple[int, str, str]]:
    """返回 [(row_index, column, value), ...]，空串视为缺失不报非法。"""
    check = _checker(rule)
    bad: list[tuple[int, str, str]] = []
    for i, r in enumerate(rows):
        v = r.get(column, "")
        if is_missing(v):
            continue
        if not check(v):
            bad.append((i, column, v))
    return bad