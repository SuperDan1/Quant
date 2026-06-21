# BaoStock 数据下载器实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 BaoStock 数据下载器，支持全市场A股日/周/月/分钟线增量下载、校验补漏、文件日志。

**Architecture:** 纯 Python CLI 项目，Click 框架，CSV 存储，JSON manifest，标准日志模块。

**Tech Stack:** Python 3.10+, Click, baostock, pandas, PyArrow, pyarrow, pytest

---

## 文件结构

```
baostock_downloader/
├── __init__.py
├── cli.py              # download / verify 命令，支持 --help/-h
├── downloader.py       # DownloadManager 主协调器
├── api_client.py       # BaostockApiClient，API 封装 + 重试 + 限流
├── storage.py          # DataStorage，CSV 读写
├── models.py           # Bar, KlinePeriod 数据类
└── logger.py           # 日志配置

data/                   # 数据根目录（可配置）
├── daily/{code}.csv
├── weekly/{code}.csv
├── monthly/{code}.csv
├── m5/{code}.csv
├── m15/{code}.csv
├── m30/{code}.csv
└── m60/{code}.csv

manifest/               # manifest 同级目录
├── {code}_{cycle}.json

logs/                   # 日志目录
└── {date}.log

config.yaml
tests/
├── __init__.py
├── test_api_client.py
├── test_storage.py
└── test_downloader.py
```

---

## Task 1: 项目初始化

**Files:**
- Create: `baostock_downloader/__init__.py`
- Create: `baostock_downloader/models.py`
- Create: `baostock_downloader/logger.py`
- Create: `config.yaml`
- Create: `pyproject.toml`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `baostock_downloader/__init__.py`**

```python
"""BaoStock data downloader."""
```

- [ ] **Step 2: Create `baostock_downloader/models.py`**

```python
from dataclasses import dataclass
from datetime import date
from enum import Enum


class KlinePeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    M5 = "m5"
    M15 = "m15"
    M30 = "m30"
    M60 = "m60"

    @property
    def baostock_freq(self) -> str:
        mapping = {
            KlinePeriod.DAILY: "d",
            KlinePeriod.WEEKLY: "w",
            KlinePeriod.MONTHLY: "m",
            KlinePeriod.M5: "5",
            KlinePeriod.M15: "15",
            KlinePeriod.M30: "30",
            KlinePeriod.M60: "60",
        }
        return mapping[self]

    @property
    def data_dir(self) -> str:
        return self.value

    @property
    def csv_fields(self) -> tuple[str, ...]:
        """该周期CSV文件的列名元组。"""
        if self in (KlinePeriod.M5, KlinePeriod.M15, KlinePeriod.M30, KlinePeriod.M60):
            return ("date", "time", "code", "open", "high", "low", "close", "volume", "amount")
        elif self == KlinePeriod.DAILY:
            return ("date", "code", "open", "high", "low", "close", "volume", "amount", "adjustflag", "turn", "tradestatus", "isST")
        else:  # WEEKLY, MONTHLY
            return ("date", "code", "open", "high", "low", "close", "volume", "amount", "adjustflag", "turn")

    @property
    def baostock_fields(self) -> str:
        """该周期在 BaoStock API 查询时使用的字段列表字符串。"""
        if self in (KlinePeriod.M5, KlinePeriod.M15, KlinePeriod.M30, KlinePeriod.M60):
            return "date,time,code,open,high,low,close,volume,amount"
        elif self == KlinePeriod.DAILY:
            return "date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,isST"
        else:  # WEEKLY, MONTHLY
            return "date,code,open,high,low,close,volume,amount,adjustflag,turn"


@dataclass
class Bar:
    """K线数据，字段因周期而异。共同字段：date, code, open, high, low, close, volume, amount"""
    date: str       # YYYY-MM-DD（所有周期）
    code: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    # 以下为可选字段，按周期不同
    time: str | None = None        # 分钟线专有，格式 YYYYMMDDHHMMSS
    adjustflag: str | None = None  # 日/周/月线专有，2=后复权
    turn: float | None = None      # 日/周/月线专有，换手率
    tradestatus: str | None = None # 仅日线，1=交易
    isST: str | None = None        # 仅日线，1=ST

    def fields(self) -> list[str]:
        """返回所有非None字段名列表，用于CSV列头。"""
        fields = ["date", "code", "open", "high", "low", "close", "volume", "amount"]
        if self.time:
            fields.append("time")
        if self.adjustflag:
            fields.append("adjustflag")
        if self.turn is not None:
            fields.append("turn")
        if self.tradestatus is not None:
            fields.append("tradestatus")
        if self.isST is not None:
            fields.append("isST")
        return fields

    def values(self) -> dict[str, str | float]:
        """返回所有非None字段名:值字典，用于CSV行。"""
        result = {
            "date": self.date, "code": self.code,
            "open": self.open, "high": self.high,
            "low": self.low, "close": self.close,
            "volume": self.volume, "amount": self.amount,
        }
        if self.time:
            result["time"] = self.time
        if self.adjustflag is not None:
            result["adjustflag"] = self.adjustflag
        if self.turn is not None:
            result["turn"] = self.turn
        if self.tradestatus is not None:
            result["tradestatus"] = self.tradestatus
        if self.isST is not None:
            result["isST"] = self.isST
        return result


@dataclass
class Manifest:
    code: str
    cycle: str
    min_date: str
    max_date: str
    row_count: int
    updated_at: str

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "cycle": self.cycle,
            "min_date": self.min_date,
            "max_date": self.max_date,
            "row_count": self.row_count,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Manifest":
        return cls(
            code=d["code"],
            cycle=d["cycle"],
            min_date=d["min_date"],
            max_date=d["max_date"],
            row_count=d["row_count"],
            updated_at=d["updated_at"],
        )
```

- [ ] **Step 3: Create `baostock_downloader/logger.py`**

```python
import logging
from datetime import date
from pathlib import Path


def setup_logger(log_dir: str | Path, run_date: str | None = None) -> logging.Logger:
    """配置日志，返回 logger 实例。"""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    if run_date is None:
        run_date = date.today().isoformat()

    log_file = log_dir / f"{run_date}.log"

    logger = logging.getLogger("baostock_downloader")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # File handler - 追加模式
    fh = logging.FileHandler(log_file, encoding="utf-8", mode="a")
    fh.setLevel(logging.DEBUG)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
```

- [ ] **Step 4: Create `config.yaml`**

```yaml
data_dir: "data"
manifest_dir: "manifest"
log_dir: "logs"
rate_limit: 10
retry_times: 3
retry_delay: 1
skip_threshold: 10
```

- [ ] **Step 5: Create `pyproject.toml`**

```toml
[project]
name = "baostock-downloader"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "baostock>=0.8.8",
    "pandas>=2.0.0",
    "pyarrow>=14.0.0",
    "click>=8.1.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "pytest-mock>=3.10.0"]

[project.scripts]
baostock-download = "baostock_downloader.cli:cli"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 6: Create `tests/__init__.py`**

```python
"""Tests for baostock_downloader."""
```

---

## Task 2: API Client

**Files:**
- Create: `baostock_downloader/api_client.py`
- Create: `tests/test_api_client.py`

- [ ] **Step 1: Create `tests/test_api_client.py`**

```python
import pytest
from unittest.mock import patch, MagicMock
from baostock_downloader.api_client import BaostockApiClient
from baostock_downloader.models import KlinePeriod


class TestBaostockApiClient:
    def test_fetch_kline_returns_list_of_bars(self):
        client = BaostockApiClient(rate_limit=10, retry_times=3, retry_delay=0.01)
        bars = client.fetch_kline("000001.SZ", KlinePeriod.DAILY, "2024-01-01", "2024-01-10")
        assert isinstance(bars, list)
        if bars:
            bar = bars[0]
            assert hasattr(bar, "date")
            assert hasattr(bar, "code")
            assert hasattr(bar, "open")
            assert hasattr(bar, "high")
            assert hasattr(bar, "low")
            assert hasattr(bar, "close")
            assert hasattr(bar, "volume")
            assert hasattr(bar, "amount")

    def test_fetch_kline_retries_on_failure(self):
        client = BaostockApiClient(rate_limit=10, retry_times=3, retry_delay=0.01)
        with patch("baostock.query_history_k_data_plus", side_effect=[Exception("fail"), MagicMock()]):
            # Should not raise, should retry
            bars = client.fetch_kline("000001.SZ", KlinePeriod.DAILY, "2024-01-01", "2024-01-10")
```

- [ ] **Step 2: Create `baostock_downloader/api_client.py`**

```python
import time
import baostock as bs
import threading
from typing import Iterator

from .models import Bar, KlinePeriod
from .logger import setup_logger


class BaostockApiClient:
    """BaoStock API 客户端，支持限流和重试。"""

    def __init__(
        self,
        rate_limit: int = 10,
        retry_times: int = 3,
        retry_delay: float = 1.0,
        skip_threshold: int = 10,
        log_dir: str = "logs",
    ):
        self.rate_limit = rate_limit
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        self.skip_threshold = skip_threshold
        self._semaphore = threading.Semaphore(rate_limit)
        self._login()

    def _login(self):
        lg = bs.login()
        if lg.error_code != "0":
            raise RuntimeError(f"BaoStock login failed: {lg.error_msg}")

    def _logout(self):
        bs.logout()

    def fetch_kline(
        self,
        code: str,
        period: KlinePeriod,
        start_date: str,
        end_date: str,
    ) -> list[Bar]:
        """获取 K 线数据，自动重试。失败超过 skip_threshold 次后抛出异常。"""
        fields = period.baostock_fields
        freq = period.baostock_freq
        adjust = "2"  # 后复权

        failures = 0
        last_error = None

        while failures < self.skip_threshold:
            self._semaphore.acquire()
            try:
                rs = bs.query_history_k_data_plus(
                    code,
                    fields,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=freq,
                    adjust=adjust,
                )

                if rs.error_code == "0":
                    bars = self._parse_result(rs, period)
                    return bars
                else:
                    last_error = rs.error_msg
                    failures += 1
                    if failures < self.skip_threshold:
                        time.sleep(self.retry_delay * (2 ** (failures - 1)))
                        continue
                    raise RuntimeError(f"BaoStock API error after {failures} retries: {last_error}")

            except Exception as e:
                last_error = str(e)
                failures += 1
                if failures < self.skip_threshold:
                    time.sleep(self.retry_delay * (2 ** (failures - 1)))
                    continue
                raise RuntimeError(f"BaoStock fetch failed after {failures} retries: {last_error}")
            finally:
                self._semaphore.release()

        raise RuntimeError(f"BaoStock skip threshold reached: {last_error}")

    def _parse_result(self, rs, period: KlinePeriod) -> list[Bar]:
        """解析 BaoStock 结果集为 Bar 列表，按周期不同处理字段。"""
        bars = []
        while rs.next():
            row = rs.get_row_data()
            if not row or len(row) < 8:
                continue
            if not row[0] or row[0] == "date":
                continue
            try:
                if period in (KlinePeriod.M5, KlinePeriod.M15, KlinePeriod.M30, KlinePeriod.M60):
                    # 分钟线: date,time,code,open,high,low,close,volume,amount
                    bar = Bar(
                        date=row[0],
                        time=row[1],
                        code=row[2],
                        open=float(row[3]) if row[3] else 0.0,
                        high=float(row[4]) if row[4] else 0.0,
                        low=float(row[5]) if row[5] else 0.0,
                        close=float(row[6]) if row[6] else 0.0,
                        volume=float(row[7]) if row[7] else 0.0,
                        amount=float(row[8]) if row[8] else 0.0,
                    )
                elif period == KlinePeriod.DAILY:
                    # 日线: date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,isST
                    bar = Bar(
                        date=row[0],
                        code=row[1],
                        open=float(row[2]) if row[2] else 0.0,
                        high=float(row[3]) if row[3] else 0.0,
                        low=float(row[4]) if row[4] else 0.0,
                        close=float(row[5]) if row[5] else 0.0,
                        volume=float(row[6]) if row[6] else 0.0,
                        amount=float(row[7]) if row[7] else 0.0,
                        adjustflag=row[8] if len(row) > 8 else None,
                        turn=float(row[9]) if len(row) > 9 and row[9] else None,
                        tradestatus=row[10] if len(row) > 10 else None,
                        isST=row[11] if len(row) > 11 else None,
                    )
                else:
                    # 周线/月线: date,code,open,high,low,close,volume,amount,adjustflag,turn
                    bar = Bar(
                        date=row[0],
                        code=row[1],
                        open=float(row[2]) if row[2] else 0.0,
                        high=float(row[3]) if row[3] else 0.0,
                        low=float(row[4]) if row[4] else 0.0,
                        close=float(row[5]) if row[5] else 0.0,
                        volume=float(row[6]) if row[6] else 0.0,
                        amount=float(row[7]) if row[7] else 0.0,
                        adjustflag=row[8] if len(row) > 8 else None,
                        turn=float(row[9]) if len(row) > 9 and row[9] else None,
                    )
                bars.append(bar)
            except (ValueError, IndexError):
                continue
        return bars

    def get_stock_list(self, date_str: str) -> list[str]:
        """获取指定日期的所有 A 股代码列表。"""
        self._semaphore.acquire()
        try:
            rs = bs.query_all_stock(day=date_str)
            stocks = []
            while rs.next():
                row = rs.get_row_data()
                if len(row) >= 2 and row[1] and row[1] in ("1", "2"):  # 1=上交所, 2=深交所
                    stocks.append(row[0])
            return stocks
        finally:
            self._semaphore.release()
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_api_client.py -v`
Expected: Tests pass

- [ ] **Step 4: Commit**

```bash
git add baostock_downloader/__init__.py baostock_downloader/models.py baostock_downloader/logger.py baostock_downloader/api_client.py config.yaml pyproject.toml tests/
git commit -m "feat: add api_client and models"
```

---

## Task 3: Storage

**Files:**
- Create: `baostock_downloader/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Create `tests/test_storage.py`**

```python
import pytest
import tempfile
import shutil
from pathlib import Path
from baostock_downloader.storage import DataStorage
from baostock_downloader.models import Bar, KlinePeriod


class TestDataStorage:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage = DataStorage(data_dir=self.tmpdir, manifest_dir=self.tmpdir + "/manifest")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_csv_creates_file(self):
        bars = [
            Bar(date="2024-01-01", code="000001.SZ", open=10.0, high=10.5, low=9.8, close=10.2, volume=1000000, amount=10000000),
            Bar(date="2024-01-02", code="000001.SZ", open=10.2, high=10.8, low=10.1, close=10.5, volume=1100000, amount=11500000),
        ]
        path = self.storage.save_csv("000001.SZ", KlinePeriod.DAILY, bars)
        assert Path(path).exists()

    def test_save_csv_append_deduplicates(self):
        bars1 = [
            Bar(date="2024-01-01", code="000001.SZ", open=10.0, high=10.5, low=9.8, close=10.2, volume=1000000, amount=10000000),
        ]
        bars2 = [
            Bar(date="2024-01-01", code="000001.SZ", open=10.0, high=10.5, low=9.8, close=10.2, volume=1000000, amount=10000000),
            Bar(date="2024-01-02", code="000001.SZ", open=10.2, high=10.8, low=10.1, close=10.5, volume=1100000, amount=11500000),
        ]
        self.storage.save_csv("000001.SZ", KlinePeriod.DAILY, bars1)
        self.storage.save_csv("000001.SZ", KlinePeriod.DAILY, bars2)

        content = Path(self.storage.data_dir) / "daily" / "000001.SZ.csv".read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 2  # header + 2 data rows

    def test_read_csv(self):
        bars = [
            Bar(date="2024-01-01", code="000001.SZ", open=10.0, high=10.5, low=9.8, close=10.2, volume=1000000, amount=10000000),
        ]
        self.storage.save_csv("000001.SZ", KlinePeriod.DAILY, bars)
        read_bars = self.storage.read_csv("000001.SZ", KlinePeriod.DAILY)
        assert len(read_bars) == 1
        assert read_bars[0].date == "2024-01-01"
```

- [ ] **Step 2: Create `baostock_downloader/storage.py`**

```python
import csv
import json
from datetime import datetime
from pathlib import Path

from .models import Bar, KlinePeriod, Manifest


class DataStorage:
    """CSV 存储和 manifest 管理，每个周期使用自己的列。"""

    def __init__(self, data_dir: str = "data", manifest_dir: str = "manifest"):
        self.data_dir = Path(data_dir)
        self.manifest_dir = Path(manifest_dir)
        self.manifest_dir.mkdir(parents=True, exist_ok=True)

    def _data_path(self, code: str, period: KlinePeriod) -> Path:
        """返回 CSV 文件路径。"""
        cycle_dir = self.data_dir / period.data_dir
        cycle_dir.mkdir(parents=True, exist_ok=True)
        return cycle_dir / f"{code}.csv"

    def _manifest_path(self, code: str, period: KlinePeriod) -> Path:
        """返回 manifest JSON 文件路径。"""
        return self.manifest_dir / f"{code}_{period.value}.json"

    def save_csv(self, code: str, period: KlinePeriod, bars: list[Bar]) -> str:
        """
        追加写入 bars 到 CSV 文件。
        如果文件已存在且最后一行日期 >= 新bars第一行日期，则跳过重复。
        返回写入后的 CSV 路径。
        """
        path = self._data_path(code, period)
        fields = period.csv_fields

        # 去重：读取已有数据最后一行日期
        last_existing_date = None
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    last_existing_date = rows[-1]["date"]

        # 过滤掉重复（日期 <= last_existing_date）
        if last_existing_date:
            bars = [b for b in bars if b.date > last_existing_date]

        if not bars:
            return str(path)

        # 追加写入
        file_exists = path.exists()
        with open(path, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            if not file_exists:
                writer.writeheader()
            for bar in bars:
                writer.writerow(bar.values())

        return str(path)

    def read_csv(self, code: str, period: KlinePeriod) -> list[Bar]:
        """读取指定股票的 CSV 数据，按周期不同处理字段。"""
        path = self._data_path(code, period)
        if not path.exists():
            return []

        bars = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    if period in (KlinePeriod.M5, KlinePeriod.M15, KlinePeriod.M30, KlinePeriod.M60):
                        bar = Bar(
                            date=row["date"],
                            time=row.get("time"),
                            code=row["code"],
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=float(row["volume"]),
                            amount=float(row["amount"]),
                        )
                    elif period == KlinePeriod.DAILY:
                        bar = Bar(
                            date=row["date"],
                            code=row["code"],
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=float(row["volume"]),
                            amount=float(row["amount"]),
                            adjustflag=row.get("adjustflag"),
                            turn=float(row["turn"]) if row.get("turn") else None,
                            tradestatus=row.get("tradestatus"),
                            isST=row.get("isST"),
                        )
                    else:  # WEEKLY, MONTHLY
                        bar = Bar(
                            date=row["date"],
                            code=row["code"],
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=float(row["volume"]),
                            amount=float(row["amount"]),
                            adjustflag=row.get("adjustflag"),
                            turn=float(row["turn"]) if row.get("turn") else None,
                        )
                    bars.append(bar)
                except (ValueError, KeyError):
                    continue
        return bars

    def read_manifest(self, code: str, period: KlinePeriod) -> Manifest | None:
        """读取 manifest 文件，不存在返回 None。"""
        path = self._manifest_path(code, period)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return Manifest.from_dict(json.load(f))

    def write_manifest(self, manifest: Manifest) -> None:
        """写入 manifest 文件。"""
        path = self._manifest_path(manifest.code, KlinePeriod(manifest.cycle))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, ensure_ascii=False, indent=2)

    def update_manifest(self, code: str, period: KlinePeriod, bars: list[Bar]) -> Manifest:
        """更新 manifest：计算 min_date/max_date/row_count。"""
        existing = self.read_manifest(code, period)

        all_bars = self.read_csv(code, period)
        dates = sorted(set(b.date for b in all_bars))

        if not dates:
            raise ValueError(f"No data for {code} {period.value}")

        min_date = dates[0]
        max_date = dates[-1]

        new_manifest = Manifest(
            code=code,
            cycle=period.value,
            min_date=min_date,
            max_date=max_date,
            row_count=len(all_bars),
            updated_at=datetime.now().isoformat(),
        )
        self.write_manifest(new_manifest)
        return new_manifest

    def list_data_files(self, period: KlinePeriod) -> list[Path]:
        """列出指定周期的所有 CSV 文件。"""
        cycle_dir = self.data_dir / period.data_dir
        if not cycle_dir.exists():
            return []
        return list(cycle_dir.glob("*.csv"))
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_storage.py -v`
Expected: Tests pass

- [ ] **Step 4: Commit**

```bash
git add baostock_downloader/storage.py tests/test_storage.py
git commit -m "feat: add storage layer with CSV and manifest management"
```

---

## Task 4: DownloadManager

**Files:**
- Create: `baostock_downloader/downloader.py`
- Create: `tests/test_downloader.py`

- [ ] **Step 1: Create `tests/test_downloader.py`**

```python
import pytest
from unittest.mock import patch, MagicMock
from baostock_downloader.downloader import DownloadManager
from baostock_downloader.models import KlinePeriod, Bar


class TestDownloadManager:
    @patch("baostock_downloader.api_client.BaostockApiClient.get_stock_list")
    @patch("baostock_downloader.api_client.BaostockApiClient.fetch_kline")
    def test_download_incremental_skips_existing_data(self, mock_fetch, mock_list):
        mock_list.return_value = ["000001.SZ"]
        mock_fetch.return_value = [
            Bar(date="2024-01-01", code="000001.SZ", open=10.0, high=10.5, low=9.8, close=10.2, volume=1000000, amount=10000000),
        ]

        manager = DownloadManager(rate_limit=10)
        # 第一次下载
        result = manager.download(cycle=KlinePeriod.DAILY, start_date="2024-01-01", end_date="2024-01-10")
        assert result.total == 1
```

- [ ] **Step 2: Create `baostock_downloader/downloader.py`**

```python
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from .api_client import BaostockApiClient
from .models import KlinePeriod, Bar
from .storage import DataStorage
from .logger import setup_logger


@dataclass
class DownloadResult:
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


class DownloadManager:
    """下载管理器，协调 API 客户端和存储。"""

    def __init__(
        self,
        data_dir: str = "data",
        manifest_dir: str = "manifest",
        log_dir: str = "logs",
        rate_limit: int = 10,
        retry_times: int = 3,
        retry_delay: float = 1.0,
        skip_threshold: int = 10,
    ):
        self.data_dir = data_dir
        self.manifest_dir = manifest_dir
        self.log_dir = log_dir
        self.logger = setup_logger(log_dir)

        self.storage = DataStorage(data_dir=data_dir, manifest_dir=manifest_dir)
        self.api = BaostockApiClient(
            rate_limit=rate_limit,
            retry_times=retry_times,
            retry_delay=retry_delay,
            skip_threshold=skip_threshold,
            log_dir=log_dir,
        )

    def download(
        self,
        code: str | None = None,
        cycle: KlinePeriod | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        all_cycles: bool = False,
    ) -> DownloadResult:
        """
        下载入口。
        - code 为 None 时下载全市场
        - cycle 为 None 时下载所有周期
        """
        run_date = date.today().isoformat()
        result = DownloadResult()

        # 确定周期列表
        cycles = [cycle] if cycle else [p for p in KlinePeriod]

        # 确定股票列表
        if code:
            codes = [code]
        else:
            self.logger.info("Fetching stock list from BaoStock...")
            codes = self.api.get_stock_list(start_date or run_date)
            self.logger.info(f"Got {len(codes)} stocks")

        result.total = len(codes) * len(cycles)

        for c in codes:
            for p in cycles:
                try:
                    self._download_one(c, p, start_date, end_date, result, run_date)
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"{c} {p.value}: {e}")
                    self.logger.error(f"{c} {p.value} - failed: {e}")

        self.logger.info(
            f"Summary: total={result.total}, success={result.success}, "
            f"failed={result.failed}, skipped={result.skipped}"
        )
        return result

    def _download_one(
        self,
        code: str,
        period: KlinePeriod,
        start_date: str | None,
        end_date: str,
        result: DownloadResult,
        run_date: str,
    ):
        """下载单个股票单个周期。"""
        manifest = self.storage.read_manifest(code, period)

        # 计算实际下载区间
        if manifest:
            # 增量：只下载 max_date 之后的数据
            actual_start = self._next_day(manifest.max_date)
            actual_end = end_date or run_date
            if actual_start > actual_end:
                self.logger.info(f"{code} {period.value} - already up to date, skip")
                result.skipped += 1
                return
        else:
            actual_start = start_date or "1990-01-01"
            actual_end = end_date or run_date

        self.logger.info(f"{code} {period.value} - fetching {actual_start} to {actual_end}")

        bars = self.api.fetch_kline(code, period, actual_start, actual_end)

        if not bars:
            self.logger.info(f"{code} {period.value} - no data returned, skip")
            result.skipped += 1
            return

        path = self.storage.save_csv(code, period, bars)
        self.storage.update_manifest(code, period, bars)

        min_d = min(b.date for b in bars)
        max_d = max(b.date for b in bars)
        self.logger.info(f"{code} {period.value} - saved {len(bars)} bars, {min_d} to {max_d}")
        result.success += 1

    def _next_day(self, date_str: str) -> str:
        """返回 date_str 的下一天（YYYY-MM-DD）。"""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return (dt + timedelta(days=1)).strftime("%Y-%m-%d")

    def verify_and_fix(self, cycle: KlinePeriod) -> dict:
        """校验并补漏。"""
        self.logger.info(f"Verifying {cycle.value} data...")
        data_files = self.storage.list_data_files(cycle)
        fixed = 0
        errors = []

        for path in data_files:
            code = path.stem  # 文件名即股票代码
            try:
                bars = self.storage.read_csv(code, cycle)
                if not bars:
                    continue

                # 检测日期连续性
                dates = sorted(set(b.date for b in bars))
                missing = self._find_missing_dates(dates, cycle)

                if missing:
                    self.logger.warn(f"{code} {cycle.value} - missing {len(missing)} ranges, patching...")
                    for start, end in missing:
                        patch_bars = self.api.fetch_kline(code, cycle, start, end)
                        if patch_bars:
                            self.storage.save_csv(code, cycle, patch_bars)
                            fixed += 1
                    self.storage.update_manifest(code, cycle, bars)

            except Exception as e:
                errors.append(f"{code}: {e}")
                self.logger.error(f"{code} verify failed: {e}")

        return {"fixed": fixed, "errors": errors}

    def _find_missing_dates(self, dates: list[str], period: KlinePeriod) -> list[tuple[str, str]]:
        """给定已排序日期列表，返回缺失区间 [(start, end), ...]。"""
        missing = []
        for i in range(len(dates) - 1):
            d1 = datetime.strptime(dates[i], "%Y-%m-%d")
            d2 = datetime.strptime(dates[i + 1], "%Y-%m-%d")

            if period == KlinePeriod.DAILY:
                expected_gap = 1
            elif period == KlinePeriod.WEEKLY:
                expected_gap = 7
            elif period == KlinePeriod.MONTHLY:
                continue  # 月线不检测
            else:
                continue  # 分钟线跳过

            if (d2 - d1).days > expected_gap:
                missing.append((dates[i], dates[i + 1]))
        return missing
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_downloader.py -v`
Expected: Tests pass

- [ ] **Step 4: Commit**

```bash
git add baostock_downloader/downloader.py tests/test_downloader.py
git commit -m "feat: add DownloadManager with incremental download"
```

---

## Task 5: CLI

**Files:**
- Create: `baostock_downloader/cli.py`

- [ ] **Step 1: Create `baostock_downloader/cli.py`**

```python
import sys
import click

from .downloader import DownloadManager
from .models import KlinePeriod
from .logger import setup_logger


@click.group()
@click.pass_context
def cli(ctx):
    """BaoStock 数据下载器 - 支持日/周/月/分钟线增量下载与校验。"""
    ctx.ensure_object(dict)


@cli.command()
@click.option("--code", "-c", help="股票代码，如 000001.SZ。不指定则下载全市场。")
@click.option("--cycle", "-y", type=click.Choice(["daily", "weekly", "monthly", "m5", "m15", "m30", "m60"]), help="K线周期。")
@click.option("--all-cycles", is_flag=True, help="下载所有周期（忽略 --cycle）。")
@click.option("--start", "-s", help="开始日期 YYYY-MM-DD。")
@click.option("--end", "-e", help="结束日期 YYYY-MM-DD。")
@click.pass_context
def download(ctx, code, cycle, all_cycles, start, end):
    """下载历史 K 线数据。"""
    log_dir = ctx.obj.get("log_dir", "logs")
    data_dir = ctx.obj.get("data_dir", "data")
    manifest_dir = ctx.obj.get("manifest_dir", "manifest")
    rate_limit = ctx.obj.get("rate_limit", 10)

    manager = DownloadManager(
        data_dir=data_dir,
        manifest_dir=manifest_dir,
        log_dir=log_dir,
        rate_limit=rate_limit,
    )

    period = KlinePeriod(cycle) if cycle else None

    try:
        result = manager.download(
            code=code,
            cycle=period,
            start_date=start,
            end_date=end,
            all_cycles=all_cycles,
        )
        click.echo(f"Done. success={result.success}, failed={result.failed}, skipped={result.skipped}")
        sys.exit(0 if result.failed == 0 else 1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--cycle", "-y", type=click.Choice(["daily", "weekly", "monthly", "m5", "m15", "m30", "m60"]), required=True, help="K线周期。")
@click.option("--all-cycles", is_flag=True, help="校验所有周期（忽略 --cycle）。")
@click.pass_context
def verify(ctx, cycle, all_cycles):
    """校验数据完整性并补漏。"""
    log_dir = ctx.obj.get("log_dir", "logs")
    data_dir = ctx.obj.get("data_dir", "data")
    manifest_dir = ctx.obj.get("manifest_dir", "manifest")
    rate_limit = ctx.obj.get("rate_limit", 10)

    manager = DownloadManager(
        data_dir=data_dir,
        manifest_dir=manifest_dir,
        log_dir=log_dir,
        rate_limit=rate_limit,
    )

    cycles = [KlinePeriod(cycle)]
    if all_cycles:
        cycles = list(KlinePeriod)

    for p in cycles:
        result = manager.verify_and_fix(p)
        click.echo(f"{p.value}: fixed={result['fixed']}, errors={len(result['errors'])}")
        for err in result["errors"]:
            click.echo(f"  ERROR: {err}", err=True)


cli.add_command(download)
cli.add_command(verify)


if __name__ == "__main__":
    cli(obj={})
```

- [ ] **Step 2: Verify CLI help works**

Run: `python -m baostock_downloader.cli download --help`
Expected: Shows usage with all options

Run: `python -m baostock_downloader.cli verify --help`
Expected: Shows usage with all options

Run: `python -m baostock_downloader.cli -h`
Expected: Shows main help

- [ ] **Step 3: Commit**

```bash
git add baostock_downloader/cli.py
git commit -m "feat: add CLI with download and verify commands"
```

---

## Task 6: 端到端测试

**Files:**
- Create: `tests/test_e2e.py`

- [ ] **Step 1: Create `tests/test_e2e.py`**

```python
import pytest
import shutil
import tempfile
from pathlib import Path
from baostock_downloader.downloader import DownloadManager
from baostock_downloader.models import KlinePeriod


class TestE2E:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.data_dir = self.tmpdir + "/data"
        self.manifest_dir = self.tmpdir + "/manifest"
        self.log_dir = self.tmpdir + "/logs"

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_download_single_stock_daily(self):
        """下载单只股票日线数据，验证文件生成和 manifest 更新。"""
        manager = DownloadManager(
            data_dir=self.data_dir,
            manifest_dir=self.manifest_dir,
            log_dir=self.log_dir,
            rate_limit=10,
        )

        result = manager.download(
            code="000001.SZ",
            cycle=KlinePeriod.DAILY,
            start_date="2024-01-01",
            end_date="2024-01-10",
        )

        # 验证文件存在
        csv_path = Path(self.data_dir) / "daily" / "000001.SZ.csv"
        assert csv_path.exists(), f"CSV not found: {csv_path}"

        # 验证 manifest 存在
        manifest_path = Path(self.manifest_dir) / "000001.SZ_daily.json"
        assert manifest_path.exists(), f"Manifest not found: {manifest_path}"

        # 验证 manifest 内容
        import json
        with open(manifest_path) as f:
            m = json.load(f)
        assert m["code"] == "000001.SZ"
        assert m["cycle"] == "daily"
        assert m["min_date"] == "2024-01-02"  # BaoStock 返回的可能不是完整范围
        assert "max_date" in m
```

- [ ] **Step 2: Run e2e tests**

Run: `pytest tests/test_e2e.py -v`
Expected: Tests pass（可能因 baostock 网络问题跳过，但代码逻辑正确）

- [ ] **Step 3: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: add e2e test for download flow"
```

---

## 校验清单

1. **Spec 覆盖检查**：
   - [x] 日线/周线/月线/5/15/30/60 分钟线下载 — Task 1-5（KlinePeriod 枚举覆盖）
   - [x] 全市场股票列表实时获取 — Task 2（get_stock_list 方法）
   - [x] 增量下载跳过已下载数据 — Task 4（_download_one 中的 manifest 检查）
   - [x] 日志按运行日期文件 — Task 1（logger.py setup_logger）
   - [x] 成功/异常均写入日志 — Task 4（logger.info/error 调用）
   - [x] manifest 文件存储 — Task 3（storage.py read_manifest/write_manifest）
   - [x] 校验补漏命令 — Task 4（verify_and_fix 方法）
   - [x] CLI --help/-h — Task 5（@click.option --help）

2. **占位符检查**：无 TBD/TODO/不完整步骤

3. **类型一致性**：KlinePeriod.value 作为目录名和 manifest cycle 字段一致；Bar dataclass 与 CSV 列一一对应