from unittest.mock import MagicMock
from novel_downloader.discovery.engine import DiscoveryEngine
from novel_downloader.models import SearchResult

def test_discovery_engine_handles_yandex_failure_gracefully():
    engine = DiscoveryEngine("诛仙", "萧鼎")
    
    # Mock providers
    mock_builtin = MagicMock()
    mock_builtin.name = "builtin"
    mock_builtin.search.return_value = []

    mock_google = MagicMock()
    mock_google.name = "google"
    mock_google.search.return_value = [
        SearchResult(provider="google", query="q", title="诛仙1", url="https://example.com/g1", rank=1),
        SearchResult(provider="google", query="q", title="诛仙2", url="https://example.com/g2", rank=2),
        SearchResult(provider="google", query="q", title="诛仙3", url="https://example.com/g3", rank=3),
    ]

    mock_yandex = MagicMock()
    mock_yandex.name = "yandex"
    mock_yandex.search.side_effect = TimeoutError("Yandex connection timed out")

    mock_ddg = MagicMock()
    mock_ddg.name = "duckduckgo"
    mock_ddg.search.return_value = [
        SearchResult(provider="duckduckgo", query="q", title="诛仙4", url="https://example.com/ddg1", rank=1),
        SearchResult(provider="duckduckgo", query="q", title="诛仙5", url="https://example.com/ddg2", rank=2),
    ]

    engine.providers = [mock_builtin, mock_google, mock_yandex, mock_ddg]

    pool = engine.discover_candidates(deep=False)
    
    # 期望：任务不崩溃，CandidatePool 成功聚合 Google 与 DDG 的结果 (>0)
    assert pool.count() >= 5
    
    # 期望：记录了 Yandex 的 failure
    failures = engine.get_failures()
    assert len(failures) >= 1
    assert any(f.target == "yandex" and "timed out" in f.reason for f in failures)
