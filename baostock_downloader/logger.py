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
