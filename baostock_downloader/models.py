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
