#!/usr/bin/env python3
"""命令行数据清洗程序。

退出码:
  0 成功
  2 输入错误 (文件不存在/无法解码)
  3 规则错误, 或 --strict 下发现非法值
  4 输出写入失败
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from io_utils import read_csv_robust, write_csv
from rules import dedup, fill_missing, validate

EXIT_OK, EXIT_INPUT, EXIT_RULE, EXIT_OUTPUT = 0, 2, 3, 4


def _write_report(path: str | None, report: dict) -> None:
    if not path:
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def _parse_rule(spec: str) -> tuple[str, dict]:
    parts = spec.split(":")
    col, typ, *extra = parts
    rule: dict = {"type": typ}
    if typ == "regex":
        rule["pattern"] = extra[0] if extra else ".*"
    elif typ == "enum":
        rule["allowed"] = extra
    elif typ == "date" and extra:
        rule["fmt"] = extra[0]
    return col, rule


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cleaner", description="命令行数据清洗")
    p.add_argument("input")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--encoding", default=None, help="强制指定输入编码")
    p.add_argument("--dedup-keys", default=None, help="逗号分隔的去重键列名")
    p.add_argument("--dedup-normalize", action="store_true",
                   help="去重前做 strip+lower 归一化")
    p.add_argument("--fill", action="append", default=[], metavar="COL:STRATEGY[:VALUE]")
    p.add_argument("--validate", action="append", default=[],
                   metavar="COL:TYPE[:EXTRA]", help="type ∈ int|float|date|regex|enum")
    p.add_argument("--report", default=None, help="JSON 清洗报告输出路径")
    p.add_argument("--strict", action="store_true", help="发现非法值即失败")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        rows, used_enc = read_csv_robust(args.input, args.encoding)
    except FileNotFoundError:
        logging.error("input not found: %s", args.input)
        return EXIT_INPUT
    except Exception as e:  # noqa: BLE001
        logging.error("read failed: %s", e)
        return EXIT_INPUT

    report: dict = {"encoding": used_enc, "rows_in": len(rows),
                    "input": args.input, "output": args.output}

    try:
        for spec in args.fill:
            col, strategy, *rest = spec.split(":")
            rows = fill_missing(rows, col, strategy, rest[0] if rest else None)
            logging.info("filled column %s (%s)", col, strategy)

        if args.dedup_keys:
            keys = [k for k in args.dedup_keys.split(",") if k]
            before = len(rows)
            rows = dedup(rows, keys, normalize=args.dedup_normalize)
            logging.info("dedup by %s: %d -> %d", keys, before, len(rows))
            report["dedup_removed"] = before - len(rows)

        violations: list = []
        for spec in args.validate:
            col, rule = _parse_rule(spec)
            violations += validate(rows, col, rule)
        report["violations"] = violations
        if violations:
            logging.warning("%d violation(s)", len(violations))
            if args.strict:
                _write_report(args.report, report)
                return EXIT_RULE

        report["rows_out"] = len(rows)

        try:
            write_csv(args.output, rows)
        except OSError as e:
            logging.error("write failed: %s", e)
            return EXIT_OUTPUT

        _write_report(args.report, report)
        logging.info("done: %d -> %d rows, encoding=%s",
                     report["rows_in"], report["rows_out"], used_enc)
        return EXIT_OK

    except (ValueError, KeyError) as e:
        logging.error("rule error: %s", e)
        _write_report(args.report, report)
        return EXIT_RULE


if __name__ == "__main__":
    sys.exit(main())