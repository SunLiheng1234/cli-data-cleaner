"""编码探测与健壮读写。"""
from __future__ import annotations

import csv
import io
from typing import Iterable

import chardet


def _looks_chinese(raw: bytes) -> bool:
    try:
        raw.decode("gb18030")
        return True
    except UnicodeDecodeError:
        return False


def detect_encoding(path: str, sample_size: int = 100_000) -> str:
    """探测文件编码，返回可用于 open() 的编码名。"""
    with open(path, "rb") as f:
        raw = f.read(sample_size)
    if not raw:
        return "utf-8"
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"

    result = chardet.detect(raw)
    enc = (result.get("encoding") or "utf-8").lower()

    # chardet 对短文件/纯 ASCII 常误判为 ascii / iso-8859-1
    if enc in ("ascii", "iso-8859-1", "latin-1"):
        try:
            raw.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            pass
        if _looks_chinese(raw):
            return "gb18030"
        return "latin-1"

    # 常见别名归一
    if enc in ("gb2312", "gbk"):
        return "gb18030"
    return enc


def read_csv_robust(path: str, encoding: str | None = None):
    """返回 (rows: list[dict], used_encoding: str)。

    先按探测/指定编码读，失败则沿回退链重试。
    """
    candidates: list[str] = []
    if encoding:
        candidates.append(encoding)
    else:
        candidates.append(detect_encoding(path))
    for fb in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        if fb not in candidates:
            candidates.append(fb)

    last_err: Exception | None = None
    for enc in candidates:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                rows = list(csv.DictReader(f))
            return rows, enc
        except UnicodeDecodeError as e:
            last_err = e
            continue
    raise last_err  # type: ignore[misc]


def write_csv(path: str, rows: Iterable[dict], fieldnames: list[str] | None = None) -> None:
    rows = list(rows)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)