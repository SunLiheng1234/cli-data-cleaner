# demo.ps1 - one-click demo for cleaner
# Usage: cd project-root ; .\demo.ps1
# If blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# This file is pure ASCII; no BOM required on Windows PowerShell 5.x.

$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot

$PY = "python"
$CLI = "cleaner/cleaner.py"
$INPUT = "samples/input_messy.csv"
$INPUT_GBK = "samples/input_messy_gbk.csv"
$INPUT_EMPTY = "samples/empty.csv"

function Show-Exit($label, $code) {
    Write-Host ("  -> {0} exit={1}" -f $label, $code) -ForegroundColor Cyan
}

function Run-Py($label, [string[]]$pyArgs) {
    Write-Host ""
    Write-Host ("=== {0} ===" -f $label) -ForegroundColor Yellow
    & $PY @pyArgs
    Show-Exit $label $LASTEXITCODE
}

Write-Host ("Project dir: {0}" -f $PWD)

# ---------- 0. prepare samples ----------
Write-Host ""
Write-Host "=== 0. prepare samples ===" -ForegroundColor Yellow

# Chinese city names built from code points so this script stays ASCII
$bj = [char]0x5317 + [char]0x4EAC   # Beijing
$sh = [char]0x4E0A + [char]0x6D77   # Shanghai
$gz = [char]0x5E7F + [char]0x5DDE   # Guangzhou
$sz = [char]0x6DF1 + [char]0x5733   # Shenzhen

$lines = @(
    "id,name,age,email,joined,city",
    "1,Alice,30,a@x.com,2020-01-01,$bj",
    "2,bob ,N/A,B@X.COM,2020-02-30,$sh",
    "2,bob ,N/A,B@X.COM,2020-02-30,$sh",
    "3,,25,not-an-email,2021-13-01,$gz",
    "4,Dan,-5,d@x.com,2019-12-31,$sz"
)
$utf8Content = ($lines -join "`r`n") + "`r`n"

[System.IO.File]::WriteAllText(
    (Join-Path $PWD $INPUT),
    $utf8Content,
    (New-Object System.Text.UTF8Encoding $false)
)
Write-Host ("  wrote {0} (UTF-8, contains CJK)" -f $INPUT)

$text = [System.IO.File]::ReadAllText((Join-Path $PWD $INPUT), [System.Text.Encoding]::UTF8)
$gbk = [System.Text.Encoding]::GetEncoding("GB18030")
[System.IO.File]::WriteAllText((Join-Path $PWD $INPUT_GBK), $text, $gbk)
Write-Host ("  wrote {0} (GB18030)" -f $INPUT_GBK)

New-Item -ItemType File -Path (Join-Path $PWD $INPUT_EMPTY) -Force | Out-Null
Write-Host ("  wrote {0} (empty)" -f $INPUT_EMPTY)

$detect = & $PY -c "import chardet;raw=open(r'$INPUT_GBK','rb').read();print(chardet.detect(raw)['encoding'])"
Write-Host ("  chardet detect {0} => {1}" -f $INPUT_GBK, $detect)

# ---------- 1. pytest ----------
Run-Py "1. pytest (expect 0)" @("-m", "pytest", "-q")

# ---------- 2. normal clean ----------
Run-Py "2. normal clean (expect 0)" @(
    $CLI, $INPUT, "-o", "out.csv",
    "--fill", "age:mean",
    "--dedup-keys", "id",
    "--validate", "email:regex:^[^@]+@[^@]+\.[^@]+$",
    "--validate", "joined:date:%Y-%m-%d",
    "--report", "report.json"
)

# ---------- 3. strict ----------
Run-Py "3. strict (expect 3)" @(
    $CLI, $INPUT, "-o", "out.csv",
    "--validate", "joined:date:%Y-%m-%d",
    "--strict"
)

# ---------- 4. GBK detect ----------
Run-Py "4. GBK detect (expect 0)" @(
    $CLI, $INPUT_GBK, "-o", "out_gbk.csv", "--report", "report_gbk.json"
)
& $PY -c "import json;d=json.load(open('report_gbk.json',encoding='utf-8'));print('  detected encoding =', d['encoding'])"

# ---------- 5. missing input ----------
Run-Py "5. missing input (expect 2)" @(
    $CLI, "samples/nope.csv", "-o", "x.csv"
)

# ---------- 6. bad rule ----------
Run-Py "6. bad rule age:unknown (expect 3)" @(
    $CLI, $INPUT, "-o", "x.csv", "--fill", "age:unknown"
)

# ---------- 7. empty file ----------
Run-Py "7. empty file (expect 0)" @(
    $CLI, $INPUT_EMPTY, "-o", "e.csv", "--report", "r_empty.json"
)
& $PY -c "import json;d=json.load(open('r_empty.json',encoding='utf-8'));print('  rows_in =', d['rows_in'], ', rows_out =', d['rows_out'])"

# ---------- 8. mean on non-numeric ----------
Run-Py "8. mean on non-numeric (expect 3)" @(
    $CLI, $INPUT, "-o", "x.csv", "--fill", "email:mean"
)

# ---------- 9. summary ----------
Write-Host ""
Write-Host "=== 9. report.json summary ===" -ForegroundColor Yellow
& $PY -c "import json;d=json.load(open('report.json',encoding='utf-8'));print(json.dumps({k:d[k] for k in ('encoding','rows_in','rows_out','dedup_removed')},ensure_ascii=False,indent=2));print('violations =', len(d['violations']))"

Write-Host ""
Write-Host "All demos finished." -ForegroundColor Green
Write-Host "Expected: pytest=0, normal=0, strict=3, gbk=0, missing=2, bad-rule=3, empty=0, mean-non-numeric=3" -ForegroundColor Green