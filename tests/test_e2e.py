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
        assert "min_date" in m
        assert "max_date" in m
