# cleaner — 命令行数据清洗程序

处理四类问题：**编码、缺失、重复、非法值**。零第三方模型依赖，仅 `chardet`。

## 环境

- Python ≥ 3.10
- `pip install -r requirements.txt`
- 已验证：Python 3.11.9 / chardet 5.2.0 / pytest 8.3.3 / Linux x86_64

## 快速开始

```bash
python cleaner/cleaner.py samples/input_messy.csv -o out.csv \
  --fill age:mean \
  --dedup-keys id \
  --validate 'email:regex:^[^@]+@[^@]+\.[^@]+$' \
  --validate 'joined:date:%Y-%m-%d' \
  --report report.json
echo $?   # 0

python cleaner/cleaner.py samples/input_messy.csv -o out.csv \
  --validate 'joined:date:%Y-%m-%d' --strict
echo $?   # 3（存在非法日期）