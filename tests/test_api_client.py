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