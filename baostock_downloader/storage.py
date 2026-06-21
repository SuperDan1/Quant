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
