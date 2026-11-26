import json
import os
import subprocess
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
CLI = os.path.join(ROOT, "cleaner", "cleaner.py")
SAMPLES = os.path.join(ROOT, "samples")
INPUT = os.path.join(SAMPLES, "input_messy.csv")


def run(tmp_path, *extra):
    out = tmp_path / "out.csv"
    rep = tmp_path / "report.json"
    cmd = [sys.executable, CLI, INPUT, "-o", str(out), "--report", str(rep), *extra]
    p = subprocess.run(cmd, capture_output=True, text=True)
    report = json.loads(rep.read_text(encoding="utf-8")) if rep.exists() else None
    return p, out, report


def test_success_non_strict(tmp_path):
    p, out, report = run(tmp_path,
        "--fill", "age:mean",
        "--dedup-keys", "id",
        "--validate", r"email:regex:^[^@]+@[^@]+\.[^@]+$",
        "--validate", "joined:date:%Y-%m-%d")
    assert p.returncode == 0, p.stderr
    assert out.exists()
    assert report["rows_in"] == 5
    assert report["rows_out"] == 4
    assert len(report["violations"]) >= 2


def test_strict_exit_3(tmp_path):
    p, _, report = run(tmp_path, "--strict",
        "--validate", "joined:date:%Y-%m-%d")
    assert p.returncode == 3
    assert report["violations"]


def test_missing_input_exit_2(tmp_path):
    out = tmp_path / "o.csv"
    cmd = [sys.executable, CLI, str(tmp_path / "nope.csv"), "-o", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    assert p.returncode == 2


def test_bad_rule_exit_3(tmp_path):
    p, _, _ = run(tmp_path, "--fill", "age:unknown")
    assert p.returncode == 3