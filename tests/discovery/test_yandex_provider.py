import pytest
from unittest.mock import patch, MagicMock
from novel_downloader.discovery.providers.yandex import YandexProvider
from novel_downloader.models import SearchResult

def test_yandex_search_normal():
    provider = YandexProvider()
    fake_html = """
    <html>
        <li class="serp-item">
            <a class="OrganicTitle-Link" href="https://example.com/book/1">《诛仙》全集目录</a>
            <div class="OrganicText">这是诛仙小说的完整目录...</div>
        </li>
    </html>
    """
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_html.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        results = provider.search("诛仙 目录")
        assert len(results) == 1
        assert results[0].provider == "yandex"
        assert results[0].url == "https://example.com/book/1"
        assert "诛仙" in results[0].title

def test_yandex_captcha_failure():
    provider = YandexProvider()
    fake_html = "<html><title>SmartCaptcha</title><body>Please verify you are human</body></html>"
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_html.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with pytest.raises(RuntimeError) as exc_info:
            provider.search("诛仙 目录")
        assert "SmartCaptcha" in str(exc_info.value)
