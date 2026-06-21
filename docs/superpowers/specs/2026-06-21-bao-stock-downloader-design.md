# BaoStock 数据下载器设计

## 概述

使用 BaoStock API 下载 A 股全市场历史 K 线数据，支持日线、周线、月线、5/15/30/60 分钟线。提供增量下载（跳过已下载数据）、全量校验补漏、文件日志输出。

## 目录结构

```
baostock_downloader/
├── __init__.py
├── cli.py              # 入口：download / verify 命令，支持 --help/-h
├── downloader.py       # DownloadManager 主协调器
├── api_client.py       # BaostockApiClient，API 封装 + 重试 + 限流
├── storage.py          # DataStorage，CSV 读写
├── models.py           # Bar, KlinePeriod 数据类
└── logger.py           # 日志配置

data/                   # 数据目录（ configurable via config.yaml ）
├── daily/              # 日线：data/daily/{code}.csv
├── weekly/             # 周线：data/weekly/{code}.csv
├── monthly/            # 月线：data/monthly/{code}.csv
├── m5/                 # 5 分钟：data/m5/{code}.csv
├── m15/                # 15 分钟：data/m15/{code}.csv
├── m30/                # 30 分钟：data/m30/{code}.csv
└── m60/                # 60 分钟：data/m60/{code}.csv

manifest/               # manifest 目录（与 data 同级的 manifest/ 子目录）
├── {code}_{cycle}.json # 每个股票 + 周期一个 manifest 文件
└── ...

logs/                   # 日志目录，按运行日期命名
└── {date}.log          # 如 logs/2026-06-21.log

config.yaml             # 配置文件
```

## CLI 接口

```bash
# 下载命令
python -m baostock_downloader download --help
python -m baostock_downloader download -h

# 下载单只股票单周期
python -m baostock_downloader download --code 000001.SZ --cycle daily --start 2020-01-01 --end 2024-12-31

# 下载全市场单周期
python -m baostock_downloader download --cycle daily --start 2020-01-01 --end 2024-12-31

# 下载全市场全周期
python -m baostock_downloader download --all-cycles --start 2020-01-01 --end 2024-12-31

# 校验命令
python -m baostock_downloader verify --help
python -m baostock_downloader verify -h

# 全量校验 + 补漏
python -m baostock_downloader verify --cycle daily
python -m baostock_downloader verify --all-cycles
```

## 核心流程

### 下载流程 (download 命令)

1. 解析参数（code 或全市场，cycle 或全周期，start_date，end_date）
2. 全市场时：从 BaoStock 实时获取所有股票列表 `baostock.query_all_stock(day=start_date)`
3. 遍历每个股票的每个周期：
   a. 读取 `manifest/{code}_{cycle}.json`（存在则获取 `max_date`）
   b. 计算实际下载区间：有 manifest 时从 `max_date + 1` 开始，否则从 `start_date` 开始
   c. 调用 `BaostockApiClient.fetch_kline(code, cycle, start, end)`
   d. 调用 `DataStorage.save_csv(code, cycle, bars)` 写入 CSV（append 模式，写入前比对最后一行日期防重）
   e. 更新 `manifest/{code}_{cycle}.json` 的 `min_date`/`max_date`/`row_count`
   f. 成功写入 info 日志；异常写入 error 日志
4. 限流：信号量控制每秒最多 10 次调用

### 校验流程 (verify 命令)

1. 遍历 `data/{cycle}/*.csv` 所有文件
2. 对每个 CSV 读取日期列，检测连续性（相邻日期差应为 1 天或对应周期倍数）
3. 发现断档：计算缺失日期区间，调用 API 重新下载缺失段
4. 补下载后更新 manifest
5. 报告校验结果：正常/补漏/异常数量

## API 重试策略

- **限流**：信号量控制，每秒最多 10 次调用
- **重试**：失败自动重试最多 3 次，指数退避（1s → 2s → 4s）
- **跳过**：连续失败 10 次后跳过该股票/周期，记录到异常日志

## 数据完整性保障

manifest 文件结构 (`manifest/{code}_{cycle}.json`)：
```json
{
  "code": "000001.SZ",
  "cycle": "daily",
  "min_date": "2020-01-01",
  "max_date": "2024-06-30",
  "row_count": 1100,
  "updated_at": "2024-06-30T10:00:00"
}
```

增量下载逻辑：
- 有 manifest → 只下载 `max_date + 1` 至今
- 无 manifest → 首次全量下载

## 日志格式

日志文件 `logs/{date}.log`，每次运行追加：

```
2026-06-21 10:00:00 [INFO] 000001.SZ daily - downloaded 100 bars, 2024-01-01 to 2024-06-30
2026-06-21 10:00:01 [INFO] 000001.SZ daily - manifest updated, max_date=2024-06-30
2026-06-21 10:00:02 [WARN] 000002.SZ m5 - retry 2/3, network error
2026-06-21 10:00:05 [ERROR] 000003.SZ daily - failed after 3 retries, skip
2026-06-21 10:00:05 [INFO] Summary: total=5000, success=4980, failed=20
```

## 数据模型（各自用自己的列）

各周期 CSV 列不同，按 BaoStock API 实际返回字段来写。统一使用后复权（`adjustflag=2`）。

### 日线 CSV 列

```
date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,isST
```

### 周线 CSV 列

```
date,code,open,high,low,close,volume,amount,adjustflag,turn
```

### 月线 CSV 列

```
date,code,open,high,low,close,volume,amount,adjustflag,turn
```

### 分钟线 CSV 列（5/15/30/60 分钟）

```
date,time,code,open,high,low,close,volume,amount
```

注意：分钟线 `date` 格式为 `YYYY-MM-DD`，`time` 格式为 `YYYYMMDDHHMMSS`（如 `20240102093500000` 表示 09:35:00）。

## 周期与 BaoStock 字段映射

| 周期    | BaoStock frequency | 复权 | 字段数 |
|---------|--------------------|------|--------|
| daily   | d                  | 2（后复权） | 12 |
| weekly  | w                  | 2（后复权） | 10 |
| monthly | m                  | 2（后复权） | 10 |
| m5      | 5                  | 2（后复权） | 9 |
| m15     | 15                 | 2（后复权） | 9 |
| m30     | 30                 | 2（后复权） | 9 |
| m60     | 60                 | 2（后复权） | 9 |

## 配置 (config.yaml)

```yaml
data_dir: "data"          # 数据根目录
manifest_dir: "manifest"  # manifest 目录
log_dir: "logs"           # 日志目录
rate_limit: 10            # 每秒最多调用次数
retry_times: 3            # 重试次数
retry_delay: 1            # 重试初始延迟（秒）
skip_threshold: 10        # 连续失败跳过阈值
```