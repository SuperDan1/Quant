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