import pytest
from unittest.mock import patch, MagicMock
from baostock_downloader.downloader import DownloadManager
from baostock_downloader.models import KlinePeriod, Bar


class TestDownloadManager:
    @patch("baostock_downloader.api_client.BaostockApiClient.get_stock_list")
    @patch("baostock_downloader.api_client.BaostockApiClient.fetch_kline")
    def test_download_incremental_skips_existingData(self, mock_fetch, mock_list):
        mock_list.return_value = ["000001.SZ"]
        mock_fetch.return_value = [
            Bar(date="2024-01-01", code="000001.SZ", open=10.0, high=10.5, low=9.8, close=10.2, volume=1000000, amount=10000000),
        ]

        manager = DownloadManager(rate_limit=10)
        # 第一次下载
        result = manager.download(cycle=KlinePeriod.DAILY, start_date="2024-01-01", end_date="2024-01-10")
        assert result.total == 1