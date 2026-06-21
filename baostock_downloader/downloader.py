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

        self.storage.save_csv(code, period, bars)
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
                    self.logger.warning(f"{code} {cycle.value} - missing {len(missing)} ranges, patching...")
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