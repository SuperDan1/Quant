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

        content = (Path(self.storage.data_dir) / "daily" / "000001.SZ.csv").read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3  # header + 2 unique data rows (2024-01-01 deduped)

    def test_read_csv(self):
        bars = [
            Bar(date="2024-01-01", code="000001.SZ", open=10.0, high=10.5, low=9.8, close=10.2, volume=1000000, amount=10000000),
        ]
        self.storage.save_csv("000001.SZ", KlinePeriod.DAILY, bars)
        read_bars = self.storage.read_csv("000001.SZ", KlinePeriod.DAILY)
        assert len(read_bars) == 1
        assert read_bars[0].date == "2024-01-01"
